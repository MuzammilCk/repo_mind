"""
Test Marathon Agent - Gemini 3 Hackathon Demo
"""
import requests
import json

SERVER_URL = "http://localhost:8000"

print("="*60)
print("🏃 MARATHON AGENT TEST - Gemini 3 Hackathon")
print("="*60)

# Test goal
goal = (
        "Run a deep security scan on https://github.com/octocat/Hello-World to check for vulnerabilities. "
        "Use the run_security_scan tool."
    )
print(f"\n📝 Goal: {goal}\n")

try:
    response = requests.post(
        f"{SERVER_URL}/api/marathon/run",
        json={
            "goal": goal,
            "max_iterations": 10,
            "thinking_level": "high"
        },
        timeout=120  # 2 minutes max
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"\n✅ Status: {result.get('status')}")
        print(f"⏱️  Duration: {result.get('duration_seconds', 0):.1f}s")
        print(f"🔄 Iterations: {result.get('iterations')}")
        print(f"🔧 Tools called: {len(result.get('tool_calls', []))}")
        
        print(f"\n📊 Tool calls:")
        for i, tool_call in enumerate(result.get('tool_calls', []), 1):
            print(f"   {i}. {tool_call['function']} (iteration {tool_call['iteration']})")
            print(f"      Status: {tool_call['result'].get('status')}")
        
        print(f"\n🎯 Final Response:")
        print("="*60)
        print(result.get('response', 'No response'))
        print("="*60)
        
    else:
        print(f"\n❌ Error {response.status_code}: {response.text}")

except requests.exceptions.Timeout:
    print("\n⏰ Request timed out (agent may still be running)")
except Exception as e:
    print(f"\n❌ Error: {e}")
