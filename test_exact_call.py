"""
Test EXACT same call as gemini_service.py uses
"""
from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

print("="*60)
print("Testing EXACT gemini_service.py config")
print("="*60)

# EXACT same call as gemini_service.py line 53-60
test_interaction = client.interactions.create(
    model="gemini-3-flash-preview",
    input="Respond with 'OK'",
    generation_config={
        "temperature": 0.0,
        "max_output_tokens": 10
    }
)

print(f"\nStatus: {test_interaction.status}")
print(f"Outputs: {test_interaction.outputs}")

if test_interaction.outputs:
    print(f"Output count: {len(test_interaction.outputs)}")
    
    # Find text output
    text_outputs = [o for o in test_interaction.outputs if o.type == 'text']
    print(f"Text outputs: {len(text_outputs)}")
    
    if text_outputs:
        print(f"Text: {text_outputs[0].text}")
        print("\n✅ FIX WORKS!")
    else:
        print("\n❌ No text output")
else:
    print("\n❌ No outputs at all")
    print(f"Usage: {test_interaction.usage}")

print("="*60)
