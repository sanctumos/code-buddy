# Code Buddy

A robust system for keeping your **Sanctum** and **Letta** AI agents informed about your coding activities through GitHub webhooks and a Cursor-addressable MCP (Model Context Protocol) server.

## 🎯 Purpose

Code Buddy bridges the gap between your development workflow and your AI agents by:

- **Capturing GitHub Events**: Receives webhooks for all coding activities (commits, PRs, issues, releases, etc.)
- **Processing & Normalizing**: Validates and normalizes GitHub events into a consistent format
- **MCP Integration**: Exposes events through a Cursor-addressable MCP server for real-time agent access
- **Agent Awareness**: Keeps Sanctum and Letta agents in the loop about your coding activities automatically

## 🏗️ Architecture

```
GitHub Organization
    ↓ (Webhook Events)
    ├─→ Webhook Processor (Flask)
    │   ├─→ HMAC Signature Verification
    │   ├─→ Event Parsing & Normalization
    │   ├─→ Event Processing
    │   └─→ Event Store (events.json)
    │
    └─→ MCP Server (Cursor-addressable)
        ├─→ Event Store (events.json)
        ├─→ MCP Tools (get_recent_events, get_event_stats, etc.)
        ├─→ Sanctum Agent Access
        └─→ Letta Agent Access
```

### Components

1. **GitHub Webhook Processor** (`webhook_processor.py`)
   - Receives GitHub organization webhook events
   - Validates HMAC-SHA256 signatures for security
   - Parses and normalizes events (issues, PRs, pushes, releases, etc.)
   - Stores events in shared event store
   - Provides health check and statistics endpoints

2. **MCP Server** (`mcp_server.py`)
   - Cursor-addressable Model Context Protocol server
   - Exposes GitHub events to AI agents via MCP tools
   - Server-Sent Events (SSE) transport for real-time communication
   - Query interface for agents to access coding activity history
   - Lightweight implementation (~300 lines)

