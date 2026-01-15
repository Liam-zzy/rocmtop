import subprocess
import re
import time
from threading import Thread

from rich.console import Console
from rich.table import Table
import readchar

import argparse
from . import __version__

console = Console()
exit_flag = False  # 按键退出标志

REFRESH_INTERVAL = 0.5


def parse_rocm_smi():
    """解析 rocm-smi 输出为 GPU 信息列表"""
    try:
        output = subprocess.check_output(["rocm-smi"], text=True)
    except Exception as e:
        console.print(f"[red]Failed to run rocm-smi: {e}[/red]")
        return []

    gpus = []
    lines = output.splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("=") or line.startswith("Device") or "Concise" in line:
            continue

        m_device = re.match(r'^(\d+)', line)
        if not m_device:
            continue
        device = m_device.group(1)

        percentages = re.findall(r'(\d+)%', line)
        if len(percentages) >= 2:
            vram = int(percentages[-2])
            gpu_util = int(percentages[-1])
        else:
            vram = gpu_util = 0

        temp_match = re.search(r'(\d+\.?\d*)°C', line)
        temp = float(temp_match.group(1)) if temp_match else 0

        power_match = re.search(r'(\d+\.?\d*)W', line)
        power = float(power_match.group(1)) if power_match else 0

        gpus.append({
            "device": device,
            "temp": temp,
            "power": power,
            "gpu_util": gpu_util,
            "vram": vram
        })

    return gpus


def color_gpu_util(val):
    if val >= 90:
        return "red"
    elif val >= 50:
        return "yellow"
    elif val > 0:
        return "green"
    else:
        return "white"


def color_power(val):
    if val > 600:
        return "red"
    elif val > 200:
        return "yellow"
    else:
        return "green"


def color_vram(val):
    if val > 90:
        return "red"
    elif val >= 50:
        return "yellow"
    elif val > 0:
        return "green"
    else:
        return "white"


def color_temp(val):
    if val > 90:
        return "red"
    elif val >= 60:
        return "yellow"
    elif val >= 30:
        return "green"
    else:
        return "white"


def display_gpus(gpus):
    """美化显示 GPU 表格"""
    table = Table(title="AMD GPU Monitor (rocmtop)", box=None, expand=True)
    table.add_column("Device", style="bold cyan")
    table.add_column("Temp (°C)", justify="right")
    table.add_column("Power (W)", justify="right")
    table.add_column("GPU Util", justify="right", width=30)
    table.add_column("VRAM %", justify="right")

    bar_len = 20

    for gpu in gpus:
        temp_str = f"[{color_temp(gpu['temp'])}]{gpu['temp']}[/]"
        power_str = f"[{color_power(gpu['power'])}]{gpu['power']}[/]"

        filled_len = int(gpu['gpu_util'] / 100 * bar_len)
        bar = "█" * filled_len + " " * (bar_len - filled_len)
        gpu_cell = (
            f"[{color_gpu_util(gpu['gpu_util'])}]"
            f"{bar}{str(gpu['gpu_util']).rjust(30 - len(bar))}%[/]"
        )

        vram_str = f"[{color_vram(gpu['vram'])}]{gpu['vram']}%[/]"

        table.add_row(
            gpu["device"],
            temp_str,
            power_str,
            gpu_cell,
            vram_str
        )

    console.clear()
    console.print(table)
    console.print("[bold magenta]Press 'q' or 'Q' to quit[/bold magenta]")


def key_listener():
    global exit_flag
    while True:
        c = readchar.readkey()
        if c in ("q", "Q"):
            exit_flag = True
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"rocmtop version {__version__}")
        return
        
    global exit_flag

    Thread(target=key_listener, daemon=True).start()

    while not exit_flag:
        gpus = parse_rocm_smi()
        if gpus:
            display_gpus(gpus)
        else:
            console.print("[red]No GPU info found[/red]")
        time.sleep(REFRESH_INTERVAL)

    console.clear()
    console.print("[bold green]Exiting rocmtop[/bold green]")
