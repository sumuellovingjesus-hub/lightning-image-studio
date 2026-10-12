# ⚡ Lightning Image Studio

**Local AI image generation · Visual control panel · One-click installer · Free & open source**

[中文](README.md) · Website: [shandianhub.cn](https://shandianhub.cn) · By Lightning Research Institute (Samuel)

---

A visual control panel on top of a local [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installation. No nodes, no wiring — just type a prompt in any language and generate. The original ComfyUI workflow UI stays one click away.

## 🖼 Screenshots

**Main panel (light / dark, one-click switch)** — full parameter console on the left, results & history on the right:

| Light | Dark |
|---|---|
| ![Light panel](docs/screenshots/panel-light-zh.png) | ![Dark panel](docs/screenshots/panel-dark-zh.png) |

**Terminal one-click installer** — formal interactive flow: license → environment check → auto-detection, Y/N at every step:

![Installer](docs/screenshots/installer.png)

**System info · auto-detected** — the panel scans and lists ComfyUI version, PyTorch, device, **all local models**, **custom nodes** and queue status on launch:

![System info](docs/screenshots/sysinfo.png)

**Settings center** — language, theme, translation, default model, upscale, history size; all persisted locally:

| Settings | English UI |
|---|---|
| ![Settings](docs/screenshots/settings.png) | ![English UI](docs/screenshots/panel-en-dark.png) |

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
git clone https://github.com/sumuellovingjesus-hub/lightning-image-studio.git
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

## 📦 Models: Zero Bundled, Fully Auto-Detected

This program **does not bundle any models**. Both the installer and the panel scan your local ComfyUI `models/` directories and support whatever they find, auto-classifying each model and matching a parameter preset by filename:

| Detected class | Auto-matched preset | Speed (16GB M4, measured) |
|------|------|------|
| Fast (Turbo / Lightning / Hyper / LCM) | 4 steps / CFG 1.0 | 5–60 s/image |
| Hi-res (SDXL) | 25 steps / CFG 7, native 1024px | 5–15 min/image |
| Classic (SD 1.5) | 20 steps / CFG 7, native 512–768px | dozens of seconds–minutes |
| Generic (unrecognized) | 20 steps / CFG 6.5, fine-tune in panel | varies |
| Z-Image (DiT + Qwen encoder, native Chinese) | 8 steps / CFG 1.0 | ~90 min/image (not recommended on 16GB) |

- Whatever checkpoints exist locally become panel buttons; the fast one is picked as default automatically
- Upscale models (e.g. RealESRGAN ×4) are auto-detected too — the ×4 option appears only when one exists
- With no models present, the installer offers a **fully optional** recommendation list (with license info), or you can drop models into `models/checkpoints/` later

## 📖 Docs (Chinese)

- [安装指南 Install Guide](docs/安装指南.md) · [使用教程 Usage](docs/使用教程.md) · [常见问题 FAQ](docs/常见问题.md)

## 🤝 Contributing

Issues and PRs welcome. Please run `python3 install.py` end-to-end before submitting to avoid regressions.

## 📄 License

Code: [MIT](LICENSE). Bundled models keep their original licenses (OpenRAIL++ / BSD-3).

---

Lightning Research Institute · [shandianhub.cn](https://shandianhub.cn)
