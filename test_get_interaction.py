"""
Test if we need to GET the interaction to retrieve outputs
"""
from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

print("="*60)
print("TEST: Do we need to GET interaction for outputs?")
print("="*60)

# Create interaction
print("\n1. Creating interaction...")
interaction = client.interactions.create(
    model="gemini-3-flash-preview",
    input="Say 'Hello World'",
    generation_config={"max_output_tokens": 20}
)

print(f"   ID: {interaction.id}")
print(f"   Status: {interaction.status}")
print(f"   Outputs (direct): {interaction.outputs}")

# Fetch interaction
print("\n2. Fetching interaction by ID...")
fetched = client.interactions.get(interaction.id)

print(f"   Status: {fetched.status}")
print(f"   Outputs: {fetched.outputs}")

if fetched.outputs:
    print(f"   Output count: {len(fetched.outputs)}")
    for i, output in enumerate(fetched.outputs):
        print(f"   Output {i+1}: type={output.type}")
        if hasattr(output, 'text'):
            print(f"            text={output.text}")

print("\n" + "="*60)
