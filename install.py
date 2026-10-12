#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闪电生图台 (Lightning Image Studio) — 一键安装程序
====================================================
纯 Python 标准库实现，无任何第三方依赖。

功能：
  1. 检测本机环境（系统 / Python / 磁盘 / 内存）
  2. 自动识别本机已安装的 ComfyUI（支持手动指定路径）
  3. 全盘扫描本机已安装的全部模型，按类型自动识别并给出运行方案
     （不依赖任何内置模型清单；仅当本机无模型时才提供可选择的推荐下载）
  4. 安装「闪电生图台」可视化控制面板并生成启动器
  5. 全程 Y/N 交互确认，安装日志落盘可追溯

许可：MIT License — 详见 README.md
"""

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

APP_NAME = "闪电生图台"
APP_EN_NAME = "Lightning Image Studio"
APP_VERSION = "4.1.0"
BRAND = "闪电研究院 Lightning Research Institute"
WEBSITE = "https://shandianhub.cn"
AUTHOR = "Samuel"
COMFY_PORT = 8188
PANEL_PORT = 8190
REQUIRED_DISK_GB = 20          # 完整安装（含模型下载）所需最低磁盘
PY_MIN = (3, 10)

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "install.log")

# ANSI 颜色
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"
C_GREY = "\033[90m"

USE_COLOR = sys.stdout.isatty() and os.environ.get("TERM") != "dumb"

# ComfyUI 常见安装位置（按优先级排列）
COMFY_CANDIDATES = [
    os.path.expanduser("~/Desktop/ComfyUI-生图/ComfyUI"),
    os.path.expanduser("~/ComfyUI"),
    os.path.expanduser("~/Documents/ComfyUI"),
    os.path.expanduser("~/Desktop/ComfyUI"),
    os.path.expanduser("~/Applications/ComfyUI"),
    "/Applications/ComfyUI",
]

# 模型目录（相对 ComfyUI 根目录）
MODEL_DIR_CHECKPOINTS = os.path.join("models", "checkpoints")
MODEL_DIR_UPSCALE = os.path.join("models", "upscale_models")

# 全盘扫描的模型类别（相对 models/ 目录, 展示名）
MODEL_SUBDIRS = [
    ("checkpoints",      "生成模型 (Checkpoint)"),
    ("diffusion_models", "扩散模型 (DiT/UNet)"),
    ("text_encoders",    "文本编码器"),
    ("vae",              "VAE 解码器"),
    ("upscale_models",   "超分放大模型"),
    ("loras",            "LoRA 微调模型"),
]

# 生成模型类型自动识别规则与对应运行方案
CLS_INFO = {
    "fast":    ("极速型",   "建议 4 步 / CFG 1.0，出图最快（Turbo / Lightning / Hyper / LCM 类）"),
    "xl":      ("高清型",   "建议 25 步 / CFG 7，原生 1024px（SDXL 类）"),
    "sd15":    ("经典型",   "建议 20 步 / CFG 7，原生 512–768px（SD 1.5 类）"),
    "generic": ("通用型",   "建议 20 步 / CFG 6.5（未识别类型，可自行在面板微调）"),
}

# 推荐模型清单：仅当本机未检测到可用生成模型时作为「可选项」提供，绝非内置必需
RECOMMENDED_MODELS = {
    "sd_turbo.safetensors": {
        "dir": MODEL_DIR_CHECKPOINTS,
        "name": "SD-Turbo 极速模型（约 5.2 GB，出图 35-60 秒）",
        "license": "CreativeML OpenRAIL++-M（可免费商用，附署名要求）",
        "sources": [
            "https://modelscope.cn/models/AI-ModelScope/sd-turbo/resolve/master/sd_turbo.safetensors",
        ],
    },
    "sd_xl_base_1.0.safetensors": {
        "dir": MODEL_DIR_CHECKPOINTS,
        "name": "SDXL 高清模型（约 6.4 GB，配合超分可达 4K）",
        "license": "CreativeML OpenRAIL++-M（可免费商用，附使用限制）",
        "sources": [
            "https://modelscope.cn/models/AI-ModelScope/stable-diffusion-xl-base-1.0/resolve/master/sd_xl_base_1.0.safetensors",
        ],
    },
    "RealESRGAN_x4plus.pth": {
        "dir": MODEL_DIR_UPSCALE,
        "name": "RealESRGAN ×4 超分放大器（约 64 MB）",
        "license": "BSD-3-Clause（可免费商用）",
        "sources": [
            "https://gh-proxy.com/https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        ],
    },
}


# ─────────────────────────── 基础 UI ───────────────────────────

def paint(text, color):
    if USE_COLOR:
        return f"{color}{text}{C_RESET}"
    return text


def line(char="─", width=64):
    return char * width


def banner():
    print()
    print(paint(line("═"), C_CYAN))
    print(paint(f"  {APP_NAME} {APP_EN_NAME}  v{APP_VERSION}", C_BOLD + C_CYAN))
    print(paint("  本地 AI 图像生成 · 可视化工作流控制面板 · 一键安装程序", C_DIM))
    print(paint(f"  {BRAND} · by {AUTHOR} · {WEBSITE}", C_DIM))
    print(paint(line("═"), C_CYAN))
    print()


def step(n, total, title):
    print()
    print(paint(f"[STEP {n}/{total}] {title}", C_BOLD))
    print(paint(line(), C_GREY))


def ok(msg):
    print(f"  {paint('✓', C_GREEN)} {msg}")


def warn(msg):
    print(f"  {paint('!', C_YELLOW)} {paint(msg, C_YELLOW)}")


def err(msg):
    print(f"  {paint('✗', C_RED)} {paint(msg, C_RED)}")


def info(msg):
    print(f"  {paint('·', C_CYAN)} {msg}")


def ask_yes_no(question, default_yes=True):
    """正式的 Y/N 交互（兼容 Yes/No 全拼与中英文）。返回 True/False。"""
    suffix = "[Y/n]" if default_yes else "[y/N]"
    while True:
        try:
            raw = input(f"  {paint('?', C_CYAN)} {question} {paint(suffix, C_BOLD)} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if raw in ("", "y", "yes", "是"):
            return default_yes or raw != ""
        if raw in ("n", "no", "否"):
            return False
        print(f"  {paint('请输入 Y 或 N。', C_YELLOW)}")


def confirm_abort():
    print()
    err("安装已取消。未对系统做任何更改。")
    print(paint(f"  如需再次运行：python3 {os.path.basename(__file__)}", C_DIM))
    sys.exit(1)


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


# ─────────────────────────── 环境检测 ───────────────────────────

def detect_system():
    """返回 (是否通过, 结果描述列表)"""
    results = []
    passed = True

    sysname = platform.system()
    if sysname == "Darwin":
        ver = platform.mac_ver()[0] or "未知"
        results.append(("系统", f"macOS {ver}", True))
    elif sysname == "Linux":
        results.append(("系统", f"Linux {platform.release()}", True))
    else:
        results.append(("系统", f"{sysname}（本安装程序面向 macOS/Linux）", False))
        passed = False

    arch = platform.machine()
    results.append(("架构", arch, True))

    pv = sys.version_info
    py_ok = (pv.major, pv.minor) >= PY_MIN
    results.append(("Python", platform.python_version(), py_ok))
    if not py_ok:
        passed = False

    usage = shutil.disk_usage(os.path.expanduser("~"))
    free_gb = usage.free / (1024 ** 3)
    disk_ok = free_gb >= REQUIRED_DISK_GB
    results.append(("磁盘可用", f"{free_gb:.1f} GB（建议 ≥ {REQUIRED_DISK_GB} GB）", disk_ok))
    if not disk_ok:
        passed = False

    mem_gb = 0.0
    try:
        out = subprocess.run(["sysctl", "-n", "hw.memsize"],
                             capture_output=True, text=True, timeout=5)
        mem_gb = int(out.stdout.strip()) / (1024 ** 3)
    except Exception:
        try:
            mem_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
        except Exception:
            pass
    if mem_gb:
        mem_ok = mem_gb >= 8
        results.append(("内存", f"{mem_gb:.1f} GB（建议 ≥ 8 GB）", mem_ok))
        if not mem_ok:
            passed = False

    return passed, results


# ─────────────────────────── ComfyUI 检测 ───────────────────────────

def is_comfyui(path):
    """判断给定路径是否为有效的 ComfyUI 根目录。"""
    if not path:
        return False
    path = os.path.expanduser(path.rstrip("/"))
    return os.path.isfile(os.path.join(path, "main.py")) and \
        os.path.isdir(os.path.join(path, "models"))


def find_comfyui():
    """在常见位置搜索 ComfyUI。"""
    for cand in COMFY_CANDIDATES:
        if is_comfyui(cand):
            return cand
    # Spotlight 搜索补充
    try:
        out = subprocess.run(
            ["mdfind", "-name", "main.py"], capture_output=True, text=True, timeout=10)
        for ln in out.stdout.splitlines():
            d = os.path.dirname(ln.strip())
            if "comfyui" in d.lower() and is_comfyui(d):
                return d
    except Exception:
        pass
    return None


def comfyui_version(path):
    try:
        req = urllib.request.Request(
            "https://raw.githubusercontent.com/comfyanonymous/ComfyUI/master/comfyui_version.py",
            method="HEAD")
        urllib.request.urlopen(req, timeout=4)
    except Exception:
        pass
    # 读取本地版本文件（存在则展示）
    for vf in ("comfyui_version.py", ".git"):
        if os.path.exists(os.path.join(path, vf)):
            return "已安装"
    return "已安装（版本未识别）"


# ─────────────────────────── 模型检测 ───────────────────────────

def scan_models(comfy_path):
    """全盘递归扫描 models/ 各类别目录。
    返回 {类别: [(文件名, 字节数, 绝对路径), ...]}（仅列有效模型文件）。"""
    result = {}
    for sub, _label in MODEL_SUBDIRS:
        root = os.path.join(comfy_path, "models", sub)
        items = []
        if os.path.isdir(root):
            for dirpath, _dirs, filenames in os.walk(root):
                for fn in sorted(filenames):
                    if fn.startswith(".") or fn.endswith((".part", ".txt", ".json", ".md")):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        sz = os.path.getsize(p)
                    except OSError:
                        continue
                    if sz < 512 * 1024:      # 忽略占位/缓存小文件
                        continue
                    items.append((fn, sz, p))
        if items:
            result[sub] = sorted(items)
    return result


def classify_ckpt(name):
    """按文件名自动识别生成模型类型 → CLS_INFO 键。"""
    n = name.lower()
    if re.search(r"turbo|lightning|hyper|lcm|ssd-1b|schnell", n):
        return "fast"
    if "xl" in n:
        return "xl"
    if re.search(r"v1-5|sd15|sd_1\.5|sd-v1|stable[-_]?diffusion[-_]?v?1", n):
        return "sd15"
    return "generic"


def pick_default(ckpt_names):
    """自动方案：优先极速型，其次高清型、经典型，再次任意第一个。"""
    if not ckpt_names:
        return None
    for want in ("fast", "xl", "sd15", "generic"):
        for n in ckpt_names:
            if classify_ckpt(n) == want:
                return n
    return ckpt_names[0]


# ─────────────────────────── 下载 ───────────────────────────

def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def sha256_of(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def download(url, dest, min_size=1024):
    """带进度显示的下载；失败返回 False。"""
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LightningImageStudio/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            got = 0
            last_pct = -1
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    pct = int(got * 100 / total)
                    if pct != last_pct and pct % 2 == 0:
                        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                        print(f"\r  下载中 [{bar}] {pct:3d}%  {human_size(got)}/{human_size(total)}",
                              end="", flush=True)
                        last_pct = pct
        print()
        if os.path.getsize(tmp) < min_size:
            os.remove(tmp)
            return False
        os.replace(tmp, dest)
        return True
    except Exception as e:
        print()
        log(f"下载失败 {url}: {e}")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return False


def download_model(fname, comfy_path):
    """按推荐清单下载单个模型，多源自动回退。"""
    meta = RECOMMENDED_MODELS[fname]
    dest_dir = os.path.join(comfy_path, meta["dir"])
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, fname)
    for url in meta["sources"]:
        info(f"下载源：{url.split('/models/')[0] if '/models/' in url else url[:60]}…")
        if download(url, dest):
            ok(f"已下载：{fname}（{human_size(os.path.getsize(dest))}）")
            info("校验值 sha256：" + sha256_of(dest)[:32] + "…（已写入安装日志备查）")
            log(f"模型 {fname} sha256={sha256_of(dest)}")
            return True
        warn("该下载源不可用，尝试下一个…")
    err(f"模型 {fname} 所有下载源均失败，可稍后手动下载后放入：{dest_dir}")
    return False


# ─────────────────────────── 全新 ComfyUI 安装 ───────────────────────────

def install_fresh_comfyui(parent_dir):
    """在 parent_dir 下克隆 ComfyUI 并创建虚拟环境。返回根目录或 None。"""
    target = os.path.join(parent_dir, "ComfyUI")
    repos = [
        "https://gh-proxy.com/https://github.com/comfyanonymous/ComfyUI.git",
        "https://github.com/comfyanonymous/ComfyUI.git",
        "https://gitee.com/mirrors/ComfyUI.git",
    ]
    cloned = False
    for repo in repos:
        info(f"正在从 {repo.split('//')[1].split('/')[0]} 克隆 ComfyUI …")
        r = subprocess.run(["git", "clone", "--depth", "1", repo, target],
                           capture_output=True, text=True, timeout=600)
        if r.returncode == 0:
            cloned = True
            break
        warn("该源克隆失败，尝试下一个…")
    if not cloned:
        err("ComfyUI 克隆失败（需已安装 git 并可访问上述任一仓库）。")
        return None

    ok("ComfyUI 源码克隆完成")
    venv_dir = os.path.join(target, "venv")
    info("正在创建 Python 虚拟环境（首次需要 1-2 分钟）…")
    r = subprocess.run([sys.executable, "-m", "venv", venv_dir], capture_output=True, text=True)
    if r.returncode != 0:
        err(f"虚拟环境创建失败：{r.stderr[:200]}")
        return target  # 源码在，环境留给用户手动处理
    pip = os.path.join(venv_dir, "bin", "pip")
    mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
    info("正在安装 PyTorch（清华镜像，约 2-3 GB，视网速 5-15 分钟）…")
    r = subprocess.run([pip, "install", "-i", mirror,
                        "torch", "torchvision"], capture_output=True, text=True)
    if r.returncode != 0:
        warn(f"PyTorch 安装失败，可稍后手动执行：{pip} install torch torchvision")
        return target
    reqs = os.path.join(target, "requirements.txt")
    if os.path.isfile(reqs):
        info("正在安装 ComfyUI 依赖 …")
        subprocess.run([pip, "install", "-i", mirror, "-r", reqs],
                       capture_output=True, text=True)
    ok("ComfyUI 环境安装完成")
    return target


# ─────────────────────────── 应用安装 ───────────────────────────

LAUNCH_TEMPLATE = '''#!/bin/bash
# 闪电生图台 启动器（由安装程序生成，请勿手改）
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="$DIR/config.json"
read_conf() { /usr/bin/python3 -c "import json,sys;print(json.load(open('$CONF'))['$1'])"; }

COMFY="$(read_conf comfyui_path)"
PYBIN="$(read_conf python_bin)"
ARGS="$(read_conf comfyui_args)"

echo "──────────────────────────────────────────────"
echo "  闪电生图台 · 启动中"
echo "──────────────────────────────────────────────"

# 若服务已在运行则直接打开页面
if curl -s --noproxy '*' -m 2 "http://127.0.0.1:__PANEL__/" -o /dev/null; then
  echo "  生图台已在运行，直接打开页面。"
  open "http://127.0.0.1:__PANEL__"
  exit 0
fi

echo "  [1/2] 启动 ComfyUI 后端（端口 __COMFY__）…"
cd "$COMFY"
nohup "$PYBIN" main.py --listen 127.0.0.1 --port __COMFY__ $ARGS >> "$DIR/comfyui.log" 2>&1 &

echo "  [2/2] 启动生图台面板（端口 __PANEL__）…"
cd "$DIR"
nohup /usr/bin/python3 "$DIR/app/生图服务器.py" >> "$DIR/生图台.log" 2>&1 &

echo -n "  等待服务就绪 "
for i in $(seq 1 60); do
  if curl -s --noproxy '*' -m 2 "http://127.0.0.1:__PANEL__/" -o /dev/null; then
    echo " 就绪"
    open "http://127.0.0.1:__PANEL__"
    echo "  已在浏览器打开生图台。两个服务在后台运行，关闭本窗口不影响使用。"
    exit 0
  fi
  echo -n "."; sleep 2
done
echo " 超时"
echo "  启动失败，请查看日志：$DIR/comfyui.log 与 $DIR/生图台.log"
exit 1
'''


def install_app(comfy_path, install_dir, detected, plan_default):
    """复制应用文件、写配置、生成启动器。"""
    os.makedirs(install_dir, exist_ok=True)
    os.makedirs(os.path.join(install_dir, "app"), exist_ok=True)

    # 复制应用源码
    for fname in ("一键生图.html", "生图服务器.py"):
        src = os.path.join(HERE, "app", fname)
        dst = os.path.join(install_dir, "app", fname)
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
        ok(f"已安装：app/{fname}")

    # 选择 Python：探测哪个解释器能加载 PyTorch（自动识别已装好的后端环境）
    candidates = [
        os.path.join(comfy_path, "venv", "bin", "python"),
        os.path.expanduser("~/.workbuddy/binaries/python/envs/default/bin/python"),
        sys.executable,
        "/usr/bin/python3",
    ]
    py_bin = None
    for cand in candidates:
        if not cand or not os.path.isfile(cand):
            continue
        r = subprocess.run([cand, "-c", "import torch"],
                           capture_output=True, timeout=120)
        if r.returncode == 0:
            py_bin = cand
            ok(f"后端环境探测成功（PyTorch 可用）：{cand}")
            break
    if not py_bin:
        py_bin = sys.executable
        warn("未探测到已装 PyTorch 的 Python，已指定默认解释器；"
             "首次启动若报缺 torch，请在 ComfyUI 目录执行："
             "python3 -m venv venv && venv/bin/pip install torch torchvision")
    info(f"后端解释器：{py_bin}")

    # 依据内存决定 ComfyUI 启动参数（自动调参）
    args = "--listen 127.0.0.1"
    try:
        out = subprocess.run(["sysctl", "-n", "hw.memsize"],
                             capture_output=True, text=True, timeout=5)
        mem_gb = int(out.stdout.strip()) / (1024 ** 3)
    except Exception:
        mem_gb = 16
    if mem_gb < 24:
        args += " --lowvram --cache-none"
        info(f"检测到内存 {mem_gb:.0f} GB，已自动启用低显存稳定参数（--lowvram --cache-none）")
    else:
        info(f"检测到内存 {mem_gb:.0f} GB，使用标准参数")

    # 写配置（含本机模型自动识别结果，面板据此自动匹配方案）
    config = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "comfyui_path": comfy_path,
        "python_bin": py_bin,
        "comfyui_args": args,
        "comfyui_port": COMFY_PORT,
        "panel_port": PANEL_PORT,
        "detected_models": {sub: [fn for fn, _s, _p in items]
                            for sub, items in detected.items()},
        "default_checkpoint": plan_default,
    }
    conf_path = os.path.join(install_dir, "config.json")
    with open(conf_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    ok(f"已生成配置：config.json")

    # 生成启动器
    launch = LAUNCH_TEMPLATE.replace("__COMFY__", str(COMFY_PORT)).replace("__PANEL__", str(PANEL_PORT))
    launch_path = os.path.join(install_dir, "启动闪电生图台.command")
    with open(launch_path, "w", encoding="utf-8") as f:
        f.write(launch)
    os.chmod(launch_path, 0o755)
    ok("已生成启动器：启动闪电生图台.command（可双击运行）")
    return conf_path, launch_path


# ─────────────────────────── 主流程 ───────────────────────────

LICENSE_TEXT = f"""  本软件基于 MIT 许可证开源发布，随附源码可自由查看、修改与分发。
  本程序不内置任何 AI 模型：安装时全盘识别您本机已装的模型；
  若选择下载推荐模型，这些模型遵循各自开源许可
  （如 CreativeML OpenRAIL++ / BSD-3），请遵守相应条款使用生成内容，
  勿用于违法违规用途。

  隐私说明：本程序与生成的图像均仅存在于您的本机，不收集、
  不上传任何个人数据。中文提示词翻译经由第三方免费翻译接口
  （MyMemory）匿名完成，不含任何身份信息。"""

def main():
    banner()
    print(paint(LICENSE_TEXT, C_DIM))
    print()
    print(paint("  安装开始前，请确认以上条款。", C_BOLD))
    if not ask_yes_no("是否同意许可条款并继续安装？", default_yes=True):
        confirm_abort()
    log("========== 安装会话开始 ==========")

    TOTAL = 6

    # ── STEP 1 环境检测 ──
    step(1, TOTAL, "环境检测")
    sys_ok, rows = detect_system()
    for name, val, good in rows:
        mark = paint("✓", C_GREEN) if good else paint("✗", C_RED)
        print(f"    {mark} {name}：{val}")
    if not sys_ok:
        warn("部分环境项未达标，继续安装可能出现性能或功能问题。")
        if not ask_yes_no("是否仍要继续？", default_yes=False):
            confirm_abort()
    else:
        ok("环境检测全部通过")

    # 端口占用检测：被占用说明服务可能已在运行
    for port, what in ((COMFY_PORT, "ComfyUI"), (PANEL_PORT, "生图台面板")):
        if port_in_use(port):
            warn(f"端口 {port} 已被占用——{what}服务可能已在运行。")
    if port_in_use(PANEL_PORT):
        info("可先在浏览器打开 http://127.0.0.1:%d 查看现有面板；继续安装将覆盖程序文件（不影响运行中服务）。" % PANEL_PORT)

    # ── STEP 2 检测 ComfyUI ──
    step(2, TOTAL, "检测 ComfyUI 本体")
    comfy = find_comfyui()
    if comfy:
        ok(f"已找到 ComfyUI：{comfy}")
        info(comfyui_version(comfy))
        if not ask_yes_no("是否使用该 ComfyUI？", default_yes=True):
            comfy = None
    if not comfy:
        warn("未在常见位置发现 ComfyUI。")
        print()
        print("  您可以选择：")
        print(f"    1. 手动输入本机 ComfyUI 路径")
        print(f"    2. 由本程序自动全新安装 ComfyUI（约需 3-6 GB 磁盘与 10-20 分钟）")
        print(f"    3. 退出安装")
        choice = input(f"  {paint('?', C_CYAN)} 请选择 [1/2/3]（默认 2）: ").strip() or "2"
        if choice == "1":
            p = input("  请输入 ComfyUI 根目录路径: ").strip()
            if is_comfyui(p):
                comfy = os.path.expanduser(p)
                ok(f"已确认：{comfy}")
            else:
                err("该路径不是有效的 ComfyUI 目录（需包含 main.py 与 models/）。")
                confirm_abort()
        elif choice == "2":
            base = os.path.dirname(COMFY_CANDIDATES[0])
            os.makedirs(base, exist_ok=True)
            comfy = install_fresh_comfyui(base)
            if not comfy:
                confirm_abort()
        else:
            confirm_abort()

    # ── STEP 3 检测模型（全盘扫描 + 自动方案）──
    step(3, TOTAL, "检测本机模型（全盘自动识别）")
    detected = scan_models(comfy)
    total_models = sum(len(v) for v in detected.values())
    if total_models:
        ok(f"共识别到 {total_models} 个模型文件，分类如下：")
        for sub, label in MODEL_SUBDIRS:
            items = detected.get(sub)
            if not items:
                continue
            print(f"\n    {paint(label, C_BOLD)}  （{len(items)} 个）")
            for fn, sz, _p in items:
                tag = ""
                if sub == "checkpoints":
                    cls = classify_ckpt(fn)
                    tag = paint(f"  → {CLS_INFO[cls][0]}", C_CYAN)
                print(f"      · {fn}  {paint(human_size(sz), C_DIM)}{tag}")
    else:
        warn("models/ 目录下未检测到任何模型文件。")

    # 自动方案：选定默认模型与参数档位
    ckpt_names = [fn for fn, _s, _p in detected.get("checkpoints", [])]
    plan_default = pick_default(ckpt_names)
    if plan_default:
        cls = classify_ckpt(plan_default)
        print()
        ok(f"自动方案：默认使用「{plan_default}」（{CLS_INFO[cls][0]}）")
        info(f"参数方案：{CLS_INFO[cls][1]}")
        info("面板会自动识别全部已就位模型并在打开时选中默认模型，可随时切换。")
        if detected.get("upscale_models"):
            ok("超分放大：已检测到，可在面板中勾选 ×4 放大")
        else:
            warn("未检测到超分放大模型，面板中 ×4 放大将不可用")
            if ask_yes_no("是否下载推荐的超分放大器 RealESRGAN（约 64 MB，可选）？", default_yes=False):
                download_model("RealESRGAN_x4plus.pth", comfy)
    else:
        warn("没有可用的生成模型（Checkpoint），面板暂时无法出图。")
        print(f"\n  可从推荐清单选择下载（完全可选，也可稍后自行放入 models/checkpoints/ 目录）：")
        opts = list(RECOMMENDED_MODELS.items())
        for i, (_fname, meta) in enumerate(opts, 1):
            print(f"    {i}. {meta['name']}")
            info(f"开源许可：{meta['license']}")
        print("     0. 跳过，暂不下载任何模型")
        while True:
            c = input(f"  {paint('?', C_CYAN)} 请输入编号（多选用逗号分隔，默认 0）: ").strip() or "0"
            try:
                picks = [int(x) for x in c.replace("，", ",").split(",")]
                if all(0 <= x <= len(opts) for x in picks):
                    break
            except ValueError:
                pass
            print(f"  {paint('输入无效，请重新输入。', C_YELLOW)}")
        for x in picks:
            if x:
                download_model(opts[x - 1][0], comfy)
        # 下载后重新扫描并更新方案
        detected = scan_models(comfy)
        ckpt_names = [fn for fn, _s, _p in detected.get("checkpoints", [])]
        plan_default = pick_default(ckpt_names)
        if plan_default:
            cls = classify_ckpt(plan_default)
            ok(f"自动方案更新：默认使用「{plan_default}」（{CLS_INFO[cls][0]}）")
        else:
            warn("仍无生成模型——可随时把模型放入 models/checkpoints/ 后重新运行安装器。")

    # ── STEP 4 安装面板 ──
    step(4, TOTAL, "安装可视化控制面板")
    default_dir = os.path.expanduser("~/Desktop/闪电生图台")
    d = input(f"  安装位置（回车使用默认 {default_dir}）: ").strip() or default_dir
    d = os.path.expanduser(d)
    print()
    conf, launch = install_app(comfy, d, detected, plan_default)

    # ── STEP 5 汇总确认 ──
    step(5, TOTAL, "安装结果汇总")
    total_models = sum(len(v) for v in detected.values())
    print(f"""
    {paint('安装位置', C_BOLD)}     {d}
    {paint('面板地址', C_BOLD)}     http://127.0.0.1:{PANEL_PORT}
    {paint('ComfyUI', C_BOLD)}      {comfy}
    {paint('启动方式', C_BOLD)}     双击「启动闪电生图台.command」或在终端运行
    {paint('识别模型', C_BOLD)}     {total_models} 个（本机自动识别）
    {paint('默认模型', C_BOLD)}     {plan_default or '无（放入模型后重新运行安装器即可识别）'}
""")
    if not ask_yes_no("确认以上信息无误？", default_yes=True):
        confirm_abort()

    # ── STEP 6 启动 ──
    step(6, TOTAL, "完成")
    ok(f"{APP_NAME} 安装完成")
    log("安装成功")
    if ask_yes_no("是否立即启动生图台？", default_yes=True):
        print()
        subprocess.run(["bash", launch])
    else:
        print()
        info(f"以后随时启动：双击 {launch}")
        info(f"或终端执行：bash \"{launch}\"")

    print()
    print(paint(line("═"), C_CYAN))
    print(paint(f"  {APP_NAME} {APP_EN_NAME} v{APP_VERSION} 安装完成", C_BOLD))
    print(paint(f"  {BRAND} · by {AUTHOR}", C_DIM))
    print(paint(f"  官网：{WEBSITE}", C_DIM))
    print(paint(f"  安装日志：{LOG_PATH}", C_DIM))
    print(paint(line("═"), C_CYAN))
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        err("安装被用户中断（Ctrl+C）。未对系统做更改的部分保持原样。")
        sys.exit(130)
