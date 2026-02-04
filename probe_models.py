import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-3-flash-preview", # Baseline
    "gemini-2.5-flash-preview",
    "gemini-2.5-flash-lite-preview",
    "gemma-3-4b-it",
    "gemma-3-27b-it",
    "gemma-3-1b-it",
]

print(f"🔍 Probing models with Key: {api_key[:6]}...")

for model in models_to_test:
    print(f"\n🧪 Testing {model}...")
    try:
        response = client.interactions.create(
            model=model,
            input="Ping",
            generation_config={"max_output_tokens": 5}
        )
        if response.outputs:
            print(f"✅ SUPPORTED! Response: {response.outputs[0].text}")
        else:
            print("⚠️ Supported but empty response")
    except Exception as e:
        err = str(e)
        if "404" in err or "found" in err.lower():
            print("❌ Not Found / Invalid Name")
        elif "429" in err:
            print("⏳ Rate Limited")
        elif "not support" in err:
            print("🚫 Interaction API Not Supported")
        else:
            print(f"❌ Error: {err}")
