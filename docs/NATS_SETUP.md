# NATS Setup Guide

## Quick Start

### 1. Start NATS Server

```bash
# Using Docker Compose (recommended)
docker-compose up -d nats

# Verify it's running
docker-compose ps

# Check logs
docker-compose logs nats
```

### 2. Test Connection

```bash
# Run example
python examples/nats_example.py

# Expected output:
# === Example 1: Broadcast ===
# [RECEIVED] architect-001 → status_update: {...}
# ...
# ✓ Disconnected from NATS
```

### 3. Monitor NATS

Open <http://localhost:8222> in your browser to see:

- Active connections
- Message statistics
- Subject subscriptions
- Server health

## Ports

- **4222** - Client connections (Python agents connect here)
- **8222** - HTTP monitoring UI
- **6222** - Cluster connections (for multi-node setup)

## Installation Options

### Option 1: Docker Compose (Recommended)

Already configured in `docker-compose.yml`:

```yaml
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"
      - "8222:8222"
      - "6222:6222"
    command:
      - "-js"   # Enable JetStream
      - "-m"    # Enable monitoring
      - "8222"
```

### Option 2: Local Binary

```bash
# macOS
brew install nats-server

# Ubuntu/Debian
wget https://github.com/nats-io/nats-server/releases/download/v2.10.7/nats-server-v2.10.7-linux-amd64.tar.gz
tar -xzf nats-server-v2.10.7-linux-amd64.tar.gz
sudo mv nats-server /usr/local/bin/

# Run
nats-server -js -m 8222
```

### Option 3: From Source

```bash
git clone https://github.com/nats-io/nats-server.git
cd nats-server
go build
./nats-server -js -m 8222
```

## Configuration

### Basic Configuration

NATS runs with defaults, but you can customize:

```bash
# Create nats-server.conf
cat > nats-server.conf << 'EOF'
# Server name
server_name: orchestrator-nats

# Client connection port
port: 4222

# HTTP monitoring port
http_port: 8222

# Enable JetStream for persistence
jetstream {
    store_dir: "/data/jetstream"
    max_memory_store: 1GB
    max_file_store: 10GB
}

# Logging
debug: false
trace: false
logtime: true

# Limits
max_connections: 1000
max_payload: 1MB
EOF

# Run with config
nats-server -c nats-server.conf
```

### Clustering (Production)

For high availability:

```yaml
# docker-compose.yml
services:
  nats-1:
    image: nats:latest
    command: "-cluster nats://0.0.0.0:6222 -routes=nats://nats-2:6222,nats://nats-3:6222"

  nats-2:
    image: nats:latest
    command: "-cluster nats://0.0.0.0:6222 -routes=nats://nats-1:6222,nats://nats-3:6222"

  nats-3:
    image: nats:latest
    command: "-cluster nats://0.0.0.0:6222 -routes=nats://nats-1:6222,nats://nats-2:6222"
```

## Verification

### Check Server Status

```bash
# Using curl
curl http://localhost:8222/varz | jq

# Expected output includes:
# {
#   "server_id": "...",
#   "version": "2.10.7",
#   "connections": 0,
#   "in_msgs": 0,
#   "out_msgs": 0,
#   ...
# }
```

### Test from Python

```python
import asyncio
from nats.aio.client import Client as NATS

async def test_connection():
    nc = await NATS().connect("nats://localhost:4222")
    print(f"Connected: {nc.is_connected}")
    await nc.close()

asyncio.run(test_connection())
# Output: Connected: True
```

## Monitoring

### Built-in HTTP Endpoints

- `/varz` - General server info
- `/connz` - Connection details
- `/routez` - Routing info
- `/subsz` - Subscription stats
- `/jsz` - JetStream stats

```bash
# View all endpoints
curl http://localhost:8222/help
```

### NATS CLI (Optional)

```bash
# Install NATS CLI
brew install nats-io/nats-tools/nats

# Check server
nats server check

# Monitor in real-time
nats server events

# View subject tree
nats server subjects
```

## Troubleshooting

### Connection Refused

```bash
# Check if NATS is running
docker-compose ps nats

# Check logs
docker-compose logs nats

# Restart
docker-compose restart nats
```

### Port Already in Use

```bash
# Find process using port 4222
lsof -i :4222

# Kill it
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Python Connection Issues

```python
# Try with error handling
import asyncio
from nats.aio.client import Client as NATS

async def connect_with_retry():
    nc = NATS()
    try:
        await nc.connect(
            servers=["nats://localhost:4222"],
            connect_timeout=5,
            max_reconnect_attempts=3,
        )
        print("✓ Connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
    finally:
        if nc.is_connected:
            await nc.close()

asyncio.run(connect_with_retry())
```

## Performance Tuning

### For Development

Default settings are fine.

### For Production

```conf
# nats-server.conf
max_connections: 10000
max_payload: 10MB
write_deadline: "5s"

# JetStream limits
jetstream {
    max_memory_store: 10GB
    max_file_store: 100GB
}
```

## Security (Production)

### Enable Authentication

```conf
# nats-server.conf
authorization {
    users = [
        {user: orchestrator, password: "secret123"}
    ]
}
```

```python
# Python connection with auth
nc = await NATS().connect(
    "nats://orchestrator:secret123@localhost:4222"
)
```

### Enable TLS

```conf
# nats-server.conf
tls {
    cert_file: "/path/to/server-cert.pem"
    key_file: "/path/to/server-key.pem"
    ca_file: "/path/to/ca.pem"
}
```

## Next Steps

1. ✓ Start NATS: `docker-compose up -d nats`
2. ✓ Test connection: `python examples/nats_example.py`
3. ✓ Review architecture: [docs/nats-architecture.md](nats-architecture.md)
4. ✓ Implement agent communication using `src/coordination/nats_bus.py`

## Resources

- [NATS Documentation](https://docs.nats.io/)
- [nats-py GitHub](https://github.com/nats-io/nats.py)
- [NATS Monitoring](https://docs.nats.io/running-a-nats-service/nats_admin/monitoring)
- [JetStream Guide](https://docs.nats.io/nats-concepts/jetstream)
