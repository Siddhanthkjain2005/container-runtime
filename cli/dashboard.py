#!/usr/bin/env python3
"""
Interactive Dashboard for Container Monitoring
"""

import os
import sys
import time
from collections import defaultdict, deque
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils

# History buffer for graphs
cpu_history = defaultdict(lambda: deque(maxlen=30))
memory_history = defaultdict(lambda: deque(maxlen=30))
last_stats = {}

def create_ascii_graph(values, height=5, width=30):
    """Create ASCII art graph from values"""
    if not values or len(values) == 0:
        return ["No data" + " " * (width - 7)] * height
    
    # Normalize values to fit in height
    max_val = max(values) if max(values) > 0 else 1
    normalized = [int((v / max_val) * (height - 1)) for v in values]
    
    # Create graph
    graph = []
    for row in range(height - 1, -1, -1):
        line = ""
        for val in normalized[-width:]:
            if val >= row:
                line += "█"
            else:
                line += " "
        graph.append(line.ljust(width))
    
    return graph

def generate_dashboard():
    """Generate dashboard layout"""
    layout = Layout()
    
    # Get all containers
    containers = utils.list_containers()
    
    if not containers:
        return Panel(
            "[yellow]No containers running[/yellow]",
            title="Container Dashboard",
            border_style="blue"
        )
    
    # Create main layout
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    
    # Header
    header_text = Text("Container Runtime Dashboard", style="bold cyan", justify="center")
    layout["header"].update(Panel(header_text, border_style="blue"))
    
    # Main content
    panels = []
    
    for container in containers:
        name = container.get('name')
        status = container.get('status')
        
        if status != 'running':
            continue
        
        # Get current stats
        stats = utils.get_container_stats(name)
        
        # Calculate CPU percentage
        cpu_percent = 0.0
        if name in last_stats and 'cpu_usage_usec' in last_stats[name] and 'cpu_usage_usec' in stats:
            cpu_percent = utils.calculate_cpu_percent(
                last_stats[name]['cpu_usage_usec'],
                stats['cpu_usage_usec'],
                1.0
            )
        
        # Update history
        cpu_history[name].append(cpu_percent)
        memory_mb = stats['memory_usage'] / (1024 * 1024)
        memory_history[name].append(memory_mb)
        
        # Store stats for next calculation
        last_stats[name] = stats
        
        # Create stats table
        stats_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="yellow")
        
        # CPU stats
        cpu_graph = create_ascii_graph(list(cpu_history[name]), height=3, width=20)
        cpu_text = f"{cpu_percent:.1f}%\n" + "\n".join(cpu_graph)
        stats_table.add_row("CPU", cpu_text)
        
        # Memory stats
        memory_graph = create_ascii_graph(list(memory_history[name]), height=3, width=20)
        memory_text = f"{utils.format_bytes(stats['memory_usage'])}\n" + "\n".join(memory_graph)
        stats_table.add_row("Memory", memory_text)
        
        # I/O stats
        io_text = f"R: {utils.format_bytes(stats['io_read'])}\nW: {utils.format_bytes(stats['io_write'])}"
        stats_table.add_row("I/O", io_text)
        
        # PIDs
        stats_table.add_row("PIDs", str(stats['pids']))
        
        # Uptime
        created_at = container.get('created_at', time.time())
        uptime = int(time.time() - created_at)
        uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s"
        stats_table.add_row("Uptime", uptime_str)
        
        # Create panel for container
        panel = Panel(
            stats_table,
            title=f"[bold green]{name}[/bold green] ({container.get('command', 'N/A')})",
            border_style="green",
            padding=(0, 1)
        )
        panels.append(panel)
    
    if panels:
        # Split main area for multiple containers
        if len(panels) == 1:
            layout["main"].update(panels[0])
        else:
            layout["main"].split_row(*[Layout(name=f"container_{i}") for i in range(len(panels))])
            for i, panel in enumerate(panels):
                layout["main"][f"container_{i}"].update(panel)
    else:
        layout["main"].update(Panel("[yellow]No running containers[/yellow]", border_style="yellow"))
    
    return layout

def run_dashboard():
    """Run the interactive dashboard"""
    console = Console()
    
    console.print("[cyan]Starting dashboard... Press Ctrl+C to exit[/cyan]")
    console.print("[cyan]Updates every 1 second[/cyan]\n")
    
    try:
        with Live(generate_dashboard(), refresh_per_second=1, console=console) as live:
            while True:
                time.sleep(1)
                live.update(generate_dashboard())
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("Error: Must be run as root")
        sys.exit(1)
    
    run_dashboard()
