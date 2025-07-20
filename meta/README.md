# 🎯 AI Assistant with Knowledge Graphs

Your personal AI wingman that remembers everything about the people you talk to - both in person and on WhatsApp.

## 🚀 Features

- **Always Listening**: 10-second rolling audio buffer via Meta Ray-Ban glasses
- **Dynamic Profiles**: Individual knowledge graphs for each person
- **AI-Powered Insights**: Automatically extracts interests, personality traits, and facts
- **WhatsApp Integration**: Updates knowledge graphs from text conversations
- **Voice Conversations**: Records and learns from in-person conversations
- **Smart Context**: Uses accumulated knowledge to generate better responses

## 📁 File Structure

```
meta/
├── knowledge/                    # Knowledge graph profiles
│   ├── anna_knowledge.json
│   ├── lucy_knowledge.json
│   └── ...
├── knowledge_manager.py         # Core knowledge management system
├── assistant.py                 # AI assistant with profile support
├── main.py                      # Main voice conversation app
├── whatsapp_integration.py      # WhatsApp automation bridge
├── view_profiles.py             # Profile viewer utility
├── live_buffer.py               # Audio buffer system
├── mic_to_text.py               # Speech-to-text (Whisper)
└── speak.py                     # Text-to-speech
```

## 🎮 How to Use

### 1. Start Voice Conversations
```bash
cd meta
python main.py
```

The app will:
- Start listening through your microphone
- Let you select or create a profile for the person you're talking to
- Save the last 10 seconds when you press Enter
- Generate contextual responses using the person's knowledge graph

### 2. View Knowledge Graphs
```bash
python view_profiles.py
```

View all profiles and their accumulated knowledge:
- Interests and personality traits
- Facts learned from conversations
- Recent topics discussed
- Conversation history

### 3. WhatsApp Integration
Import the integration in your WhatsApp automation:

```python
from whatsapp_integration import update_knowledge_from_whatsapp, get_contact_knowledge_context

# When receiving a WhatsApp message
update_knowledge_from_whatsapp("Anna", "I love hiking and just got back from Portugal!")

# When generating a WhatsApp response
context = get_contact_knowledge_context("Anna")
# Use context in your GPT prompt
```

## 🧠 Knowledge Graph Structure

Each profile contains:
- **Basic Info**: Name, creation date, relationship stage
- **Interests**: Hobbies, passions, activities
- **Personality**: Traits, communication style
- **Facts**: Specific information learned about the person
- **Topics**: Recent conversation subjects
- **History**: WhatsApp messages and voice conversations
- **Preferences**: Tone, topics, communication style

## 🔄 How It Learns

### From Voice Conversations:
1. You talk to someone in person
2. Press Enter to capture last 10 seconds
3. AI transcribes the conversation
4. AI extracts insights and updates the knowledge graph
5. AI generates contextual response

### From WhatsApp:
1. WhatsApp message received
2. Message added to profile history
3. AI extracts insights from the message
4. Knowledge graph updated with new information

## 🛠️ Technical Details

- **Audio Buffer**: 10-second rolling buffer using sounddevice
- **Speech Recognition**: OpenAI Whisper for transcription
- **AI Responses**: GPT-4o for contextual replies
- **Knowledge Extraction**: GPT-4o-mini for insight extraction
- **Storage**: Local JSON files for portability
- **Integration**: Simple function calls for WhatsApp automation

## 🎯 Next Steps

1. **React Native App**: Profile selection interface
2. **Enhanced WhatsApp Integration**: Automatic fact extraction
3. **Analytics**: Conversation success metrics
4. **Multi-modal**: Image and voice message support

## 💡 Tips

- Create profiles before conversations for better context
- Use the profile viewer to understand what the AI has learned
- The system gets smarter with each conversation
- Knowledge graphs are portable - backup the `knowledge/` folder 