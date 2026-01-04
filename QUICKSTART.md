# Quick Reference Card

## Container Runtime System - Quick Start Guide

### Prerequisites
```bash
# 1. Build the runtime
make

# 2. Install Python dependencies  
pip3 install -r requirements.txt

# 3. Create rootfs (BusyBox minimal)
mkdir -p rootfs/{bin,sbin,etc,proc,sys,dev,usr/bin,usr/sbin,lib,lib64,tmp}
cp /bin/busybox rootfs/bin/
sudo chroot rootfs /bin/busybox --install -s
sudo cp -a /lib/x86_64-linux-gnu rootfs/lib/
sudo cp -a /lib64/ld-linux-x86-64.so.* rootfs/lib64/
sudo ln -sf busybox rootfs/bin/sh
```

### Basic Commands

#### Create Container
```bash
# Basic
sudo python3 cli/container_cli.py create mycontainer

# With limits
sudo python3 cli/container_cli.py create mycontainer \
    --cpu 50 \
    --memory 512M \
    --command /bin/sh
```

#### List Containers
```bash
sudo python3 cli/container_cli.py list
```

#### View Statistics
```bash
sudo python3 cli/container_cli.py stats mycontainer
```

#### Execute Command
```bash
sudo python3 cli/container_cli.py exec mycontainer ls -la
```

#### Delete Container
```bash
sudo python3 cli/container_cli.py delete mycontainer
```

#### Launch Dashboard
```bash
sudo python3 cli/container_cli.py dashboard
```

### Direct Runtime Usage
```bash
# Basic
sudo ./container_runtime <name> <rootfs> <command>

# With limits
sudo CPU_LIMIT=50 MEMORY_LIMIT=512M \
    ./container_runtime mycontainer ./rootfs /bin/sh
```

### Environment Variables
- `CPU_LIMIT`: CPU percentage (0-100)
- `MEMORY_LIMIT`: Memory limit (e.g., 512M, 1G)
- `IO_LIMIT`: I/O limit in bytes per second
- `PID_LIMIT`: Maximum number of PIDs

### Demonstrations
```bash
# Basic demo
sudo ./demo.sh

# Stats monitoring demo
sudo ./demo_stats.sh
```

### Checking cgroups
```bash
# View cgroup hierarchy
ls -la /sys/fs/cgroup/mycontainer/

# Check CPU limit
cat /sys/fs/cgroup/mycontainer/<name>/cpu.max

# Check memory usage
cat /sys/fs/cgroup/mycontainer/<name>/memory.current
```

### Troubleshooting

#### Container won't start
```bash
# Verify rootfs exists
ls -la ./rootfs/

# Check if running as root
sudo whoami

# Verify cgroups v2
mount | grep cgroup2
```

#### Permission denied
```bash
# All commands need root
sudo <command>
```

#### Build fails
```bash
# Clean and rebuild
make clean
make
```

### File Locations
- Container Runtime: `./container_runtime`
- CLI Scripts: `./cli/*.py`
- Source Code: `./src/*.{c,h}`
- Container State: `/var/lib/mycontainer/containers/`
- cgroups: `/sys/fs/cgroup/mycontainer/`

### Key Features
✅ Namespace isolation (PID, Mount, Network, UTS, IPC)
✅ Resource limits (CPU, Memory, I/O, PIDs)
✅ Real-time monitoring
✅ Interactive dashboard
✅ Clean error handling
✅ Production-ready code

### Documentation
- README.md - Complete guide
- TESTING.md - Test scenarios
- EXAMPLES.md - Usage examples
- SUMMARY.md - Project overview

### Getting Help
```bash
# CLI help
python3 cli/container_cli.py --help

# Command-specific help
python3 cli/container_cli.py create --help
```

---

**Ready for demonstration!** 🚀

All features implemented and tested.
System is production-ready.
