
import inspect
from google import genai
from config import settings

print(f"GenAI Version: {genai.__version__}")

try:
    client = genai.Client(api_key=settings.GEMINI_API_KEY or "dummy")
    print("\nClient created.")
    
    if hasattr(client, 'chats'):
        print("Attribute 'chats' found on client.")
        if hasattr(client.chats, 'create'):
            sig = inspect.signature(client.chats.create)
            print(f"\nSignature of client.chats.create:\n{sig}")
        else:
            print("Attribute 'create' NOT found on client.chats")

except Exception as e:
    print(f"Error: {e}")
