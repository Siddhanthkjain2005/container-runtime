# Container Runtime System

A lightweight, Docker-like container runtime system built using Linux cgroups v2 and namespaces. This project provides isolated execution environments with resource limits and monitoring capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Container CLI (Python)                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐  │
│  │  create  │   list   │  delete  │  stats   │  dashboard   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Container Runtime (C)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Namespaces: PID, Mount, Network, UTS, IPC              │  │
│  │  - clone() with CLONE_NEW* flags                         │  │
│  │  - pivot_root() for filesystem isolation                 │  │
│  │  - mount /proc, /sys, /dev                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  cgroups v2: Resource Management                         │  │
│  │  - CPU limiting (cpu.max)                                │  │
│  │  - Memory limiting (memory.max)                          │  │
│  │  - I/O limiting (io.max)                                 │  │
│  │  - PID limiting (pids.max)                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Linux Kernel                               │
│  /sys/fs/cgroup/mycontainer/<container_name>/                   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Linux Namespaces**: Complete isolation using PID, Mount, Network, UTS, and IPC namespaces
- **cgroups v2**: Resource limiting and monitoring for CPU, Memory, I/O, and PIDs
- **Resource Limits**: Set CPU percentage, memory limits, I/O limits, and maximum PIDs
- **Real-time Monitoring**: View live container statistics including CPU, memory, I/O usage
- **Interactive Dashboard**: Terminal-based dashboard with live graphs
- **Container Management**: Create, list, delete, and execute commands in containers
- **Production Ready**: Error handling, validation, and proper cleanup

## Prerequisites

- **Linux Kernel**: 5.0+ (for cgroups v2 support)
- **Root Access**: Required for namespace and cgroup operations
- **Dependencies**:
  - GCC compiler
  - Python 3.8+
  - cgroups v2 enabled
  - util-linux (for nsenter)

### Verify cgroups v2

```bash
mount | grep cgroup2
# Should show: cgroup2 on /sys/fs/cgroup type cgroup2 ...
```

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/Siddhanthkjain2005/container-runtime.git
cd container-runtime
```

2. **Build the C runtime**:
```bash
make
```

3. **Install Python dependencies**:
```bash
pip3 install -r requirements.txt
```

4. **Create required directories**:
```bash
sudo mkdir -p /var/lib/mycontainer/containers
sudo mkdir -p /sys/fs/cgroup/mycontainer
```

5. **Prepare a rootfs** (Ubuntu example):
```bash
# Download Ubuntu base rootfs for your architecture
# For x86_64:
mkdir -p rootfs
wget https://cloud-images.ubuntu.com/minimal/releases/jammy/release/ubuntu-22.04-minimal-cloudimg-amd64-root.tar.xz
sudo tar -xf ubuntu-22.04-minimal-cloudimg-amd64-root.tar.xz -C rootfs/

# Or use debootstrap
sudo debootstrap --arch=amd64 jammy rootfs http://archive.ubuntu.com/ubuntu/
```

## Usage

### Create Container

```bash
# Basic container with default settings
sudo ./cli/container_cli.py create mycontainer

# Container with resource limits
sudo ./cli/container_cli.py create mycontainer \
    --cpu 50 \
    --memory 512M \
    --command /bin/bash

# Container with custom rootfs
sudo ./cli/container_cli.py create mycontainer \
    --rootfs /path/to/rootfs \
    --cpu 75 \
    --memory 1G \
    --pids 100
```

### List Containers

```bash
sudo ./cli/container_cli.py list
```

Output:
```
                                Containers                                
┌───────────┬──────┬─────────┬──────────┬─────────────────────┬───────────┬──────────────┐
│ Name      │ PID  │ Status  │ Command  │ Created             │ CPU Limit │ Memory Limit │
├───────────┼──────┼─────────┼──────────┼─────────────────────┼───────────┼──────────────┤
│ container1│ 1234 │ running │ /bin/sh  │ 2026-01-04 10:30:00 │ 50%       │ 512M         │
└───────────┴──────┴─────────┴──────────┴─────────────────────┴───────────┴──────────────┘
```

### View Statistics

```bash
sudo ./cli/container_cli.py stats mycontainer
```

Output:
```
            Container Stats: mycontainer            
