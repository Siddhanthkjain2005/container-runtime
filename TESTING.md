# Testing Guide

This document describes how to test the container runtime system.

## Prerequisites

- Root access
- Linux kernel 5.0+ with cgroups v2
- Built container runtime (`make`)
- Python dependencies installed (`pip3 install -r requirements.txt`)
- A valid rootfs in `./rootfs/`

## Running Tests

### Quick Demo

Run the automated demo script:

```bash
sudo ./demo.sh
```

This will:
1. Build the container runtime
2. List containers (empty initially)
3. Create a test container
4. List containers again
5. Delete the container
6. Test direct runtime usage
7. Test with resource limits

### Manual Testing

#### Test 1: Basic Container Creation

```bash
sudo python3 cli/container_cli.py create test1 --command /bin/sh
```

Expected: Container created successfully with PID output.

#### Test 2: Container with Resource Limits

```bash
sudo python3 cli/container_cli.py create test2 \
    --cpu 50 \
    --memory 512M \
    --pids 100 \
    --command /init.sh
```

Expected: Container runs with specified limits.

#### Test 3: List Containers

```bash
sudo python3 cli/container_cli.py list
```

Expected: Table showing all containers with status, PID, limits, etc.

#### Test 4: Delete Container

```bash
sudo python3 cli/container_cli.py delete test1
```

Expected: Container stopped and removed cleanly.

#### Test 5: Direct Runtime Usage

```bash
sudo CPU_LIMIT=30 MEMORY_LIMIT=256M \
    ./container_runtime mytest ./rootfs /bin/echo "Hello"
```

Expected: "Hello" printed, then PID shown.

## Verification

### Verify Namespaces

Inside a container, check isolation:

```bash
# In container: Check PID namespace
ps aux
# Should only show container processes

# Check hostname (UTS namespace)
hostname
# Should show container name

# Check mounts (Mount namespace)
mount
# Should show isolated mounts
```

### Verify cgroups

Check cgroup setup:

```bash
ls -la /sys/fs/cgroup/mycontainer/
cat /sys/fs/cgroup/mycontainer/<container_name>/cpu.max
cat /sys/fs/cgroup/mycontainer/<container_name>/memory.max
```

### Verify Resource Limits

Test CPU limit enforcement:

```bash
# Create container with 10% CPU limit
sudo python3 cli/container_cli.py create cputest --cpu 10 --command /bin/sh

# Should be throttled to ~10% CPU usage
```

Test memory limit enforcement:

```bash
# Container attempting to use more memory than limit should be OOM killed
```

## Known Limitations

1. **Container Lifecycle**: The CLI waits for containers to complete, so long-running containers will block the CLI until they exit.

2. **Network**: Basic network namespace isolation only. No bridge or external connectivity configured.

3. **Stats Command**: Only works for running containers. The stats calculation requires two samples over 1 second.

4. **Dashboard**: Requires running containers to display meaningful data.

5. **Exec Command**: Uses `nsenter` which must be installed separately via util-linux package.

## Troubleshooting Tests

### Container won't start

- Verify rootfs exists and is accessible
- Check you're running as root
- Verify cgroups v2 is available: `mount | grep cgroup2`

### Pivot root fails

- Ensure rootfs path is absolute
- Check rootfs has proper directory structure

### Stats show zero

- Container may not be running
- Wait a few seconds after container start
- Verify cgroup files exist

### Dashboard doesn't update

- Ensure containers are running
- Check terminal supports rich formatting
- Verify update interval (1 second)
