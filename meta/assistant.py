import openai
import json
import dotenv
import os

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY not found in environment variables")

# Set API key properly using the new config system
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Load girl profile
with open("girlprofile.json") as f:
    girl = json.load(f)

def build_prompt(transcript):
    facts = "\n- ".join(girl["fun_facts"])
    return f"""
You're an AI assistant helping me on a date with a girl named {girl['name']}.
She likes: {', '.join(girl['interests'])}
Fun facts:
- {facts}

She just said: "{transcript}"

What is a charming, flirty, or witty one-liner I can say in response?
"""

def get_reply(transcript):
    prompt = build_prompt(transcript)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )
    return response.choices[0].message.content
