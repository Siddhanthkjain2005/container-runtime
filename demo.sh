#!/bin/bash
# Demo script for container runtime

set -e

echo "================================================"
echo "Container Runtime System - Demonstration"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

cd "$(dirname "$0")"

echo "1. Building container runtime..."
make clean > /dev/null 2>&1
make > /dev/null 2>&1
echo "   ✓ Build successful"
echo ""

echo "2. Listing containers (should be empty)..."
python3 cli/container_cli.py list
echo ""

echo "3. Creating a short-lived container..."
python3 cli/container_cli.py create demo1 --cpu 50 --memory 512M --command /init.sh
echo ""

echo "4. Listing containers after creation..."
python3 cli/container_cli.py list
echo ""

echo "5. Deleting the container..."
python3 cli/container_cli.py delete demo1
echo ""

echo "6. Testing direct container runtime..."
echo "   Running: ./container_runtime demo2 ./rootfs /bin/echo 'Hello from container!'"
CPU_LIMIT=30 MEMORY_LIMIT=256M ./container_runtime demo2 ./rootfs /bin/echo "Hello from container!"
echo ""

echo "7. Testing container with resource limits..."
echo "   CPU: 75%, Memory: 1G"
CPU_LIMIT=75 MEMORY_LIMIT=1G ./container_runtime demo3 ./rootfs /init.sh
echo ""

echo "================================================"
echo "Demonstration Complete!"
echo "================================================"
echo ""
echo "Available commands:"
echo "  sudo python3 cli/container_cli.py create <name> [options]"
echo "  sudo python3 cli/container_cli.py list"
echo "  sudo python3 cli/container_cli.py stats <name>"
echo "  sudo python3 cli/container_cli.py delete <name>"
echo "  sudo python3 cli/container_cli.py dashboard"
echo ""
echo "Direct runtime usage:"
echo "  sudo ./container_runtime <name> <rootfs> <command>"
echo ""
