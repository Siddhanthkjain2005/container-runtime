#!/usr/bin/env python3
"""
Container CLI - Command-line interface for container management
"""

import os
import sys
import argparse
import subprocess
import signal
import time
from rich.console import Console
from rich.table import Table
from rich import box

# Import utility functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils

console = Console()

def cmd_create(args):
    """Create and start a container"""
    try:
        utils.check_root()
        utils.check_cgroups_v2()
        utils.check_runtime()
        
        # Check if container already exists
        if utils.load_container_metadata(args.name):
            console.print(f"[red]Error: Container '{args.name}' already exists[/red]")
            return 1
        
        # Validate rootfs
        rootfs_path = os.path.abspath(args.rootfs) if args.rootfs else os.path.abspath("./rootfs")
        if not os.path.exists(rootfs_path):
            console.print(f"[red]Error: Rootfs path '{rootfs_path}' does not exist[/red]")
            return 1
        
        # Prepare environment variables for limits
        env = os.environ.copy()
        limits = {}
        
        if args.cpu:
            env['CPU_LIMIT'] = str(args.cpu)
            limits['cpu'] = args.cpu
        
        if args.memory:
            env['MEMORY_LIMIT'] = args.memory
            limits['memory'] = args.memory
        
        if args.io:
            env['IO_LIMIT'] = str(args.io)
            limits['io'] = args.io
        
        if args.pids:
            env['PID_LIMIT'] = str(args.pids)
            limits['pids'] = args.pids
        
        # Prepare command
        command = args.command if args.command else "/bin/sh"
        cmd_args = [utils.RUNTIME_PATH, args.name, rootfs_path, command]
        
        console.print(f"[yellow]Creating container '{args.name}'...[/yellow]")
        
        # Run container runtime
        result = subprocess.run(
            cmd_args,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]Failed to create container[/red]")
            console.print(f"[red]Error: {result.stderr}[/red]")
            return 1
        
        # Get PID from output
        pid = None
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                break
        
        if pid:
            # Save metadata
            utils.save_container_metadata(args.name, pid, rootfs_path, command, limits)
            console.print(f"[green]✓ Container '{args.name}' created successfully (PID: {pid})[/green]")
        else:
            console.print(f"[yellow]Container created but PID not captured[/yellow]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

def cmd_list(args):
    """List all containers"""
    try:
        utils.check_root()
        
        containers = utils.list_containers()
        
        if not containers:
            console.print("[yellow]No containers found[/yellow]")
            return 0
        
        # Create table
        table = Table(title="Containers", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("PID", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Command", style="yellow")
        table.add_column("Created", style="blue")
        table.add_column("CPU Limit", style="white")
        table.add_column("Memory Limit", style="white")
        
        for container in containers:
            # Format created time
            created_time = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(container.get('created_at', 0))
            )
            
            # Format limits
            limits = container.get('limits', {})
            cpu_limit = f"{limits.get('cpu', 'N/A')}%" if limits.get('cpu') else "N/A"
            memory_limit = limits.get('memory', 'N/A')
            
            # Status color
            status = container.get('status', 'unknown')
            if status == 'running':
                status_str = "[green]running[/green]"
            else:
                status_str = "[red]stopped[/red]"
            
            table.add_row(
                container.get('name', 'N/A'),
                str(container.get('pid', 'N/A')),
                status_str,
                container.get('command', 'N/A'),
                created_time,
                cpu_limit,
                memory_limit
            )
        
        console.print(table)
        return 0
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

def cmd_delete(args):
    """Stop and delete a container"""
    try:
        utils.check_root()
        
        # Load metadata
        metadata = utils.load_container_metadata(args.name)
        if not metadata:
            console.print(f"[red]Error: Container '{args.name}' not found[/red]")
            return 1
        
        console.print(f"[yellow]Deleting container '{args.name}'...[/yellow]")
        
        # Kill the process if running
        pid = metadata.get('pid')
        if pid and utils.is_process_running(pid):
            try:
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
            except OSError:
                pass
        
        # Cleanup cgroup
        cgroup_path = os.path.join(utils.CGROUP_BASE_PATH, args.name)
        if os.path.exists(cgroup_path):
            # Kill all processes in cgroup
            procs_file = os.path.join(cgroup_path, "cgroup.procs")
            if os.path.exists(procs_file):
                try:
                    with open(procs_file, 'r') as f:
                        for line in f:
                            try:
                                pid = int(line.strip())
                                if pid > 1:
                                    os.kill(pid, signal.SIGKILL)
                            except (ValueError, OSError):
                                pass
                except IOError:
                    pass
            
            time.sleep(0.2)
            
            # Remove cgroup directory
            try:
                os.rmdir(cgroup_path)
            except OSError:
                console.print(f"[yellow]Warning: Could not remove cgroup directory[/yellow]")
        
        # Delete metadata
        utils.delete_container_metadata(args.name)
        
        console.print(f"[green]✓ Container '{args.name}' deleted successfully[/green]")
        return 0
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

def cmd_stats(args):
    """Show container statistics"""
    try:
        utils.check_root()
        
        # Load metadata
        metadata = utils.load_container_metadata(args.name)
        if not metadata:
            console.print(f"[red]Error: Container '{args.name}' not found[/red]")
            return 1
        
        # Check if running
        if metadata.get('status') == 'stopped' or not utils.is_process_running(metadata.get('pid')):
            console.print(f"[yellow]Container '{args.name}' is not running[/yellow]")
            return 1
        
        # Get initial stats for CPU calculation
        stats1 = utils.get_container_stats(args.name)
        time.sleep(1)
        stats2 = utils.get_container_stats(args.name)
        
        # Calculate CPU percentage
        cpu_percent = 0.0
        if 'cpu_usage_usec' in stats1 and 'cpu_usage_usec' in stats2:
            cpu_percent = utils.calculate_cpu_percent(
                stats1['cpu_usage_usec'],
                stats2['cpu_usage_usec'],
                1.0
            )
        
        # Create stats table
        table = Table(title=f"Container Stats: {args.name}", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("CPU Usage", f"{cpu_percent}%")
        table.add_row("Memory Usage", utils.format_bytes(stats2['memory_usage']))
        
        if stats2['memory_limit'] > 0:
            mem_percent = (stats2['memory_usage'] / stats2['memory_limit']) * 100
            table.add_row("Memory Limit", f"{utils.format_bytes(stats2['memory_limit'])} ({mem_percent:.1f}%)")
        else:
            table.add_row("Memory Limit", "unlimited")
        
        table.add_row("I/O Read", utils.format_bytes(stats2['io_read']))
        table.add_row("I/O Write", utils.format_bytes(stats2['io_write']))
        table.add_row("PIDs", str(stats2['pids']))
        
        # Calculate uptime
        created_at = metadata.get('created_at', time.time())
        uptime = int(time.time() - created_at)
        uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s"
        table.add_row("Uptime", uptime_str)
        
        console.print(table)
        return 0
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

def cmd_exec(args):
    """Execute command in running container"""
    try:
        utils.check_root()
        
        # Load metadata
        metadata = utils.load_container_metadata(args.name)
        if not metadata:
            console.print(f"[red]Error: Container '{args.name}' not found[/red]")
            return 1
        
        # Check if running
        pid = metadata.get('pid')
        if not pid or not utils.is_process_running(pid):
            console.print(f"[yellow]Container '{args.name}' is not running[/yellow]")
            return 1
        
        console.print(f"[yellow]Note: nsenter functionality would be used here[/yellow]")
        console.print(f"[yellow]Command to execute: {args.command}[/yellow]")
        console.print(f"[yellow]PID: {pid}[/yellow]")
        
        # Use nsenter to enter container namespaces
        nsenter_cmd = [
            'nsenter',
            '-t', str(pid),
            '-m', '-u', '-i', '-n', '-p',
            '--'
        ] + args.command
        
        try:
            result = subprocess.run(nsenter_cmd)
            return result.returncode
        except FileNotFoundError:
            console.print("[red]Error: nsenter not found. Please install util-linux package.[/red]")
            return 1
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

def cmd_dashboard(args):
    """Launch interactive dashboard"""
    try:
        utils.check_root()
        
        # Import dashboard module
        from dashboard import run_dashboard
        
        run_dashboard()
        return 0
        
    except ImportError:
        console.print("[red]Error: Dashboard module not available[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Container Runtime CLI - Manage Linux containers",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create and start a container')
    create_parser.add_argument('name', help='Container name')
    create_parser.add_argument('--rootfs', help='Path to rootfs (default: ./rootfs)')
    create_parser.add_argument('--cpu', type=int, help='CPU limit percentage (0-100)')
    create_parser.add_argument('--memory', help='Memory limit (e.g., 512M, 1G)')
    create_parser.add_argument('--io', type=int, help='I/O limit in bytes per second')
    create_parser.add_argument('--pids', type=int, help='Maximum number of PIDs')
    create_parser.add_argument('--command', help='Command to run (default: /bin/sh)')
    create_parser.set_defaults(func=cmd_create)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all containers')
    list_parser.set_defaults(func=cmd_list)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Stop and delete a container')
    delete_parser.add_argument('name', help='Container name')
    delete_parser.set_defaults(func=cmd_delete)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show container statistics')
    stats_parser.add_argument('name', help='Container name')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Exec command
    exec_parser = subparsers.add_parser('exec', help='Execute command in running container')
    exec_parser.add_argument('name', help='Container name')
    exec_parser.add_argument('command', nargs='+', help='Command to execute')
    exec_parser.set_defaults(func=cmd_exec)
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Launch interactive dashboard')
    dashboard_parser.set_defaults(func=cmd_dashboard)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
