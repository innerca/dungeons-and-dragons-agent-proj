# CPU-Only PyTorch 快速安装指南

## 问题
`sentence-transformers` 依赖 PyTorch，默认会下载包含 CUDA 支持的完整版本（3GB+）。

## 解决方案

### 方案 1：首次安装时使用 CPU 版本（推荐，节省 3GB 空间）

如果你不需要 GPU 加速（大多数开发场景），使用 CPU-only 版本：

```bash
cd gameserver

# 使用 CI 配置（CPU-only PyTorch）
uv sync --frozen --config-file uv.ci.toml
```

**优点**：
- 下载量从 3GB+ 减少到 ~500MB
- 安装速度快 5-10 倍
- 功能完全满足开发测试需求

### 方案 2：需要 GPU 加速时使用完整版

如果你需要 GPU 训练或推理：

```bash
cd gameserver

# 使用默认配置（包含 CUDA）
uv sync --frozen
```

**注意**：这需要 NVIDIA GPU 和 CUDA 工具包。

### 方案 3：混合使用（高级）

先安装 CPU 版本快速开始，后续按需升级到 GPU 版本：

```bash
# 1. 快速安装 CPU 版本
uv sync --frozen --config-file uv.ci.toml

# 2. 后续需要 GPU 时，重新安装完整版
uv sync --frozen --reinstall-package torch
```

## 配置文件说明

- `uv.toml` - 本地开发配置（使用清华源加速）
- `uv.ci.toml` - CI/CD 配置（CPU-only PyTorch，避免下载 CUDA 包）

## 性能对比

| 配置 | 下载大小 | 安装时间 | 适用场景 |
|------|---------|---------|---------|
| CPU-only | ~500MB | 1-2 分钟 | 本地开发、CI/CD、测试 |
| CUDA 完整 | 3GB+ | 10-20 分钟 | GPU 训练、生产推理 |

## 验证安装

```bash
# 检查 PyTorch 版本
uv run python -c "import torch; print(f'PyTorch: {torch.__version__}')"

# 检查是否使用 CPU
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

CPU 版本会显示 `CUDA available: False`，这是正常的。
