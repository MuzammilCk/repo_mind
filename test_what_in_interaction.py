"""
Debug what's actually in the interaction object
"""
from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

print("Creating interaction...")
test_interaction = client.interactions.create(
    model="gemini-3-flash-preview",
    input="Respond with 'OK'",
    generation_config={
        "temperature": 0.0,
        "max_output_tokens": 10
    }
)

print("\nInteraction object type:", type(test_interaction))
print("\nAll attributes:")
for attr in dir(test_interaction):
    if not attr.startswith('_'):
        try:
            value = getattr(test_interaction, attr)
            if not callable(value):
                print(f"  {attr}: {value}")
        except:
            pass

print("\n" + "="*60)
print("Checking outputs specifically...")
print(f"outputs = {test_interaction.outputs}")
print(f"outputs type = {type(test_interaction.outputs)}")

if test_interaction.outputs is not None:
    print(f"outputs length = {len(test_interaction.outputs)}")
else:
    print("outputs is None!")
