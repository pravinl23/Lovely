# Contact Manager App

A React Native Expo app to manage your WhatsApp contacts and select which person you're currently on a date with.

## Features

- **Contact List**: View all your WhatsApp contacts
- **Whitelist Management**: Toggle whitelist status for contacts
- **Star System**: Star one contact as your "active date" (only one can be starred at a time)
- **Profile Integration**: Automatically uses the correct knowledge graph for the starred contact
- **Real-time Updates**: Syncs with Supabase for persistent storage
- **Secure Configuration**: Uses environment variables to protect API keys

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

**IMPORTANT**: Never commit your API keys to version control!

1. Copy the `.env` file template:
```bash
cp .env.example .env  # if you have an example file
```

2. Edit the `.env` file with your actual credentials:
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_actual_supabase_anon_key_here

# OpenAI Configuration (if needed for future features)
OPENAI_API_KEY=your_openai_api_key_here
```

3. **Verify the `.env` file is in `.gitignore`** (it should be already)

### 3. Database Schema

Make sure your Supabase database has these tables:

#### `contacts` table:
```sql
CREATE TABLE contacts (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  phone_number TEXT UNIQUE NOT NULL,
  is_whitelisted BOOLEAN DEFAULT FALSE,
  knowledge_file TEXT DEFAULT 'default.json'
);
```

#### `app_settings` table:
```sql
CREATE TABLE app_settings (
  id INTEGER PRIMARY KEY DEFAULT 1,
  starred_contact_id INTEGER REFERENCES contacts(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4. Run the App

```bash
# For iOS
npm run ios

# For Android
npm run android

# For web
npm run web
```

## Security Features

### Environment Variables
- ✅ **API keys are loaded from `.env` file**
- ✅ **`.env` file is in `.gitignore`** - never committed to version control
- ✅ **Validation warnings** if environment variables are not configured
- ✅ **Graceful fallback** to demo data if credentials are missing

### Configuration Validation
The app will show a configuration error screen if:
- `.env` file is missing
- Supabase credentials are not set
- Environment variables contain placeholder values

## Usage

### Contact Management

1. **View Contacts**: The app displays all your WhatsApp contacts
2. **Whitelist**: Tap the "Whitelist" button to add/remove contacts from whitelist
3. **Star Contact**: Tap the "Star" button to set someone as your active date
4. **Active Date**: Only one person can be starred at a time

### Profile Integration

The app automatically maps contact IDs to knowledge graph files:

- **647** → `bob.json`
- **416** → `isabella.json`
- **289** → `adam.json`

When you star a contact, the meta folder will automatically use their knowledge graph for AI responses.

## Testing Profile Switching

In the meta folder, you can test profile switching:

```bash
cd meta

# Set Bob as active
python set_starred_contact.py 647

# Set Isabella as active
python set_starred_contact.py 416

# Set Adam as active
python set_starred_contact.py 289

# Clear active contact
python set_starred_contact.py clear

# Show current active contact
python set_starred_contact.py show
```

## File Structure

```
contact-manager/
├── App.js                 # Main app component
├── config.js              # Configuration with env vars
├── babel.config.js        # Babel config for env vars
├── .env                   # Environment variables (not in git)
├── .gitignore            # Git ignore rules
├── package.json           # Dependencies
└── README.md             # This file

profiles/
├── bob.json              # Bob's knowledge graph
├── isabella.json         # Isabella's knowledge graph
└── adam.json             # Adam's knowledge graph

meta/
├── profile_manager.py    # Profile management system
├── assistant.py          # Updated AI assistant
├── main.py              # Main audio processing
└── set_starred_contact.py # Profile switching utility
```

## Features

### Contact Display
- Shows contact name, phone number, and knowledge file
- Visual indicators for whitelist and star status
- Clean, modern UI with cards and icons

### Whitelist System
- Toggle whitelist status with visual feedback
- Green checkmark for whitelisted contacts
- Updates stored in Supabase

### Star System
- Only one contact can be starred at a time
- Golden star indicator for active date
- Automatic profile switching in meta folder

### Error Handling
- Graceful fallback to hardcoded data if Supabase is unavailable
- User-friendly error messages
- Loading states and feedback
- Configuration validation

### Security
- Environment variables for API keys
- `.env` file excluded from version control
- Validation warnings for missing configuration
- Secure credential management

## Future Enhancements

- **Real-time Sync**: WebSocket connection for live updates
- **Profile Editor**: In-app profile editing capabilities
- **Analytics**: Conversation success metrics
- **Notifications**: Push notifications for new messages
- **Offline Mode**: Work without internet connection
- **Profile Import/Export**: Backup and restore profiles

## Troubleshooting

### App Won't Start
- Check `.env` file exists and has correct values
- Ensure all dependencies are installed
- Verify database schema is correct

### Configuration Error Screen
- Create `.env` file in the contact-manager directory
- Add your Supabase URL and anon key
- Restart the app

### Profile Not Switching
- Check `current_starred.json` file in meta folder
- Verify contact ID mapping is correct
- Restart the meta folder application

### Supabase Connection Issues
- Verify URL and API key in `.env` file
- Check network connectivity
- Ensure database tables exist

### Environment Variables Not Loading
- Check babel.config.js has react-native-dotenv plugin
- Restart the development server
- Clear Metro cache: `npx expo start --clear`

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use different API keys** for development and production
3. **Rotate API keys** regularly
4. **Monitor API usage** for unusual activity
5. **Use environment-specific configurations** 