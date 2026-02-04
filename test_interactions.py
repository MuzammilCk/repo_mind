"""
Test if Interactions API works with available models
"""
from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

# Test models for Interactions API
test_models = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]

print("="*60)
print("TESTING INTERACTIONS API")
print("="*60)

for model_name in test_models:
    print(f"\nTesting: {model_name}")
    try:
        interaction = client.interactions.create(
            model=model_name,
            input="Say 'OK'",
            generation_config={"max_output_tokens": 10}
        )
        response = interaction.outputs[-1].text if interaction.outputs else "No output"
        print(f"  ✅ WORKS - Response: {response}")
        print(f"     Interaction ID: {interaction.id}")
        
    except Exception as e:
        error_str = str(e)
        if "404" in error_str or "not found" in error_str.lower():
            print(f"  ❌ NOT AVAILABLE for Interactions API")
        elif "not supported" in error_str.lower():
            print(f"  ⚠️  Exists but doesn't support Interactions")
        else:
            print(f"  ❌ ERROR: {error_str[:80]}")

print("\n" + "="*60)
