# Deployment Guide

This guide covers various deployment options for the Polymarket Arbitrage Bot.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Systemd Service](#systemd-service)
- [VPS Deployment](#vps-deployment)
- [Raspberry Pi](#raspberry-pi)
- [Monitoring & Maintenance](#monitoring--maintenance)

## Prerequisites

### System Requirements

- **CPU**: 1+ cores (2+ recommended)
- **RAM**: 512MB minimum (1GB+ recommended)
- **Storage**: 1GB for application + logs
- **Network**: Stable internet connection with low latency

### Software Requirements

- Python 3.9 or higher
- pip (Python package manager)
- Git
- (Optional) Docker & Docker Compose
- (Optional) systemd for service management

### API Access

- **Polymarket**: API key and Ethereum private key
- **Exchanges**: API keys for Binance, Coinbase, etc.
- **Funds**: Capital on both Polymarket and exchanges

## Local Development

For testing and development:

```bash
# Clone repository
git clone https://github.com/gabubu-dev/polymarket-arbitrage-bot.git
cd polymarket-arbitrage-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.json config.json
# Edit config.json with your API keys

# Run tests
pytest tests/ -v

# Run bot
python bot.py
```

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t polymarket-bot .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Configuration

1. Create `config.json` in the project root
2. Docker Compose will mount it automatically
3. Logs are persisted to `./logs/`

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Systemd Service

Running as a system service on Linux:

### Setup

```bash
# 1. Edit the service file
cp deployment/polymarket-bot.service /tmp/polymarket-bot.service
nano /tmp/polymarket-bot.service

# Update these fields:
#   - User=YOUR_USERNAME
#   - WorkingDirectory=/full/path/to/bot
#   - ExecStart=/full/path/to/bot/venv/bin/python /full/path/to/bot/bot.py

# 2. Copy to systemd
sudo cp /tmp/polymarket-bot.service /etc/systemd/system/

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Enable service (start on boot)
sudo systemctl enable polymarket-bot

# 5. Start service
sudo systemctl start polymarket-bot
```

### Management

```bash
# Check status
sudo systemctl status polymarket-bot

# View logs
sudo journalctl -u polymarket-bot -f

# Restart
sudo systemctl restart polymarket-bot

# Stop
sudo systemctl stop polymarket-bot

# Disable auto-start
sudo systemctl disable polymarket-bot
```

## VPS Deployment

Recommended for production use due to low latency.

### Provider Recommendations

- **DigitalOcean**: Droplets in NYC or Singapore (close to exchanges)
- **AWS EC2**: t3.micro or t3.small (us-east-1)
- **Linode**: Nanode or Shared instances
- **Vultr**: Optimized Cloud Compute

### Setup on Ubuntu 22.04

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git

# 3. Create bot user
sudo useradd -m -s /bin/bash botuser
sudo su - botuser

# 4. Clone and setup
git clone https://github.com/gabubu-dev/polymarket-arbitrage-bot.git
cd polymarket-arbitrage-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configure
cp config.example.json config.json
nano config.json  # Add your API keys

# 6. Test run
python bot.py

# 7. Exit and setup systemd service (as root)
exit
sudo cp /home/botuser/polymarket-arbitrage-bot/deployment/polymarket-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/polymarket-bot.service  # Update paths
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot
```

### Security Hardening

```bash
# 1. Setup firewall
sudo ufw allow ssh
sudo ufw enable

# 2. Disable root SSH
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd

# 3. Setup fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban

# 4. Encrypt config file
# Store sensitive keys in environment variables or encrypted vault
```

### Network Optimization

```bash
# Reduce latency
sudo sysctl -w net.ipv4.tcp_low_latency=1

# Increase connection limits
ulimit -n 10000
```

## Raspberry Pi

Run the bot on a Raspberry Pi for low-power 24/7 operation.

### Requirements

- Raspberry Pi 4 (2GB+ RAM recommended)
- MicroSD card (16GB+)
- Raspberry Pi OS Lite
- Ethernet connection (lower latency than WiFi)

### Installation

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3-pip python3-venv git

# 3. Clone and setup (same as Linux)
git clone https://github.com/gabubu-dev/polymarket-arbitrage-bot.git
cd polymarket-arbitrage-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure
cp config.example.json config.json
nano config.json

# 5. Setup systemd service
sudo cp deployment/polymarket-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/polymarket-bot.service
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot
```

### Performance Tips

- Use Ethernet instead of WiFi
- Overclock if needed (but watch temperatures)
- Use lightweight system (no GUI)
- Disable unnecessary services

## Monitoring & Maintenance

### Log Management

```bash
# View real-time logs
tail -f logs/bot.log

# View trade log
tail -f logs/trades.log

# Rotate logs automatically
sudo apt install logrotate
sudo nano /etc/logrotate.d/polymarket-bot
```

logrotate config:
```
/path/to/bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Health Monitoring

```bash
# Check bot health
python examples/analyze_performance.py

# System health
htop  # CPU/RAM usage
iotop  # Disk I/O
nethogs  # Network usage
```

### Backup Strategy

```bash
# Backup configuration
cp config.json config.backup.json

# Backup logs and data
tar -czf backup-$(date +%Y%m%d).tar.gz logs/ data/ config.json

# Automated daily backup
crontab -e
# Add: 0 2 * * * tar -czf /backup/bot-$(date +\%Y\%m\%d).tar.gz /path/to/bot/logs /path/to/bot/data
```

### Updates

```bash
# Pull latest code
cd /path/to/bot
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart polymarket-bot
```

### Notifications

Setup webhook notifications (Discord/Slack/Telegram):

```json
{
  "notifications": {
    "enabled": true,
    "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK"
  }
}
```

### Alerting

Setup alerts for critical events:

- Bot crashes (use systemd email notifications)
- Large losses (configured in risk management)
- API errors (monitored by bot health checks)
- Low balance warnings

## Troubleshooting

### Bot Won't Start

```bash
# Check logs
tail -100 logs/bot.log

# Check systemd status
sudo systemctl status polymarket-bot

# Test manually
source venv/bin/activate
python bot.py
```

### No Opportunities Detected

- Lower divergence threshold in config
- Verify exchange connections are active
- Check that markets exist on Polymarket
- Ensure correct symbols are configured

### High Memory Usage

- Reduce max_positions
- Implement log rotation
- Restart bot daily via cron

### Network Issues

- Check exchange API status
- Verify API keys are correct
- Test network latency: `ping api.binance.com`
- Switch to different exchange region

## Best Practices

1. **Start Small**: Test with minimum position sizes
2. **Monitor Regularly**: Check logs and performance daily
3. **Keep Updated**: Pull updates and security patches
4. **Backup Config**: Store API keys securely
5. **Test Changes**: Always test configuration changes
6. **Set Alerts**: Get notified of critical issues
7. **Review Performance**: Analyze trades weekly
8. **Adjust Strategy**: Optimize based on performance

## Support

For deployment issues:
- Check logs first
- Review documentation
- Open GitHub issue with details
- Include system specs and error messages

---

**Security Note**: Never commit `config.json` with real API keys to version control!
