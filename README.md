# Intelligent WhatsApp Automation System

An AI-powered WhatsApp automation system that intelligently engages in personal conversations, builds rapport, and facilitates meaningful connections while keeping users informed.

## 🌟 Features

- **Intelligent Conversation Management**: AI-driven responses that adapt to conversation context and progression stages
- **Memory Graph System**: Maintains comprehensive knowledge about contacts with fact extraction and updating
- **Policy-Based Safety**: Multiple safety checks including sensitivity screening and rate limiting
- **Progression Tracking**: Monitors conversation stages from discovery through confirmation
- **Comprehensive Briefings**: Generates detailed briefings when dates are confirmed
- **Multi-Layer Architecture**: Clean separation of concerns with API, Perception, Cognition, and Persistence layers

## 🏗 Architecture

### Four-Layer System Design

1. **API Control Plane**: WhatsApp Cloud API integration and webhook handling
2. **Perception Layer**: Message processing, media handling, and semantic enrichment
3. **Cognition Layer**: Memory management, policy enforcement, and reply generation
4. **Persistence Layer**: Database operations, embeddings, and email notifications

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- WhatsApp Business Account with Cloud API access
- Docker and Docker Compose (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/whatsapp-automation.git
cd whatsapp-automation
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Configure your WhatsApp credentials in `.env`:
```
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_verify_token
WHATSAPP_WEBHOOK_SECRET=your_webhook_secret
```

4. Start with Docker Compose:
```bash
docker-compose up -d
```

Or install locally:
```bash
pip install -r requirements.txt
alembic upgrade head
python -m src.main
```

## 📋 Configuration

### WhatsApp Setup

1. Create a WhatsApp Business Account at [Meta for Developers](https://developers.facebook.com)
2. Set up a WhatsApp Business App
3. Configure webhook URL: `https://yourdomain.com/webhook`
4. Subscribe to webhook fields: `messages`, `message_status`

### Environment Variables

Key configuration options:

- `LLM_PROVIDER`: Choose between `openai` or `anthropic`
- `LLM_MODEL_NAME`: Model to use (e.g., `gpt-4-turbo-preview`)
- `ENABLE_MEDIA_PROCESSING`: Enable audio/image processing
- `MAX_CONCURRENT_CONVERSATIONS`: Limit concurrent active conversations

## 🔧 Development

### Project Structure

```
├── src/
│   ├── api_control_plane/     # WhatsApp API integration
│   ├── perception_layer/      # Message processing
│   ├── cognition_layer/       # AI logic and memory
│   ├── persistence_layer/     # Database and storage
│   ├── core/                  # Shared components
│   └── utils/                 # Utilities
├── config/                    # Configuration
├── tests/                     # Test suite
├── alembic/                   # Database migrations
└── docker/                    # Docker configurations
```

### Running Tests

```bash
pytest tests/
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## 📊 Monitoring

The system includes Prometheus metrics exposed on port 9090:

- Message processing times
- Active conversations
- API errors
- Queue depths

Access metrics at `http://localhost:9090/metrics`

## 🔒 Security Considerations

- All API tokens are encrypted at rest
- Webhook signatures are verified
- Sensitive message content is redacted in logs
- Rate limiting prevents abuse
- Human intervention for sensitive topics

## 🤝 Ethical Usage

This system is designed for personal use with explicit consent. Users must:

1. Obtain consent from contacts before enabling AI engagement
2. Clearly communicate when AI is being used
3. Respect WhatsApp's Business Policy and terms of service
4. Use the system responsibly and ethically

## 📝 API Documentation

### Webhook Endpoints

- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - Receive WhatsApp events
- `GET /health` - Health check endpoint

### Internal APIs

The system uses internal message queues for communication between layers.

## 🐛 Troubleshooting

### Common Issues

1. **Webhook not receiving messages**
   - Verify webhook URL is publicly accessible
   - Check webhook verification token matches
   - Ensure webhook is subscribed to correct fields

2. **Messages not being processed**
   - Check Redis connection
   - Verify message queue consumers are running
   - Check logs for processing errors

3. **Database connection errors**
   - Verify PostgreSQL is running
   - Check database credentials
   - Run migrations: `alembic upgrade head`

## 📚 Additional Resources

- [WhatsApp Business Platform Documentation](https://developers.facebook.com/docs/whatsapp)
- [Architecture Decision Records](docs/adr/)
- [API Reference](docs/api/)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

Built with love using:
- FastAPI for the web framework
- SQLAlchemy for database ORM
- OpenAI/Anthropic for LLM capabilities
- Redis for message queuing
- And many other amazing open-source projects

---

**Note**: This is a powerful system. Use it responsibly and always prioritize genuine human connection over automation.