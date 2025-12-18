# API Reference

## Overview

The GitHub webhook processor provides REST API endpoints for receiving GitHub webhooks and monitoring system health.

## 🌐 Base URL

```
Production: https://your-domain.com
Development: http://localhost:5000
```

## 📡 Endpoints

### POST /webhook

Main webhook endpoint for receiving GitHub organization events.

#### Headers Required

| Header | Type | Description |
|--------|------|-------------|
| `X-Hub-Signature-256` | string | HMAC-SHA256 signature of payload |
| `X-GitHub-Event` | string | Event type (issues, push, pull_request, etc.) |
| `X-GitHub-Delivery` | string | Unique delivery ID |
| `Content-Type` | string | application/json |

#### Request Body

GitHub webhook payload (varies by event type).

#### Response

**Success (200 OK):**
```json
{
  "status": "processed",
  "event_id": "delivery-id-123",
  "processed_at": "2025-10-10T18:03:18Z",
  "event_count": 42
}
```

**Error (400 Bad Request):**
```json
{
  "status": "error",
  "message": "Invalid signature",
  "error_code": "INVALID_SIGNATURE"
}
```

**Error (401 Unauthorized):**
```json
{
  "status": "error",
  "message": "Signature verification failed",
  "error_code": "SIGNATURE_VERIFICATION_FAILED"
}
```

#### Example Request

```bash
curl -X POST https://your-domain.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=abc123..." \
  -H "X-GitHub-Event: issues" \
  -H "X-GitHub-Delivery: delivery-123" \
  -d '{
    "action": "opened",
    "issue": {
      "id": 123456789,
      "number": 42,
      "title": "Test Issue",
      "body": "This is a test issue"
    },
    "repository": {
      "id": 111222333,
      "name": "test-repo",
      "full_name": "test/test-repo"
    },
    "sender": {
      "login": "testuser",
      "id": 987654321
    }
  }'
```

### GET /health

Health check endpoint for monitoring system status.

#### Response

**Success (200 OK):**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "events_processed": 42,
  "timestamp": "2025-10-10T18:03:18Z"
}
```

#### Example Request

```bash
curl https://your-domain.com/health
```

### GET /stats

Detailed statistics endpoint for monitoring and analytics.

#### Response

**Success (200 OK):**
```json
{
  "uptime_seconds": 3600,
  "events_processed": 42,
  "start_time": "2025-10-10T17:03:18Z",
  "webhook_secret_configured": true,
  "debug_mode": false
}
```

#### Example Request

```bash
curl https://your-domain.com/stats
```

## 🔐 Authentication

### HMAC Signature Verification

All webhook requests must include a valid HMAC-SHA256 signature.

#### Signature Format

```
X-Hub-Signature-256: sha256=<hex_digest>
```

#### Signature Generation

```python
import hmac
import hashlib

def generate_signature(payload: bytes, secret: str) -> str:
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"
```

#### Example

```python
payload = b'{"action": "opened", "issue": {...}}'
secret = "your_webhook_secret"
signature = generate_signature(payload, secret)
# Result: "sha256=abc123def456..."
```

## 📊 Event Types

### Supported GitHub Events

| Event Type | Description |
|------------|-------------|
| `issues` | Issue created, closed, assigned, labeled |
| `pull_request` | PR opened, closed, merged, reviewed |
| `push` | Code commits, branch updates, tags |
| `release` | Release published, unpublished |
| `repository` | Repository created, deleted, archived |
| `issue_comment` | Comments on issues |
| `pull_request_review_comment` | Comments on PRs |
| `create` | Branch/tag creation |
| `delete` | Branch/tag deletion |

### Event Processing Flow

1. **Receive Webhook** → Validate HMAC signature
2. **Parse Event** → Extract relevant data
3. **Normalize Data** → Standardize format
4. **Process Event** → Custom processing logic

## 🔄 Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2025-10-10T18:03:18Z"
}
```

### Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_SIGNATURE` | 400 | Invalid HMAC signature format |
| `SIGNATURE_VERIFICATION_FAILED` | 401 | HMAC signature verification failed |
| `MISSING_HEADERS` | 400 | Required headers missing |
| `INVALID_JSON` | 400 | Invalid JSON payload |
| `UNSUPPORTED_EVENT` | 400 | Unsupported event type |

## 📈 Rate Limiting

### GitHub Webhook Limits

- **Rate Limit**: 60 requests per hour per webhook
- **Burst Limit**: 10 requests per minute
- **Retry Policy**: GitHub retries failed deliveries

## 🧪 Testing

### Manual Testing

```bash
# Test health endpoint
curl https://your-domain.com/health

# Test webhook endpoint
curl -X POST https://your-domain.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=..." \
  -H "X-GitHub-Event: issues" \
  -H "X-GitHub-Delivery: test-123" \
  -d '{"action": "opened", "issue": {...}}'
```

## 📊 Monitoring

### Health Check Integration

The `/health` endpoint is designed for load balancer health checks:

```bash
# Load balancer health check
curl -f https://your-domain.com/health || exit 1
```

### Metrics Collection

The `/stats` endpoint provides metrics for monitoring systems:

```bash
# Collect metrics
curl https://your-domain.com/stats | jq '.events_processed'
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBHOOK_SECRET` | ✅ | - | GitHub webhook secret |
| `FLASK_SECRET_KEY` | ✅ | - | Flask secret key |
| `PORT` | ❌ | 5000 | Server port |
| `DEBUG` | ❌ | False | Debug mode |
| `LOG_LEVEL` | ❌ | INFO | Logging level |

### Webhook Configuration

GitHub webhook must be configured with:

- **URL**: `https://your-domain.com/webhook`
- **Content Type**: `application/json`
- **Secret**: Must match `WEBHOOK_SECRET`
- **Events**: All events (`["*"]`) or specific events

## 🚀 Performance

### Response Times

| Endpoint | Typical Response Time | Timeout |
|----------|----------------------|---------|
| `/webhook` | 200-500ms | 30s |
| `/health` | 50-100ms | 5s |
| `/stats` | 100-200ms | 10s |

### Throughput

- **Concurrent Requests**: Up to 100 (Gunicorn default)
- **Events per Second**: ~10-20
- **Memory Usage**: ~50-100MB per worker
- **CPU Usage**: Low (mostly I/O bound)

## 🔒 Security

### HTTPS Requirements

- **Production**: HTTPS required
- **Development**: HTTP allowed for localhost
- **Certificates**: Valid SSL certificates required

### Input Validation

- **HMAC Verification**: All webhook requests verified
- **JSON Validation**: Payload structure validated
- **Header Validation**: Required headers checked
- **Size Limits**: Payload size limited to 1MB

### Error Information

- **No Sensitive Data**: Errors don't expose internal details
- **Logging**: Detailed errors logged internally
- **Monitoring**: Error rates monitored and alerted

