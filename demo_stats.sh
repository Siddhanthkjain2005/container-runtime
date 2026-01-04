#!/bin/bash
# Advanced demo showing stats monitoring

set -e

echo "================================================"
echo "Container Stats Demonstration"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

cd "$(dirname "$0")"

echo "This demo shows how container stats would work with long-running containers."
echo ""
echo "Note: The current CLI implementation waits for containers to complete,"
echo "so stats and dashboard work best with containers running in separate processes."
echo ""

echo "1. Creating a container with resource limits..."
echo "   CPU: 50%, Memory: 256M"
echo ""

# Run container in background via direct runtime
echo "Starting container 'statstest' in background..."
CPU_LIMIT=50 MEMORY_LIMIT=256M ./container_runtime statstest ./rootfs /sleep_test.sh &
CONTAINER_PID=$!
echo "Container process PID: $CONTAINER_PID"

# Give it time to start
sleep 2

# Create metadata file for the CLI to use
mkdir -p /var/lib/mycontainer/containers
cat > /var/lib/mycontainer/containers/statstest.json << EOF
{
  "name": "statstest",
  "pid": $CONTAINER_PID,
  "rootfs": "$(pwd)/rootfs",
  "command": "/sleep_test.sh",
  "created_at": $(date +%s),
  "limits": {
    "cpu": 50,
    "memory": "256M"
  },
  "status": "running"
}
EOF

echo ""
echo "2. Checking if container is running..."
python3 cli/container_cli.py list

echo ""
echo "3. Getting container stats..."
echo "   (This will take 2 seconds to calculate CPU usage)"
python3 cli/container_cli.py stats statstest 2>&1 || echo "Stats may not be available if container exited"

echo ""
echo "4. Waiting a few seconds..."
sleep 3

echo ""
echo "5. Getting updated stats..."
python3 cli/container_cli.py stats statstest 2>&1 || echo "Container may have stopped"

echo ""
echo "6. Cleaning up..."
python3 cli/container_cli.py delete statstest

# Make sure the background process is killed
kill $CONTAINER_PID 2>/dev/null || true

echo ""
echo "================================================"
echo "Stats Demonstration Complete!"
echo "================================================"
