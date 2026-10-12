# ⚡ 闪电生图台 Lightning Image Studio

**本地 AI 图像生成 · 可视化控制面板 · 一键安装 · 完全免费开源**

[English](README_EN.md) · 官网：[shandianhub.cn](https://shandianhub.cn) · 出品：闪电研究院 Lightning Research Institute · by Samuel

---

一个部署在本机 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 之上的可视化控制面板。不懂节点、不用连线，中文描述直接出图；同时保留一键跳转 ComfyUI 原版工作流界面的入口。

## ✨ 特性

- **一键安装**：终端交互式安装器（Y/N 确认），自动检测环境、自动识别本机 ComfyUI 与模型，缺失模型可自动下载（国内镜像）
- **中文直出**：内置自动翻译，中文提示词自动转为英文提交（可关闭）
- **全参数可调**：尺寸 / 步数 / CFG / 采样器 / 调度器 / 种子 / 批量 / 超分放大
- **自动识别**：启动即扫描本机模型清单、已装插件、运行环境与队列状态，直接展示在面板上
- **中英双语**：界面一键切换中文 / English
- **亮暗主题**：亮色 / 暗色 / 跟随系统
- **设置中心**：语言、主题、翻译、默认模型、默认超分、历史记录条数，全部本地记忆
- **隐私优先**：完全本地运行，不上传任何图像与个人数据

## 🚀 快速开始

```bash
git clone https://github.com/<你的用户名>/lightning-image-studio.git
cd lightning-image-studio
python3 install.py
```

或下载仓库 zip 后直接双击运行（macOS）：

```
安装闪电生图台.command
```

安装器会引导你完成：环境检测 → ComfyUI 识别（未安装可自动全新安装）→ 模型识别与补全 → 面板安装 → 启动。

日常使用：双击生成的 `启动闪电生图台.command`，浏览器自动打开 `http://127.0.0.1:8190`。

## 🖥 系统要求

| 项目 | 最低 | 推荐 |
|------|------|------|
| 系统 | macOS 13+ / Linux | macOS 14+（Apple Silicon 实测流畅） |
| Python | 3.10 | 3.10 – 3.12 |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 20 GB（含模型） | 30 GB |
| 网络 | 仅安装和下载模型时需要，生成阶段可离线 | — |

> 16 GB 及以下内存自动启用低显存稳定参数（`--lowvram --cache-none`）。

## 📦 内置模型

| 模型 | 用途 | 速度（16GB M4 实测） | 许可 |
|------|------|------|------|
| SD-Turbo | 极速生图（默认） | 5–60 秒/张 | CreativeML OpenRAIL++-M |
| SDXL Base 1.0 | 高清 + 超分 4K | 5–15 分钟/张 | CreativeML OpenRAIL++-M |
| RealESRGAN ×4+ | 超分放大 | 数秒 | BSD-3-Clause |

## 📁 仓库结构

```
lightning-image-studio/
├── install.py               一键安装器（纯 Python 标准库）
├── app/
│   ├── 一键生图.html         可视化控制面板（i18n / 设置中心 / 自动识别）
│   └── 生图服务器.py         本地中转服务器（system-info API / 队列保护）
├── docs/                    安装指南 · 使用教程 · 常见问题
├── LICENSE                  MIT
└── SECURITY.md              安全策略
```

## 📖 文档

- [安装指南](docs/安装指南.md)
- [使用教程](docs/使用教程.md)
- [常见问题](docs/常见问题.md)

## 🤝 参与贡献

欢迎 Issue 与 PR。提交前请运行 `python3 install.py` 完整走一遍安装流程确认无回归。

## 📄 许可

本仓库代码基于 [MIT License](LICENSE) 开源。内置模型遵循各自原始许可（OpenRAIL++ / BSD-3），请合规使用生成内容。

---

闪电研究院 Lightning Research Institute · [shandianhub.cn](https://shandianhub.cn)
