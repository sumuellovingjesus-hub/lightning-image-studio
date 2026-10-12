#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""闪电生图台 · 本地中转服务器 v4.0
打开 http://127.0.0.1:8190 即是生图页面；
页面发起的 API 请求由本服务器转发给 ComfyUI（8188），同源无跨域拦截。

v4.0 新增：
  - /api/system-info  自动识别：模型清单 / 插件 / 运行环境 / 队列
  - 请求体大小限制（10 MB），防异常大包
  - 队列保护（最多 3 个排队任务）
  - 翻译超时自动降级（不阻塞出图）
  - 日志自动轮转（10 MB）
仅绑定 127.0.0.1，不对外网开放。
"""
import http.server
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "4.1.0"
BACKEND = "http://127.0.0.1:8188"
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "一键生图.html")
PORT = 8190
MAX_BODY = 10 * 1024 * 1024        # 请求体上限 10 MB
QUEUE_LIMIT = 3                    # 排队任务上限
TRANSLATE_TIMEOUT = 8              # 翻译超时（秒），超时降级
LOG_MAX = 10 * 1024 * 1024         # 日志轮转阈值

# 逐跳头不透传
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailers", "transfer-encoding", "upgrade", "content-length"}


def find_comfy_root():
    """定位 ComfyUI 根目录：优先读安装配置 config.json。"""
    for cand in (os.path.join(HERE, "..", "config.json"),
                 os.path.join(HERE, "config.json"),
                 os.path.join(os.path.expanduser("~"), "Desktop", "闪电生图台", "config.json")):
        try:
            with open(cand, encoding="utf-8") as f:
                p = json.load(f).get("comfyui_path")
            if p and os.path.isdir(os.path.join(p, "custom_nodes")):
                return p
        except Exception:
            continue
    return None


def backend_get(path, timeout=6):
    """请求 ComfyUI 后端，返回 dict 或 None。"""
    try:
        with urllib.request.urlopen(BACKEND + path, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def collect_system_info():
    """自动识别：运行环境 / 模型清单 / 插件 / 队列。"""
    info = {"version": VERSION, "backend_online": False}
    stats = backend_get("/system_stats")
    if not stats:
        return info
    info["backend_online"] = True
    info["version"] = stats.get("system", {}).get("comfyui_version", "")
    info["torch"] = stats.get("system", {}).get("pytorch_version", "")
    dev = (stats.get("devices") or [{}])[0]
    vram = dev.get("vram_total") or 0
    name = dev.get("name") or ""
    info["device"] = ("%s · %.0fGB" % (name, vram / 1024 ** 3)) if vram else name or "CPU/MPS"

    def names(node_cls, field):
        """兼容新旧 object_info 格式：
        旧: [["a","b"], {...}]  新: ["COMBO", {"options": [...]}]"""
        d = backend_get("/object_info/" + node_cls)
        try:
            spec = d[node_cls]["input"]["required"][field]
            if isinstance(spec, list) and spec:
                if spec[0] == "COMBO" and len(spec) > 1:
                    return list(spec[1].get("options") or [])
                return list(spec[0] or [])
            return []
        except Exception:
            return []

    info["checkpoints"] = sorted(names("CheckpointLoaderSimple", "ckpt_name"))
    comps = []
    comps += ["DiT:" + n for n in names("UNETLoader", "unet_name")]
    comps += ["编码器:" + n for n in names("CLIPLoader", "clip_name")]
    comps += ["VAE:" + n for n in names("VAELoader", "vae_name")]
    info["components"] = comps
    info["upscale_models"] = sorted(names("UpscaleModelLoader", "model_name"))

    root = find_comfy_root()
    plugins = []
    if root:
        cn = os.path.join(root, "custom_nodes")
        try:
            for name in sorted(os.listdir(cn)):
                if name.startswith((".", "__")):
                    continue
                if os.path.isdir(os.path.join(cn, name)):
                    plugins.append(name)
        except OSError:
            pass
    info["custom_nodes"] = plugins

    q = backend_get("/queue")
    info["queue"] = {"running": len((q or {}).get("queue_running") or []),
                     "pending": len((q or {}).get("queue_pending") or [])}
    return info


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _page(self):
        try:
            with open(PAGE, "rb") as f:
                data = f.read()
        except OSError:
            data = "页面文件缺失：一键生图.html".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        # 禁止缓存，防止浏览器用旧版页面导致"改了没生效"
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        """读取请求体，超过上限抛错。"""
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("request too large")
        return self.rfile.read(n) if n else b""

    def _proxy(self):
        url = BACKEND + self.path
        body = None
        if self.command == "POST":
            try:
                body = self._read_body()
            except ValueError:
                self._respond(413, json.dumps({"error": "请求体过大（上限 10MB）"}, ensure_ascii=False))
                return
        req = urllib.request.Request(url, data=body, method=self.command)
        req.add_header("Accept-Encoding", "identity")
        for key, val in self.headers.items():
            low = key.lower()
            # origin/sec-fetch 头会触发 ComfyUI 的跨源防护(403)，转发前剥掉
            if low in ("host", "connection", "origin", "referer", "sec-fetch-site") or low in HOP:
                continue
            req.add_header(key, val)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = r.read()
                self.send_response(r.status)
                for key, val in r.getheaders():
                    if key.lower() in HOP:
                        continue
                    self.send_header(key, val)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() in HOP:
                    continue
                self.send_header(key, val)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:  # 后端未启动等
            msg = ("ComfyUI 服务未就绪或请求失败：%s" % e).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _queue_guard(self):
        """提交前检查队列长度；超过上限返回 False 并回复 429。"""
        q = backend_get("/queue", timeout=3)
        running = len((q or {}).get("queue_running") or [])
        pending = len((q or {}).get("queue_pending") or [])
        if running + pending >= QUEUE_LIMIT:
            self._respond(429, json.dumps({"error": "队列已满（上限 %d 个任务），请稍候再试" % QUEUE_LIMIT},
                                          ensure_ascii=False))
            return False
        return True

    def _translate(self):
        """免费翻译（MyMemory API，无需密钥）。
        成功 → {"translated": "..."}
        超时/失败 → {"translated": "", "degraded": true}（页面降级按原文提交，不阻塞出图）
        """
        try:
            body = json.loads(self._read_body() or b"{}")
            text = str(body.get("text", "")).strip()
            if not text:
                raise ValueError("empty")
            url = ("https://api.mymemory.translated.net/get?q=%s&langpair=zh-CN|en-US"
                   % urllib.parse.quote(text[:480]))
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TRANSLATE_TIMEOUT) as r:
                out = json.loads(r.read())
            translated = (out.get("responseData") or {}).get("translatedText") or ""
            if not translated or "MYMEMORY WARNING" in translated:
                raise ValueError("bad result")
            self._respond(200, json.dumps({"translated": translated}, ensure_ascii=False))
        except Exception as e:
            self._log("翻译降级: %s" % e)
            self._respond(200, json.dumps({"translated": "", "degraded": True,
                                           "error": str(e)}, ensure_ascii=False))

    def _system_info(self):
        self._respond(200, json.dumps(collect_system_info(), ensure_ascii=False))

    def _respond(self, code, text):
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass

    def _log(self, msg):
        """带轮转的请求日志。"""
        path = os.path.join(HERE, "请求日志.log")
        try:
            if os.path.isfile(path) and os.path.getsize(path) > LOG_MAX:
                os.replace(path, path + ".old")
            with open(path, "a", encoding="utf-8") as f:
                f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg[:120]))
        except OSError:
            pass

    def do_GET(self):
        self._log("GET %s" % self.path[:80])
        if self.path in ("/", "/index.html"):
            self._page()
        elif self.path.startswith("/api/system-info"):
            self._system_info()
        else:
            self._proxy()

    def do_POST(self):
        self._log("POST %s" % self.path[:80])
        if self.path.startswith("/translate"):
            self._translate()
        elif self.path.startswith("/prompt"):
            if self._queue_guard():
                self._proxy()
        else:
            self._proxy()

    def do_DELETE(self):
        self._log("DELETE %s" % self.path[:80])
        self._proxy()


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    if port_in_use(PORT):
        print("端口 %d 已被占用：生图台可能已在运行（浏览器打开 http://127.0.0.1:%d 即可）。" % (PORT, PORT))
        print("如确认没有在运行，请换端口后重启，或先结束旧进程：pkill -f 生图服务器.py")
        raise SystemExit(1)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("闪电生图台 v%s 就绪: http://127.0.0.1:%d （转发后端 %s）" % (VERSION, PORT, BACKEND))
    srv.serve_forever()
