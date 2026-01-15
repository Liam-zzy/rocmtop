# rocmtop

**rocmtop** 是一个轻量级的 ROCm GPU 监控工具，可以在终端动态展示 AMD 显卡的状态（温度、功率、GPU 利用率和显存占用），类似于 `nvidia-smi top`。  

用户可以直接通过终端使用：

```bash
pip install rocmtop

rocmtop
````

## 功能特点

* 实时刷新 GPU 状态（默认 0.5 秒刷新间隔）
* 彩色显示 GPU 温度、功率、利用率和显存占用
* 进度条直观显示 GPU 利用率
* 按 `q` 或 `Q` 退出
* 轻量、易用，无依赖复杂库，仅依赖 `rich` 和 `readchar`

## 安装

```bash
pip install rocmtop
```

## 使用

```bash
rocmtop
```

> 注意：需要在支持 ROCm 的 AMD 显卡上使用，并安装 `rocm-smi` 工具。

## 作者
```
Ziyang Zhai (Liam)

```
