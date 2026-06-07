# rocmtop

**rocmtop** 是一个轻量级的 AMD ROCm GPU 监控工具，可以在终端实时展示显卡型号、温度、功耗、利用率、显存占用，以及主机 CPU/RAM 状态。

## 一键体验

```bash
# 本地开发版（可编辑安装）
git clone https://github.com/Liam-zzy/rocmtop.git
cd rocmtop
pip install -e .
rocmtop
```

或从 PyPI 安装正式版：

```bash
pip install rocmtop
rocmtop
```

## 功能亮点

- 实时刷新显卡型号、温度、功耗、GPU 利用率、VRAM 占用和显存读写活动
- 展示主机 CPU 利用率、load average、RAM 使用量和整机 GPU 总功耗
- Rich 彩色表格 + 进度条，适合 SSH 终端和多卡服务器
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
rocmtop                         # 默认 0.5 s 刷新 GPU 指标
rocmtop -i 1                    # 每 1 秒刷新一次 GPU 指标
rocmtop --version
```

## 数据来源

- GPU 指标来自 `rocm-smi --showuse --showmemuse --showtemp --showpower --json`
- 显卡型号来自 `rocm-smi --showproductname --json`
- CPU/RAM 指标来自 Linux `/proc`

## 作者

Ziyang Zhai (Liam)  
项目地址: [https://github.com/Liam-zzy/rocmtop](https://github.com/Liam-zzy/rocmtop)