3. **Event Store** (`event_store.py`)
   - Shared event storage (file-based persistence)
   - Thread-safe event storage and retrieval
   - Filtering by event type, repository, and time range
   - Statistics and querying capabilities

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- GitHub organization admin access
- A server/domain for webhook endpoint (or use localhost for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sanctumos/code-buddy.git
   cd code-buddy
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp config.env.example .env
   # Edit .env with your settings
   ```

4. **Set up GitHub webhook**
   ```bash
   # See docs/github-webhook-setup.md for detailed instructions
   gh api --method POST /orgs/YOUR_ORG_NAME/hooks \
     -f name='web' \
     -f config='{"url":"https://your-domain.com/webhook","content_type":"json","secret":"your_webhook_secret"}' \
     -f events='["*"]' \
     -F active=true
   ```

5. **Start the services**

   **Terminal 1 - Webhook Processor:**
   ```bash
   python webhook_processor.py
   ```

   **Terminal 2 - MCP Server:**
   ```bash
   python mcp_server.py
   ```

   The webhook processor runs on port 5000 (default) and the MCP server runs on port 8001 (default).

## 📋 Configuration

### Environment Variables

Create a `.env` file from `config.env.example`:

```bash
# Webhook Configuration
WEBHOOK_SECRET=your_webhook_secret_here          # Random string for HMAC verification
FLASK_SECRET_KEY=your-flask-secret-key-here      # Flask session secret

# Server Configuration
PORT=5000                                        # Server port
DEBUG=False                                      # Debug mode
LOG_LEVEL=INFO                                   # Logging level
```

### GitHub Webhook Secret

The `WEBHOOK_SECRET` is **not** a Personal Access Token (PAT). It's a shared secret string used for HMAC signature verification:

- Generate a random secret: `python -c "import secrets; print(secrets.token_hex(32))"`
- Must match the secret configured in your GitHub webhook
- Used to verify webhook requests are legitimate

## 🔧 How It Works

### 1. GitHub Webhook Flow

1. **Event Occurs**: You push code, create a PR, open an issue, etc.
2. **GitHub Sends Webhook**: GitHub sends a POST request to your webhook endpoint
3. **Signature Verification**: Code Buddy verifies the HMAC-SHA256 signature
4. **Event Parsing**: Event is parsed and normalized into a consistent format
5. **Processing**: Event is processed and made available to agents

### 2. Event Normalization

All GitHub events are normalized into a consistent structure:

```json
{
  "event_type": "issues",
  "delivery_id": "unique-delivery-id",
  "timestamp": "2025-01-15T10:30:00Z",
  "action": "opened",
  "repository": {
    "id": 123456789,
    "name": "my-repo",
    "full_name": "org/my-repo",
    "url": "https://github.com/org/my-repo"
  },
  "sender": {
    "login": "username",
    "id": 987654321
  },
  "organization": {
    "login": "org-name",
    "id": 444555666
  },
  "issue": {
    "number": 42,
    "title": "Bug fix needed",
    "body": "Description...",
    "state": "open"
  }
}
```

### 3. Agent Integration

**Sanctum & Letta Agents** can access events through:

- **MCP Server** (Coming Soon): Real-time event streaming via Cursor
- **Event History**: Query interface for past events
- **Event Filtering**: Subscribe to specific event types

## 📡 API Endpoints

### POST /webhook
Main webhook endpoint for receiving GitHub events.

**Headers Required:**
- `X-Hub-Signature-256`: HMAC-SHA256 signature
- `X-GitHub-Event`: Event type
- `X-GitHub-Delivery`: Unique delivery ID

### GET /health
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "events_processed": 42,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### GET /stats
Statistics endpoint for monitoring and analytics.

**Response:**
```json
{
  "uptime_seconds": 3600,
  "events_processed": 42,
  "start_time": "2025-01-15T09:30:00Z",
  "webhook_secret_configured": true,
  "debug_mode": false
}
```

See [docs/api-reference.md](docs/api-reference.md) for complete API documentation.

## 📚 Documentation

- **[GitHub Webhook Setup](docs/github-webhook-setup.md)** - Complete guide for setting up GitHub webhooks
- **[API Reference](docs/api-reference.md)** - Detailed API endpoint documentation
- **[Production Deployment](docs/production-deployment.md)** - Production deployment guide

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest test_webhook_processor.py -v
```

## 🔐 Security

- **HMAC Signature Verification**: All webhook requests are verified using HMAC-SHA256
- **Environment Variables**: Sensitive configuration stored in environment variables
- **HTTPS Required**: Production deployments require SSL/TLS
- **Input Validation**: All payloads are validated before processing

## 🔌 MCP Server Tools

The MCP server exposes the following tools for AI agents:

### `get_recent_events`
Get recent GitHub webhook events with optional filtering.

**Parameters:**
- `event_type` (optional): Filter by event type (e.g., 'issues', 'push', 'pull_request')
- `repository` (optional): Filter by repository name
- `limit` (optional): Maximum number of events (default: 50, max: 100)
- `since` (optional): ISO timestamp to filter events since

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_recent_events",
    "arguments": {
      "event_type": "issues",
      "limit": 10
    }
  }
}
```

### `get_event_stats`
Get statistics about stored events.

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_event_stats",
    "arguments": {}
  }
}
```

### `get_event_by_id`
Get a specific event by its delivery ID.

**Parameters:**
- `delivery_id` (required): The delivery ID of the event

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_event_by_id",
    "arguments": {
      "delivery_id": "12345678-1234-1234-1234-123456789abc"
    }
  }
}
```

## 🚧 Roadmap

- [x] GitHub webhook processor
- [x] Event parsing and normalization
- [x] Health check and statistics endpoints
- [x] MCP server implementation
- [x] Event storage and querying
- [ ] Cursor integration documentation
- [ ] Sanctum agent integration examples
- [ ] Letta agent integration examples
- [ ] Real-time event streaming enhancements

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0 - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built on top of the webhook processor from [animus-discord](https://github.com/animusuno/animus-discord)
- Designed for integration with Sanctum and Letta AI agents

---

**Status**: 🚧 In Development | **Version**: 0.1.0



