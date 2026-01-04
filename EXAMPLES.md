# Examples and Use Cases

This document provides practical examples of using the container runtime system.

## Basic Examples

### Example 1: Hello World Container

```bash
sudo ./container_runtime hello ./rootfs /bin/echo "Hello from container!"
```

Output:
```
Hello from container!
4193
```

### Example 2: Running Shell Commands

```bash
sudo ./container_runtime mytest ./rootfs /bin/sh -c "hostname && ps aux"
```

### Example 3: Container with CPU Limit

```bash
sudo CPU_LIMIT=25 ./container_runtime cpucontainer ./rootfs /bin/sh
```

This container will be limited to 25% CPU usage.

### Example 4: Container with Memory Limit

```bash
sudo MEMORY_LIMIT=512M ./container_runtime memcontainer ./rootfs /bin/sh
```

This container can use up to 512MB of memory.

## CLI Examples

### Creating Containers

**Basic container:**
```bash
sudo python3 cli/container_cli.py create mycontainer
```

**With resource limits:**
```bash
sudo python3 cli/container_cli.py create limited \
    --cpu 50 \
    --memory 512M \
    --pids 100 \
    --command /bin/sh
```

**With custom rootfs:**
```bash
sudo python3 cli/container_cli.py create custom \
    --rootfs /path/to/custom/rootfs \
    --cpu 75 \
    --memory 1G \
    --command /init.sh
```

### Listing Containers

```bash
sudo python3 cli/container_cli.py list
```

Example output:
```
                                  Containers                                  
┌────────┬──────┬─────────┬──────────┬─────────────────────┬───────────┬──────────────┐
│ Name   │ PID  │ Status  │ Command  │ Created             │ CPU Limit │ Memory Limit │
├────────┼──────┼─────────┼──────────┼─────────────────────┼───────────┼──────────────┤
│ test1  │ 1234 │ running │ /bin/sh  │ 2026-01-04 10:30:00 │ 50%       │ 512M         │
│ test2  │ 1235 │ stopped │ /init.sh │ 2026-01-04 10:31:00 │ N/A       │ N/A          │
└────────┴──────┴─────────┴──────────┴─────────────────────┴───────────┴──────────────┘
```

### Viewing Container Stats

```bash
sudo python3 cli/container_cli.py stats mycontainer
```

Example output:
```
    Container Stats: mycontainer    
╭──────────────┬─────────────────╮
│ Metric       │ Value           │
├──────────────┼─────────────────┤
│ CPU Usage    │ 12.5%           │
│ Memory Usage │ 256.00MB        │
│ Memory Limit │ 512.00MB (50%)  │
│ I/O Read     │ 10.24MB         │
│ I/O Write    │ 5.12MB          │
│ PIDs         │ 15              │
│ Uptime       │ 0h 5m 32s       │
╰──────────────┴─────────────────╯
```

### Executing Commands in Containers

```bash
# List files
sudo python3 cli/container_cli.py exec mycontainer ls -la

# Check processes
sudo python3 cli/container_cli.py exec mycontainer ps aux

# Check network
sudo python3 cli/container_cli.py exec mycontainer ip addr
```

### Deleting Containers

```bash
sudo python3 cli/container_cli.py delete mycontainer
```

## Advanced Use Cases

### Use Case 1: Isolated Build Environment

Create a container for building software without affecting the host:

```bash
# Create container with more CPU and memory
sudo python3 cli/container_cli.py create buildenv \
    --cpu 75 \
    --memory 2G \
    --rootfs /path/to/ubuntu/rootfs \
    --command /bin/bash

# Execute build commands
sudo python3 cli/container_cli.py exec buildenv make -j4
```

### Use Case 2: Testing with Resource Constraints

Test application behavior under resource constraints:

```bash
# Create container with limited resources
sudo python3 cli/container_cli.py create testenv \
    --cpu 10 \
    --memory 128M \
    --pids 50 \
    --command /app/test.sh
```

### Use Case 3: Multiple Isolated Services

Run multiple services in isolation:

```bash
# Web server container
sudo python3 cli/container_cli.py create webserver \
    --cpu 50 \
    --memory 512M \
    --command /usr/sbin/nginx

# Database container
sudo python3 cli/container_cli.py create database \
    --cpu 50 \
    --memory 1G \
    --command /usr/bin/mysqld

# Cache server container
sudo python3 cli/container_cli.py create cache \
    --cpu 25 \
    --memory 256M \
    --command /usr/bin/redis-server
```

