"""
Check what's actually in the interaction response
"""
from google import genai
import json

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

model = "gemini-3-flash-preview"  # Use Gemini 3!

print("="*60)
print(f"TESTING: {model}")
print("="*60)

try:
    interaction = client.interactions.create(
        model=model,
        input="Say 'Hello World' and nothing else",
        generation_config={"max_output_tokens": 20}
    )
    
    print(f"\n✅ Interaction created!")
    print(f"ID: {interaction.id}")
    print(f"\nOutputs ({len(interaction.outputs)} total):")
    
    for i, output in enumerate(interaction.outputs):
        print(f"\n  Output {i+1}:")
        print(f"    Type: {output.type if hasattr(output, 'type') else 'unknown'}")
        
        # Check different possible attributes
        if hasattr(output, 'text'):
            print(f"    Text: {output.text}")
        if hasattr(output, 'content'):
            print(f"    Content: {output.content}")
        if hasattr(output, 'data'):
            print(f"    Data: {output.data[:100] if len(str(output.data)) > 100 else output.data}")
        
        # Print all attributes
        print(f"    All attributes: {dir(output)}")
    
    # Try to access text directly
    if interaction.outputs:
        last_output = interaction.outputs[-1]
        print(f"\n  Last output object: {last_output}")
        print(f"  Type: {type(last_output)}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
