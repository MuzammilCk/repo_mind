import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_keys_str = os.getenv("GEMINI_API_KEY", "")
api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

print(f"🔍 Found {len(api_keys)} keys in .env")

model = "gemini-3-flash-preview"

for i, key in enumerate(api_keys):
    masked = key[:6] + "..." + key[-4:]
    print(f"\n🔑 Key {i+1}: {masked}")
    try:
        client = genai.Client(api_key=key)
        resp = client.interactions.create(
            model=model,
            input="Ping",
            generation_config={"max_output_tokens": 5}
        )
        if resp.outputs:
            print("   ✅ SUCCESS")
        else:
            print("   ⚠️ Empty Response")
            
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
