# rocmtop

**rocmtop** 是一个轻量级的 ROCm GPU 监控工具，可在终端实时展示 AMD 显卡状态（温度、功耗、利用率、显存占用），功能类似 `nvidia-smi top`，专为 ROCm 平台优化。

## 一键体验

```bash
# 本地开发版（可编辑安装）
git clone https://github.com/Liam-zzy/rocmtop.git
cd rocmtop
pip install -e .
rocmtop
```

# 或从 PyPI 安装正式版
```bash
pip install rocmtop
rocmtop
```

## 功能亮点

- 实时刷新（默认 0.5 s）GPU 温度、功耗、利用率、显存占用
- 彩色表格 + 进度条，直观易读
- 按 `q` / `Q` 即刻退出
- 零复杂依赖，仅依赖 `rich` 与 `readchar`

## 运行要求

- AMD GPU 已安装 ROCm 驱动
- 系统路径可调用 `rocm-smi`

## 安装方式

| 场景        | 命令                          |
|-------------|-------------------------------|
| **开发/贡献** | `pip install -e .`            |
| **生产使用** | `pip install rocmtop`         |

## 使用方法

```bash
rocmtop                 # 默认 0.5 s 刷新
```

## 作者

Ziyang Zhai (Liam)  
项目地址: [https://github.com/Liam-zzy/rocmtop](https://github.com/Liam-zzy/rocmtop)
```
