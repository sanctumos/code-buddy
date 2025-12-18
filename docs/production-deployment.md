# Production Deployment Guide

## 🚀 Overview

This guide covers deploying the GitHub webhook processor to a production server.

## 📋 Prerequisites

- **Server**: Linux/Windows server with public IP
- **Python**: 3.9+ installed
- **Git**: For repository cloning
- **Domain**: Optional, for custom webhook URLs
- **SSL Certificate**: Required for HTTPS webhooks

## 🏗️ Architecture

```
GitHub Organization
    ↓ (Webhook Events)
Production Server
    ↓ (HTTPS + HMAC-SHA256)
Webhook Processor (Flask)
    ↓ (Normalized Events)
Event Processing Pipeline
```

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/code-buddy.git
cd code-buddy
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy configuration template
cp config.env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```bash
# Webhook Configuration
WEBHOOK_SECRET=your-production-webhook-secret
FLASK_SECRET_KEY=your-production-flask-secret-key

# Server Configuration
PORT=5000
DEBUG=False

# Optional: Custom domain
DOMAIN=your-domain.com
```

## 🔧 Production Server Setup

### Option A: Using Gunicorn (Recommended)

```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn configuration
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
EOF

# Start with Gunicorn
gunicorn -c gunicorn.conf.py webhook_processor:app
```

### Option B: Using systemd Service

```bash
# Create systemd service file
sudo cat > /etc/systemd/system/webhook-processor.service << EOF
[Unit]
Description=GitHub Webhook Processor
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/webhook-processor
Environment=PATH=/opt/webhook-processor/venv/bin
ExecStart=/opt/webhook-processor/venv/bin/gunicorn -c gunicorn.conf.py webhook_processor:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable webhook-processor
sudo systemctl start webhook-processor
```

### Option C: Using Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "webhook_processor:app"]
```

```bash
# Build and run
docker build -t webhook-processor .
docker run -d -p 5000:5000 --env-file .env webhook-processor
```

## 🌐 Reverse Proxy Setup (Nginx)

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Webhook specific headers
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        proxy_set_header X-GitHub-Event $http_x_github_event;
        proxy_set_header X-GitHub-Delivery $http_x_github_delivery;
    }
}
```

## 🔐 SSL Certificate Setup

### Using Let's Encrypt (Certbot)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring & Logging

### Log Configuration

The webhook processor uses structured JSON logging. Configure log rotation:

```bash
# Create logrotate configuration
sudo cat > /etc/logrotate.d/webhook-processor << EOF
/opt/webhook-processor/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload webhook-processor
    endscript
}
EOF
```

### Health Monitoring

```bash
# Health check endpoint
curl https://your-domain.com/health

# Stats endpoint
curl https://your-domain.com/stats
```

## 🔧 GitHub Webhook Configuration

### Update Webhook URL

```bash
# Update webhook to production URL
gh api --method PATCH /orgs/YOUR_ORG_NAME/hooks/WEBHOOK_ID \
  --field config[url]="https://your-domain.com/webhook" \
  --field config[content_type]="json" \
  --field config[secret]="your-production-webhook-secret"
```

## 🚨 Security Considerations

### 1. Webhook Secret
- Use a strong, random webhook secret
- Store securely in environment variables
- Rotate regularly

### 2. Server Security
- Keep system updated
- Use firewall to restrict access
- Enable fail2ban for brute force protection
- Use non-root user for service

### 3. SSL/TLS
- Use strong SSL certificates
- Enable HSTS headers
- Use modern TLS versions only

## 📈 Performance Optimization

### 1. Worker Configuration
```python
# gunicorn.conf.py
workers = 4  # Adjust based on CPU cores
worker_class = "sync"
worker_connections = 1000
```

### 2. Monitoring
- Set up application monitoring (e.g., New Relic, DataDog)
- Monitor response times and error rates
- Set up alerting for failures

## 🔄 Deployment Process

### Rolling Updates

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Restart service
sudo systemctl restart webhook-processor

# Verify deployment
curl https://your-domain.com/health
```

## 🐛 Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**
   - Check webhook URL is accessible
   - Verify SSL certificate is valid
   - Check firewall rules
   - Review webhook secret configuration

2. **High Memory Usage**
   - Adjust Gunicorn worker count
   - Check for memory leaks in logs
   - Monitor system resources

3. **Slow Response Times**
   - Check server resources
   - Review network connectivity
   - Optimize worker configuration

### Debug Mode

```bash
# Enable debug mode (development only)
export DEBUG=True
python webhook_processor.py
```

### Log Analysis

```bash
# View recent logs
tail -f /opt/webhook-processor/logs/webhook.log

# Search for errors
grep "ERROR" /opt/webhook-processor/logs/webhook.log

# Monitor webhook events
grep "Event processed" /opt/webhook-processor/logs/webhook.log
```

## 🔮 Next Steps

1. **Monitoring**: Set up comprehensive monitoring
2. **Scaling**: Implement horizontal scaling for high volume
3. **Event Processing**: Add custom event processing logic

---

**Production Checklist:**
- [ ] Server configured with SSL
- [ ] Environment variables set
- [ ] Service running with systemd
- [ ] Nginx reverse proxy configured
- [ ] GitHub webhook updated
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Security hardening completed

