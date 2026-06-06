import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Dict, Optional

import readchar
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__

console = Console()
exit_flag = False  # 按键退出标志

REFRESH_INTERVAL = 0.5
COMMAND_TIMEOUT = 2.0


@dataclass
class CpuSample:
    total: int
    idle: int


@dataclass
class MonitorState:
    cpu_sample: Optional[CpuSample] = None
    gpu_names: Dict[str, str] = field(default_factory=dict)


def run_command(command):
    try:
        return subprocess.check_output(command, text=True, timeout=COMMAND_TIMEOUT)
    except FileNotFoundError:
        console.print("[red]rocm-smi not found. Please install ROCm and ensure it is in PATH.[/red]")
    except subprocess.TimeoutExpired:
        console.print(f"[red]{' '.join(command)} timed out[/red]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]{' '.join(command)} failed: {exc}[/red]")
    return ""


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_rocm_smi():
    """Parse GPU metrics from rocm-smi JSON output."""
    output = run_command(["rocm-smi", "--showuse", "--showmemuse", "--showtemp", "--showpower", "--json"])
    if not output:
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return parse_rocm_smi_text(output)

    gpus = []
    for card, metrics in sorted(data.items(), key=lambda item: to_int(item[0].replace("card", ""))):
        device = card.replace("card", "")
        temp = metrics.get("Temperature (Sensor junction) (C)")
        power = metrics.get("Current Socket Graphics Package Power (W)")
        gpu_util = metrics.get("GPU use (%)")
        vram = metrics.get("GPU Memory Allocated (VRAM%)")
        memory_activity = metrics.get("GPU Memory Read/Write Activity (%)")
        gpus.append({
            "device": device,
            "temp": to_float(temp),
            "power": to_float(power),
            "gpu_util": to_int(gpu_util),
            "vram": to_int(vram),
            "memory_activity": to_int(memory_activity),
        })

    return gpus


def parse_gpu_names():
    output = run_command(["rocm-smi", "--showproductname", "--json"])
    if not output:
        return {}

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {}

    names = {}
    for card, metrics in data.items():
        device = card.replace("card", "")
        raw_name = metrics.get("Card Series") or metrics.get("Card Model") or "Unknown GPU"
        names[device] = compact_gpu_name(raw_name)
    return names


def compact_gpu_name(name):
    replacements = (
        ("Advanced Micro Devices, Inc. [AMD/ATI]", "AMD"),
        ("AMD Instinct ", ""),
        ("AMD Radeon ", "Radeon "),
        ("AMD ", ""),
    )
    compact = name
    for old, new in replacements:
        compact = compact.replace(old, new)
    return compact.strip()


def parse_rocm_smi_text(output):
    """Fallback parser for older rocm-smi text output."""
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
            "vram": vram,
            "memory_activity": 0,
        })

    return gpus


def read_cpu_sample():
    try:
        first_line = Path("/proc/stat").read_text().splitlines()[0]
    except OSError:
        return None

    values = [to_int(value) for value in first_line.split()[1:]]
    if len(values) < 4:
        return None

    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return CpuSample(total=sum(values), idle=idle)


def read_cpu_percent(state):
    current = read_cpu_sample()
    previous = state.cpu_sample
    state.cpu_sample = current

    if current is None or previous is None:
        return 0.0

    total_delta = current.total - previous.total
    idle_delta = current.idle - previous.idle
    if total_delta <= 0:
        return 0.0

    return max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100))


def read_memory_info():
    try:
        meminfo = Path("/proc/meminfo").read_text()
    except OSError:
        return {"used": 0, "total": 0, "percent": 0.0}

    values = {}
    for line in meminfo.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            values[parts[0].rstrip(":")] = to_int(parts[1]) * 1024

    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(0, total - available)
    percent = used / total * 100 if total else 0.0
    return {"used": used, "total": total, "percent": percent}


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


def human_bytes(num):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num)
    for unit in units:
        if abs(value) < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PiB"


