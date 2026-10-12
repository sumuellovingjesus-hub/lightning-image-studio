# ⚡ Lightning Image Studio

**Local AI image generation · Visual control panel · One-click installer · Free & open source**

[中文](README.md) · Website: [shandianhub.cn](https://shandianhub.cn) · By Lightning Research Institute (Samuel)

---

A visual control panel on top of a local [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installation. No nodes, no wiring — just type a prompt in any language and generate. The original ComfyUI workflow UI stays one click away.

## ✨ Features

- **One-click install**: interactive terminal installer (Y/N), auto-detects environment, finds your local ComfyUI and models, downloads missing models from mirrors
- **Any-language prompts**: built-in auto-translation (can be disabled)
- **Fully adjustable**: size / steps / CFG / sampler / scheduler / seed / batch / ×4 upscale
- **Auto-detection**: scans local models, custom nodes, runtime info and queue status on launch
- **Bilingual UI**: 中文 / English one-click switch
- **Light / Dark theme**: including follow-system
- **Settings center**: language, theme, translation, default model, upscale, history size — all remembered locally
- **Privacy first**: runs 100% locally, no images or personal data ever uploaded

## 🚀 Quick Start

```bash
git clone https://github.com/<your-username>/lightning-image-studio.git
cd lightning-image-studio
python3 install.py
```

Or download the zip and double-click `安装闪电生图台.command` (macOS).

Daily use: run the generated `启动闪电生图台.command`, then open `http://127.0.0.1:8190`.

## 🖥 Requirements

| Item | Minimum | Recommended |
|------|---------|-------------|
| OS | macOS 13+ / Linux | macOS 14+ (Apple Silicon tested) |
| Python | 3.10 | 3.10 – 3.12 |
| RAM | 8 GB | 16 GB+ |
| Disk | 20 GB (incl. models) | 30 GB |
| Network | Only for install & model download; generation works offline | — |

> Machines with ≤ 16 GB RAM automatically get low-memory flags (`--lowvram --cache-none`).

## 📦 Bundled Models

| Model | Purpose | Speed (16GB M4) | License |
|-------|---------|-----------------|---------|
| SD-Turbo | Fast generation (default) | 5–60 s/image | CreativeML OpenRAIL++-M |
| SDXL Base 1.0 | Hi-res + 4K upscale | 5–15 min/image | CreativeML OpenRAIL++-M |
| RealESRGAN ×4+ | Upscaler | seconds | BSD-3-Clause |

## 📖 Docs (Chinese)

- [安装指南 Install Guide](docs/安装指南.md) · [使用教程 Usage](docs/使用教程.md) · [常见问题 FAQ](docs/常见问题.md)

## 🤝 Contributing

Issues and PRs welcome. Please run `python3 install.py` end-to-end before submitting to avoid regressions.

## 📄 License

Code: [MIT](LICENSE). Bundled models keep their original licenses (OpenRAIL++ / BSD-3).

---

Lightning Research Institute · [shandianhub.cn](https://shandianhub.cn)
