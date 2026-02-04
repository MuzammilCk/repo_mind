import os
from dotenv import load_dotenv
import google.genai as genai
from config import settings

print("🔍 Debugging Gemini Connection...")

# 1. Check Env
load_dotenv()
env_key = os.getenv("GEMINI_API_KEY")
setting_key = settings.GEMINI_API_KEY

print(f"Env Key present: {bool(env_key)}")
print(f"Settings Key present: {bool(setting_key)}")
if setting_key:
    print(f"Key Prefix: {setting_key[:4]}...")

print(f"Model: {settings.GEMINI_MODEL}")

# 2. Try Connection
if not setting_key:
    print("❌ No API Key found!")
    exit(1)

try:
    client = genai.Client(api_key=setting_key)
    print("Connecting...")
    response = client.interactions.create(
        model=settings.GEMINI_MODEL,
        input="Ping",
        generation_config={"max_output_tokens": 10}
    )
    print("✅ Success!")
    print("Output:", response.outputs[0].text if response.outputs else "No output")
except Exception as e:
    print(f"❌ Connection Failed: {e}")
