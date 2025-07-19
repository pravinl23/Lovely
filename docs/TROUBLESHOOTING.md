# Troubleshooting Guide

## 🚨 Authentication Errors

### WhatsApp Access Token Expired (Error 401)

**Error Message:**
```
Error validating access token: Session has expired on [date]. The current time is [date].
```

**Solution:**
1. Go to [Meta for Developers](https://developers.facebook.com/apps/)
2. Select your WhatsApp Business app
3. Navigate to **WhatsApp > API Setup**
4. Click **Generate Access Token** 
5. Copy the new temporary token
6. Update `WHATSAPP_ACCESS_TOKEN` in your `.env` file
7. Restart the application

**Notes:**
- Temporary tokens expire after 24 hours
- For production, set up System User tokens (permanent)
- See [WhatsApp Business Platform docs](https://developers.facebook.com/docs/whatsapp/business-management-api/get-started#system-user-access-tokens) for permanent tokens

### SendGrid API Key Invalid (Error 401)

**Error Message:**
```
Client error '401 Unauthorized' for url 'https://api.sendgrid.com/v3/mail/send'
```

**Solution:**
1. Go to [SendGrid API Keys](https://app.sendgrid.com/settings/api_keys)
2. Click **Create API Key**
3. Give it a name (e.g., "WhatsApp Automation")
4. Select **Restricted Access** 
5. Under **Mail Send**, select **Full Access**
6. Click **Create & View**
7. Copy the API key (starts with `SG.`)
8. Update `SENDGRID_API_KEY` in your `.env` file
9. Restart the application

## 🔧 Setup Issues

### Missing .env File

**Error:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
```

**Solution:**
1. Copy the template: `cp env-template.txt .env`
2. Generate secure keys: `python scripts/generate_keys.py`
3. Fill in your API credentials (see sections above)
4. Update database and other settings as needed

### Database Connection Issues

**Error:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**Solution:**

#### Option 1: Using Docker Compose (Recommended)
```bash
docker-compose up -d db redis
docker-compose run --rm app alembic upgrade head
```

#### Option 2: Local PostgreSQL
1. Install PostgreSQL 15+
2. Create database: `createdb whatsapp_automation`
3. Update `DATABASE_URL` in `.env`
4. Run migrations: `alembic upgrade head`

### Redis Connection Issues

**Error:**
```
redis.exceptions.ConnectionError: Error 61 connecting to localhost:6379. Connection refused.
```

**Solution:**

#### Option 1: Using Docker Compose
```bash
docker-compose up -d redis
```

#### Option 2: Local Redis
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

## 🔑 Security Configuration

### Generate Secure Keys

Run the key generator:
```bash
python scripts/generate_keys.py
```

This generates:
- `JWT_SECRET_KEY`: For authentication tokens
- `ENCRYPTION_KEY`: For encrypting sensitive data (exactly 32 bytes)
- `WHATSAPP_WEBHOOK_SECRET`: For webhook signature verification

### Environment Variables Checklist

**Required:**
- [ ] `WHATSAPP_PHONE_NUMBER_ID`
- [ ] `WHATSAPP_ACCESS_TOKEN` (fresh, not expired)
- [ ] `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
- [ ] `WHATSAPP_WEBHOOK_SECRET`
- [ ] `DATABASE_URL`
- [ ] `JWT_SECRET_KEY`
- [ ] `ENCRYPTION_KEY`

**Optional but Recommended:**
- [ ] `SENDGRID_API_KEY` (for email notifications)
- [ ] `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (for AI features)
- [ ] `WEBHOOK_URL` (your public domain)

## 🌐 Webhook Setup

### Webhook Not Receiving Messages

1. **Verify webhook URL is publicly accessible:**
   ```bash
   curl -X GET "https://yourdomain.com/webhook?hub.mode=subscribe&hub.verify_token=your_token&hub.challenge=test"
   ```

2. **Check webhook configuration in Meta:**
   - Go to WhatsApp > Configuration
   - Webhook URL: `https://yourdomain.com/webhook`
   - Verify token matches `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
   - Subscribe to: `messages`, `message_status`

3. **For local development with ngrok:**
   ```bash
   # Install ngrok
   ngrok http 8000
   
   # Use the https URL as your webhook URL
   # Example: https://abc123.ngrok.io/webhook
   ```

### Webhook Signature Verification Failed

**Error:**
```
Invalid webhook signature
```

**Solution:**
1. Verify `WHATSAPP_WEBHOOK_SECRET` matches the value in Meta console
2. Check that webhook secret is being used for signature generation
3. Ensure the secret doesn't have extra spaces or characters

## 🐛 Common Application Errors

### Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
Run from the project root:
```bash
python -m src.main
```

### Permission Errors

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Fix file permissions
chmod +x scripts/*.sh
chmod +x scripts/*.py

# Or use python directly
python scripts/generate_keys.py
```

### Port Already in Use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn src.main:app --port 8001
```

## 📞 Getting Help

If you're still having issues:

1. **Check the logs** for specific error messages
2. **Verify environment variables** are set correctly
3. **Test API credentials** manually:
   - WhatsApp: Try sending a test message via Graph API Explorer
   - SendGrid: Test with their web interface
4. **Review the error handling** in the application logs - they now provide specific guidance

## 🔄 Token Refresh Automation (Advanced)

For production deployments, consider:

1. **WhatsApp System User Tokens**: Never expire, more suitable for production
2. **Token refresh monitoring**: Set up alerts before token expiration  
3. **Graceful degradation**: Handle token expiration without crashing
4. **Health checks**: Monitor API connectivity

The improved error handling in this application now provides clear guidance when tokens expire, making it easier to maintain. 