# ChargePoint Grid Guard

Monitors Tesla Powerwall grid status and automatically stops EV charging when the grid goes offline. This prevents your Powerwall from draining while trying to charge your car during a power outage.

## Features

- 🔌 Monitors Powerwall grid status via pypowerwall
- 🚗 Automatically stops ChargePoint charging when grid goes offline
- ⚡ Optionally resumes charging when grid is restored
- 🐳 Docker containerized for easy deployment
- 🏗️ Multi-arch support (amd64/arm64)

## Quick Start

```bash
docker run -d \
  --name chargepoint-grid-guard \
  -e CHARGEPOINT_USERNAME=your_email@example.com \
  -e CHARGEPOINT_PASSWORD=your_password \
  -e POWERWALL_URL=http://pypowerwall:8675 \
  ghcr.io/mccahan/chargepoint-grid-guard:main
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHARGEPOINT_USERNAME` | Yes | - | Your ChargePoint account email |
| `CHARGEPOINT_PASSWORD` | Yes | - | Your ChargePoint account password |
| `POWERWALL_URL` | No | `http://pypowerwall:8675` | pypowerwall API URL |
| `POLL_INTERVAL` | No | `30` | Seconds between status checks |
| `RESUME_CHARGING` | No | `false` | Resume charging when grid is restored |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DRY_RUN` | No | `false` | Log actions without executing them |

## Docker Compose

```yaml
version: '3.8'

services:
  chargepoint-grid-guard:
    image: ghcr.io/mccahan/chargepoint-grid-guard:main
    container_name: chargepoint-grid-guard
    restart: unless-stopped
    environment:
      CHARGEPOINT_USERNAME: ${CHARGEPOINT_USERNAME}
      CHARGEPOINT_PASSWORD: ${CHARGEPOINT_PASSWORD}
      POWERWALL_URL: http://pypowerwall:8675
      POLL_INTERVAL: 30
      RESUME_CHARGING: "false"
```

## How It Works

1. Polls pypowerwall every `POLL_INTERVAL` seconds
2. Checks the `GridStatus` field (1 = online, 0 = offline)
3. When grid goes offline:
   - Checks for active ChargePoint charging session
   - Stops the charging session to preserve Powerwall capacity
4. When grid is restored (if `RESUME_CHARGING=true`):
   - Resumes charging on the previously stopped device

## Requirements

- [pypowerwall](https://github.com/jasonacox/pypowerwall) running and accessible
- ChargePoint Home Flex charger with active account
- Docker

## Related Projects

- [python-chargepoint](https://github.com/mbillow/python-chargepoint) - ChargePoint API client
- [pypowerwall](https://github.com/jasonacox/pypowerwall) - Tesla Powerwall API
- [chargepoint-mqtt](https://github.com/mccahan/chargepoint-mqtt) - ChargePoint status to MQTT

## License

MIT
