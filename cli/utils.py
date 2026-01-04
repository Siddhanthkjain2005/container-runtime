#!/usr/bin/env python3
"""
Utility functions for container management
"""

import os
import json
import time
from pathlib import Path

# Paths
CONTAINER_STATE_DIR = "/var/lib/mycontainer/containers"
CGROUP_BASE_PATH = "/sys/fs/cgroup/mycontainer"
RUNTIME_PATH = "./container_runtime"

def ensure_directories():
    """Ensure required directories exist"""
    os.makedirs(CONTAINER_STATE_DIR, exist_ok=True)
    os.makedirs(CGROUP_BASE_PATH, exist_ok=True)

def check_root():
    """Check if running as root"""
    if os.geteuid() != 0:
        raise PermissionError("This command must be run as root")

def check_cgroups_v2():
    """Check if cgroups v2 is available"""
    if not os.path.exists("/sys/fs/cgroup/cgroup.controllers"):
        raise RuntimeError("cgroups v2 is not available on this system")

def check_runtime():
    """Check if container runtime binary exists"""
    if not os.path.exists(RUNTIME_PATH):
        raise RuntimeError(
            f"Container runtime not found at {RUNTIME_PATH}. "
            "Please run 'make' to build it."
        )

def save_container_metadata(name, pid, rootfs, command, limits):
    """Save container metadata to JSON file"""
    ensure_directories()
    
    metadata = {
        "name": name,
        "pid": pid,
        "rootfs": rootfs,
        "command": command,
        "created_at": time.time(),
        "limits": limits,
        "status": "running"
    }
    
    metadata_file = os.path.join(CONTAINER_STATE_DIR, f"{name}.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata

def load_container_metadata(name):
    """Load container metadata from JSON file"""
    metadata_file = os.path.join(CONTAINER_STATE_DIR, f"{name}.json")
    
    if not os.path.exists(metadata_file):
        return None
    
    try:
        with open(metadata_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def delete_container_metadata(name):
    """Delete container metadata file"""
    metadata_file = os.path.join(CONTAINER_STATE_DIR, f"{name}.json")
    if os.path.exists(metadata_file):
        os.remove(metadata_file)

def list_containers():
    """List all containers"""
    ensure_directories()
    containers = []
    
    for filename in os.listdir(CONTAINER_STATE_DIR):
        if filename.endswith('.json'):
            name = filename[:-5]
            metadata = load_container_metadata(name)
            if metadata:
                # Check if process is still running
                pid = metadata.get('pid')
                if pid and is_process_running(pid):
                    metadata['status'] = 'running'
                else:
                    metadata['status'] = 'stopped'
                containers.append(metadata)
    
    return containers

def is_process_running(pid):
    """Check if a process is running"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False

def parse_memory_limit(limit_str):
    """Parse memory limit string (e.g., '512M', '1G') to bytes"""
    if not limit_str:
        return 0
    
    limit_str = limit_str.strip().upper()
    
    if limit_str.endswith('K'):
        return int(limit_str[:-1]) * 1024
    elif limit_str.endswith('M'):
        return int(limit_str[:-1]) * 1024 * 1024
    elif limit_str.endswith('G'):
        return int(limit_str[:-1]) * 1024 * 1024 * 1024
    else:
        return int(limit_str)

def format_bytes(bytes_val):
    """Format bytes to human-readable string"""
    if bytes_val < 1024:
        return f"{bytes_val}B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.2f}KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f}MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f}GB"

def read_cgroup_stat(container_name, stat_file):
    """Read a cgroup stat file"""
    path = os.path.join(CGROUP_BASE_PATH, container_name, stat_file)
    
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'r') as f:
            return f.read()
    except IOError:
        return None

def get_container_stats(container_name):
    """Get container resource statistics"""
    stats = {
        "cpu_usage": 0,
        "memory_usage": 0,
        "memory_limit": 0,
        "io_read": 0,
        "io_write": 0,
        "pids": 0
    }
    
    # Read CPU stats
    cpu_stat = read_cgroup_stat(container_name, "cpu.stat")
    if cpu_stat:
        for line in cpu_stat.split('\n'):
            if line.startswith('usage_usec'):
                stats["cpu_usage_usec"] = int(line.split()[1])
    
    # Read memory stats
    memory_current = read_cgroup_stat(container_name, "memory.current")
    if memory_current:
        stats["memory_usage"] = int(memory_current.strip())
    
    memory_max = read_cgroup_stat(container_name, "memory.max")
    if memory_max:
        try:
            stats["memory_limit"] = int(memory_max.strip())
        except ValueError:
            stats["memory_limit"] = 0  # 'max' means no limit
    
    # Read I/O stats
    io_stat = read_cgroup_stat(container_name, "io.stat")
    if io_stat:
        for line in io_stat.split('\n'):
            parts = line.split()
            if len(parts) > 1:
                for part in parts[1:]:
                    if part.startswith('rbytes='):
                        stats["io_read"] += int(part.split('=')[1])
                    elif part.startswith('wbytes='):
                        stats["io_write"] += int(part.split('=')[1])
    
    # Read PID stats
    pids_current = read_cgroup_stat(container_name, "pids.current")
    if pids_current:
        stats["pids"] = int(pids_current.strip())
    
    return stats

def calculate_cpu_percent(old_usage_usec, new_usage_usec, time_delta_sec):
    """Calculate CPU usage percentage"""
    if time_delta_sec <= 0:
        return 0.0
    
    usage_delta = new_usage_usec - old_usage_usec
    # Convert microseconds to seconds and calculate percentage
    cpu_time_sec = usage_delta / 1_000_000
    cpu_percent = (cpu_time_sec / time_delta_sec) * 100
    
    return round(cpu_percent, 2)
