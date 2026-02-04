"""
Test which generation_config causes empty outputs
"""
from google import genai

api_key = "AIzaSyDSovChcwcjkGeWgsRp4YfEOOSfvjs1dr8"
client = genai.Client(api_key=api_key)

model = "gemini-3-flash-preview"
input_text = "Respond with 'OK'"

configs = [
    {"name": "No config", "config": None},
    {"name": "temp=0.0, max=10", "config": {"temperature": 0.0, "max_output_tokens": 10}},
    {"name": "temp=0.0, max=50", "config": {"temperature": 0.0, "max_output_tokens": 50}},
    {"name": "temp=0.5, max=10", "config": {"temperature": 0.5, "max_output_tokens": 10}},
    {"name": "Only max=50", "config": {"max_output_tokens": 50}},
]

print("="*60)
print("Testing which config works")
print("="*60)

for test in configs:
    print(f"\nTest: {test['name']}")
    
    try:
        kwargs = {"model": model, "input": input_text}
        if test['config']:
            kwargs['generation_config'] = test['config']
        
        interaction = client.interactions.create(**kwargs)
        
        if interaction.outputs:
            text_out = [o for o in interaction.outputs if o.type == 'text']
            if text_out:
                print(f"  ✅ Got output: {text_out[0].text}")
            else:
                print(f"  ⚠️  Outputs exist but no text: {[o.type for o in interaction.outputs]}")
        else:
            print(f"  ❌ No outputs (thought tokens: {interaction.usage.total_thought_tokens})")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:60]}")

print("\n" + "="*60)
