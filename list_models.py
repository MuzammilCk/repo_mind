from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

print("="*60)
print("AVAILABLE MODELS")
print("="*60)

try:
    models = list(client.models.list())
    print(f"\\nFound {len(models)} models:\\n")
    
    for m in models:
        print(f"  - {m.name}")
        
except Exception as e:
    print(f"Error: {e}")

print("\\n" + "="*60)
