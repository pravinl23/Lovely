# WhatsApp Rizz Bot

An AI-powered WhatsApp bot that responds with charisma and charm to help build connections.

## Features

- **AI-Powered Responses**: Uses GPT-4 to generate engaging, flirty responses
- **Whitelist Management**: Web dashboard to control which contacts get AI responses
- **Conversation Memory**: Remembers facts about contacts for personalized interactions
- **Safety Controls**: Rate limiting and content filtering

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL or Supabase
- Redis
- WhatsApp Business Account with Cloud API access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd whatsapp-automation
```

2. Set up environment:
```bash
cp .env.template .env
# Edit .env with your credentials
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the application:
```bash
python -m src.main
```

## Configuration

### Required Environment Variables

- `WHATSAPP_PHONE_NUMBER_ID`: Your WhatsApp phone number ID
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp Cloud API access token
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`: Webhook verification token
- `WHATSAPP_WEBHOOK_SECRET`: Webhook signature secret
- `DATABASE_URL`: PostgreSQL or Supabase connection string
- `OPENAI_API_KEY`: OpenAI API key for GPT-4

### WhatsApp Setup

1. Create a WhatsApp Business Account
2. Set up webhook URL: `https://yourdomain.com/webhook`
3. Subscribe to webhook fields: `messages`

## Usage

### Web Dashboard

Access the dashboard at `http://localhost:8000/dashboard` to:
- View all contacts
- Enable/disable AI for specific contacts
- Monitor conversation metrics

### How It Works

1. Receives WhatsApp messages via webhook
2. Checks if contact is whitelisted for AI responses
3. Generates contextual, charismatic responses using GPT-4
4. Sends response back through WhatsApp Cloud API

## API Endpoints

- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - Receive WhatsApp messages
- `GET /dashboard` - Web dashboard
- `GET /health` - Health check

## License

MIT License