### Use Case 4: Development Environment

Create isolated development environments:

```bash
# Python development
sudo python3 cli/container_cli.py create pydev \
    --cpu 50 \
    --memory 1G \
    --command /bin/bash

# Node.js development
sudo python3 cli/container_cli.py create nodedev \
    --cpu 50 \
    --memory 1G \
    --command /bin/bash
```

## Monitoring Examples

### Continuous Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Continuous container monitoring

while true; do
    clear
    echo "Container Status - $(date)"
    echo "================================"
    sudo python3 cli/container_cli.py list
    echo ""
    echo "Container Stats:"
    for container in $(sudo ls /var/lib/mycontainer/containers/*.json 2>/dev/null | xargs -n1 basename | sed 's/.json//'); do
        echo "--- $container ---"
        sudo python3 cli/container_cli.py stats $container 2>/dev/null || echo "Not running"
        echo ""
    done
    sleep 5
done
```

### Resource Usage Analysis

```bash
#!/bin/bash
# Check cgroup stats directly

CONTAINER_NAME="mycontainer"
CGROUP_PATH="/sys/fs/cgroup/mycontainer/$CONTAINER_NAME"

if [ -d "$CGROUP_PATH" ]; then
    echo "CPU Stats:"
    cat "$CGROUP_PATH/cpu.stat"
    echo ""
    
    echo "Memory Usage:"
    cat "$CGROUP_PATH/memory.current"
    echo ""
    
    echo "Memory Max:"
    cat "$CGROUP_PATH/memory.max"
    echo ""
    
    echo "PIDs:"
    cat "$CGROUP_PATH/pids.current"
fi
```

## Troubleshooting Examples

### Check Container Processes

```bash
# List all processes in container cgroup
sudo cat /sys/fs/cgroup/mycontainer/mycontainer/cgroup.procs
```

### Verify Namespace Isolation

```bash
# Check PID namespace
sudo python3 cli/container_cli.py exec mycontainer ps aux

# Should only show processes within container
```

### Check Resource Limits

```bash
# View CPU limit
sudo cat /sys/fs/cgroup/mycontainer/mycontainer/cpu.max

# View memory limit
sudo cat /sys/fs/cgroup/mycontainer/mycontainer/memory.max
```

### Debug Container Creation

```bash
# Enable verbose output
set -x
sudo python3 cli/container_cli.py create debugtest --command /bin/sh
set +x
```

## Best Practices

1. **Always specify resource limits** for production containers:
   ```bash
   sudo python3 cli/container_cli.py create prod \
       --cpu 50 --memory 1G --pids 200 --command /app/start.sh
   ```

2. **Use appropriate rootfs** based on your needs:
   - BusyBox for minimal containers
   - Alpine for small but feature-rich
   - Ubuntu/Debian for full compatibility

3. **Monitor container stats regularly**:
   ```bash
   watch -n 1 'sudo python3 cli/container_cli.py list'
   ```

4. **Clean up stopped containers**:
   ```bash
   # List stopped containers
   sudo python3 cli/container_cli.py list | grep stopped
   
   # Delete them
   sudo python3 cli/container_cli.py delete <name>
   ```

5. **Test resource limits** before production:
   ```bash
   # Start with conservative limits
   sudo python3 cli/container_cli.py create test \
       --cpu 25 --memory 512M --command /app/test.sh
   
   # Monitor and adjust
   sudo python3 cli/container_cli.py stats test
   ```

## Scripting Examples

### Batch Container Creation

```bash
#!/bin/bash
# Create multiple containers

for i in {1..5}; do
    sudo python3 cli/container_cli.py create "worker$i" \
        --cpu 20 \
        --memory 256M \
        --command /worker.sh
done
```

### Container Health Check

```bash
#!/bin/bash
# health_check.sh

CONTAINER=$1

if sudo python3 cli/container_cli.py list | grep -q "$CONTAINER.*running"; then
    echo "Container $CONTAINER is healthy"
    exit 0
else
    echo "Container $CONTAINER is not running"
    exit 1
fi
```

### Automated Cleanup

```bash
#!/bin/bash
# cleanup_old_containers.sh

# Delete all stopped containers
sudo python3 cli/container_cli.py list | grep stopped | awk '{print $2}' | while read name; do
    sudo python3 cli/container_cli.py delete "$name"
done
```