┌──────────────┬──────────────────────────────────┐
│ Metric       │ Value                            │
├──────────────┼──────────────────────────────────┤
│ CPU Usage    │ 12.5%                            │
│ Memory Usage │ 256.00MB                         │
│ Memory Limit │ 512.00MB (50.0%)                 │
│ I/O Read     │ 10.24MB                          │
│ I/O Write    │ 5.12MB                           │
│ PIDs         │ 15                               │
│ Uptime       │ 0h 5m 32s                        │
└──────────────┴──────────────────────────────────┘
```

### Execute Command in Container

```bash
sudo ./cli/container_cli.py exec mycontainer ls -la
sudo ./cli/container_cli.py exec mycontainer ps aux
```

### Interactive Dashboard

```bash
sudo ./cli/container_cli.py dashboard
```

Features:
- Real-time CPU and memory graphs
- Live I/O statistics
- Process count
- Uptime tracking
- Updates every second
- Press Ctrl+C to exit

### Delete Container

```bash
sudo ./cli/container_cli.py delete mycontainer
```

## Technical Details

### How It Works

1. **Container Creation**:
   - The CLI calls the C runtime with container configuration
   - Runtime creates a new process using `clone()` with namespace flags
   - Sets up cgroups and applies resource limits
   - Performs `pivot_root()` to change to container's rootfs
   - Mounts essential filesystems (/proc, /sys, /dev)
   - Executes the specified command

2. **Namespace Isolation**:
   - **PID**: Container has its own process tree (PID 1)
   - **Mount**: Isolated filesystem view
   - **Network**: Isolated network stack
   - **UTS**: Isolated hostname
   - **IPC**: Isolated inter-process communication

3. **Resource Management**:
   - Creates cgroup at `/sys/fs/cgroup/mycontainer/<name>/`
   - Writes resource limits to cgroup files:
     - `cpu.max`: CPU quota and period
     - `memory.max`: Memory limit in bytes
     - `io.max`: I/O bandwidth limits
     - `pids.max`: Maximum process count
   - Adds container PID to `cgroup.procs`

4. **Monitoring**:
   - Reads statistics from cgroup files:
     - `cpu.stat`: CPU usage in microseconds
     - `memory.current`: Current memory usage
     - `io.stat`: I/O read/write bytes
     - `pids.current`: Current process count
   - Calculates CPU percentage from usage deltas
   - Formats data for display

### Comparison with Docker

| Feature | This Runtime | Docker |
|---------|--------------|--------|
| Namespaces | PID, Mount, Net, UTS, IPC | PID, Mount, Net, UTS, IPC, User |
| cgroups | v2 | v1/v2 |
| Image Format | Raw rootfs directory | OCI images (layers) |
| Networking | Basic isolation | Bridge, overlay, etc. |
| Storage | Direct mount | Overlay2, BTRFS, etc. |
| Registry | N/A | Docker Hub, etc. |
| Ecosystem | Minimal | Extensive |

### File Structure

```
.
├── src/
│   ├── container.c      # Main runtime with clone() and pivot_root()
│   ├── container.h      # Container structures and functions
│   ├── cgroups.c        # cgroups v2 management
│   ├── cgroups.h        # cgroups interface
│   ├── namespaces.c     # Namespace setup functions
│   └── namespaces.h     # Namespace interface
├── cli/
│   ├── container_cli.py # CLI interface
│   ├── dashboard.py     # Interactive dashboard
│   └── utils.py         # Helper functions
├── build/               # Build artifacts (created by make)
├── rootfs/              # Container root filesystem
├── containers/          # Container state (JSON files)
├── Makefile             # Build system
├── README.md            # This file
└── requirements.txt     # Python dependencies
```

## Troubleshooting

### Error: Must be run as root

Most operations require root privileges for namespace and cgroup management.

```bash
sudo ./cli/container_cli.py <command>
```

### Error: cgroups v2 is not available

Ensure your system uses cgroups v2:

```bash
# Check if cgroup2 is mounted
mount | grep cgroup2

# If not, you may need to enable it in boot parameters
# Add to /etc/default/grub:
# GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"
# Then: sudo update-grub && sudo reboot
```

### Error: Rootfs path does not exist

Provide a valid rootfs directory:

```bash
sudo ./cli/container_cli.py create mycontainer --rootfs /path/to/rootfs
```

### Error: nsenter not found

Install util-linux:

```bash
sudo apt-get install util-linux  # Debian/Ubuntu
sudo yum install util-linux      # CentOS/RHEL
```

### Container won't start

Check the C runtime directly:

```bash
sudo ./container_runtime mycontainer ./rootfs /bin/sh
```

### Permission denied on cgroup files

Ensure cgroup controllers are enabled:

```bash
# Enable controllers
echo "+cpu +memory +io +pids" | sudo tee /sys/fs/cgroup/cgroup.subtree_control
```

## Development

### Building

```bash
make clean
make
```

### Code Style

The C code follows these conventions:
- GNU C11 standard
- Compiled with `-Wall -Wextra` for warnings
- Error checking on all system calls
- Proper cleanup on failures

### Adding Features

1. **New cgroup controller**: Add functions to `cgroups.c`
2. **New namespace**: Add setup to `namespaces.c`
3. **New CLI command**: Add to `container_cli.py`
4. **Dashboard feature**: Modify `dashboard.py`

## Future Improvements

- [ ] User namespaces for rootless containers
- [ ] Network bridge and veth pair setup
- [ ] Container image support (tar archives)
- [ ] Overlay filesystem for layers
- [ ] Container logs and persistence
- [ ] Resource limit validation and warnings
- [ ] Health checks and restart policies
- [ ] Container networking (port mapping)
- [ ] Volume mounts
- [ ] Environment variable support
- [ ] seccomp and AppArmor profiles
- [ ] Checkpoint/restore support

## License

This project is created for educational purposes.

## Author

Siddhanth K Jain

## Acknowledgments

- Linux kernel documentation
- cgroups v2 documentation
- Docker and runc projects for inspiration
