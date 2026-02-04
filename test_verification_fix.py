"""
Test exact fix needed for gemini_service.py verification
"""
from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

print("Testing verification logic...")
print("="*60)

# Simulate what gemini_service.py does
test_interaction = client.interactions.create(
    model="gemini-3-flash-preview",
    input="Respond with 'OK'",
    generation_config={
        "temperature": 0.0,
        "max_output_tokens": 10
    }
)

print(f"Outputs count: {len(test_interaction.outputs)}")

# Current approach (FAILS)
print("\n1. Current approach: outputs[-1].text")
try:
    response_text = test_interaction.outputs[-1].text
    print(f"   ✅ Works: {response_text}")
except AttributeError as e:
    print(f"   ❌ AttributeError: {e}")

# Proposed fix: filter for type='text'
print("\n2. Proposed fix: filter for type='text'")
try:
    text_outputs = [o for o in test_interaction.outputs if hasattr(o, 'type') and o.type == 'text']
    if text_outputs and hasattr(text_outputs[0], 'text'):
        response_text = text_outputs[0].text
        print(f"   ✅ Works: {response_text}")
    else:
        print(f"   ❌ No text output found")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Simpler fix: just check attribute exists
print("\n3. Simpler fix: check hasattr before access")
try:
    last_output = test_interaction.outputs[-1]
    if hasattr(last_output, 'text'):
        response_text = last_output.text
        print(f"   ✅ Works: {response_text}")
    else:
        print(f"   ❌ No text attribute")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("="*60)
