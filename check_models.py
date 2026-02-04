"""
Check what models are available to your API key
"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

print("="*60)
print("CHECKING AVAILABLE MODELS")
print("="*60)

try:
    # List all models
    models = client.models.list()
    
    print("\n✅ Models available to your API key:\n")
    
    for model in models:
        # Check if it supports interactions
        supports_interactions = hasattr(model, 'supported_generation_methods') and \
                                'generateContent' in getattr(model, 'supported_generation_methods', [])
        
        print(f"  - {model.name}")
        if hasattr(model, 'display_name'):
            print(f"    Display: {model.display_name}")
        if hasattr(model, 'description'):
            desc = model.description[:80] + "..." if len(model.description) > 80 else model.description
            print(f"    Description: {desc}")
        print()
    
except Exception as e:
    print(f"\n❌ Error listing models: {e}\n")
    print("Trying simple test with common models...")
    
    # Test specific models
    test_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro", 
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-3-flash-preview"
    ]
    
    for model_name in test_models:
        try:
            print(f"\nTesting {model_name}...")
            interaction = client.interactions.create(
                model=model_name,
                input="Hi",
                generation_config={"max_output_tokens": 5}
            )
            print(f"  ✅ {model_name} WORKS")
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower() or "404" in error_msg:
                print(f"  ❌ {model_name} NOT AVAILABLE")
            elif "not supported" in error_msg.lower():
                print(f"  ⚠️  {model_name} exists but doesn't support Interactions API")
            else:
                print(f"  ❌ {model_name} error: {error_msg[:60]}")

print("\n" + "="*60)