def percent_bar(value, width=12):
    value = max(0, min(100, int(value)))
    filled = int(value / 100 * width)
    bar = "█" * filled + " " * (width - filled)
    return f"{bar} {value:3d}%"


def render_summary(gpus, cpu_percent, memory_info):
    total_power = sum(gpu["power"] for gpu in gpus)
    avg_gpu = sum(gpu["gpu_util"] for gpu in gpus) / len(gpus) if gpus else 0
    load_1, load_5, load_15 = os.getloadavg()
    cpu_count = os.cpu_count() or 1

    summary = Text()
    summary.append("rocmtop ", style="bold cyan")
    summary.append(f"v{__version__}  ", style="dim")
    summary.append(datetime.now().strftime("%H:%M:%S"), style="bold")
    summary.append(f"  CPU {cpu_percent:4.1f}%")
    summary.append(f"  Load {load_1:.1f}/{load_5:.1f}/{load_15:.1f} ({cpu_count} cores)")
    summary.append(f"  RAM {memory_info['percent']:4.1f}% {human_bytes(memory_info['used'])}/{human_bytes(memory_info['total'])}")
    summary.append(f"  GPU avg {avg_gpu:4.1f}%")
    summary.append(f"  Power {total_power:.0f} W")
    return Panel(summary, box=box.ROUNDED)


def render_gpus(gpus, gpu_names):
    table = Table(title="GPU Overview", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("GPU", style="bold cyan", justify="right")
    table.add_column("Model", min_width=10, max_width=18, overflow="ellipsis", no_wrap=True)
    table.add_column("Temp", justify="right")
    table.add_column("Pwr", justify="right")
    table.add_column("GPU Util", min_width=18)
    table.add_column("VRAM", min_width=18)
    table.add_column("RW", justify="right")

    for gpu in gpus:
        table.add_row(
            gpu["device"],
            gpu_names.get(gpu["device"], "Unknown GPU"),
            f"[{color_temp(gpu['temp'])}]{gpu['temp']:.0f}°C[/]",
            f"[{color_power(gpu['power'])}]{gpu['power']:.0f} W[/]",
            f"[{color_gpu_util(gpu['gpu_util'])}]{percent_bar(gpu['gpu_util'])}[/]",
            f"[{color_vram(gpu['vram'])}]{percent_bar(gpu['vram'])}[/]",
            f"{gpu['memory_activity']}%",
        )
    return table


def render_dashboard(gpus, gpu_names, cpu_percent, memory_info):
    return Group(
        render_summary(gpus, cpu_percent, memory_info),
        render_gpus(gpus, gpu_names),
        Text("Press 'q' or 'Q' to quit", style="bold magenta"),
    )


def key_listener():
    global exit_flag
    while True:
        try:
            c = readchar.readkey()
        except (EOFError, OSError):
            break
        if c in ("q", "Q"):
            exit_flag = True
            break


def main():
    parser = argparse.ArgumentParser(description="Lightweight AMD ROCm GPU monitor")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=REFRESH_INTERVAL,
        help=f"Refresh interval in seconds (default: {REFRESH_INTERVAL})",
    )
    args = parser.parse_args()

    if args.version:
        print(f"rocmtop version {__version__}")
        return

    global exit_flag

    if sys.stdin.isatty():
        Thread(target=key_listener, daemon=True).start()
    state = MonitorState()

    initial_dashboard = Panel("Loading ROCm metrics...", box=box.ROUNDED)
    with Live(initial_dashboard, console=console, refresh_per_second=4, screen=True) as live:
        while not exit_flag:
            gpus = parse_rocm_smi()
            if not state.gpu_names:
                state.gpu_names = parse_gpu_names()
            cpu_percent = read_cpu_percent(state)
            memory_info = read_memory_info()
            if gpus:
                live.update(render_dashboard(gpus, state.gpu_names, cpu_percent, memory_info))
            else:
                live.update(Panel("[red]No GPU info found[/red]", box=box.ROUNDED))
            time.sleep(max(0.1, args.interval))

    console.print("[bold green]Exiting rocmtop[/bold green]")


if __name__ == "__main__":
    main()
