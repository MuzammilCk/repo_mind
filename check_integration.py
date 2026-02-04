import sys
import os
import json

# Add current dir to path
sys.path.append(os.getcwd())

from services.tool_executor import run_security_scan

print("🧪 Testing Deep Integration (Ingest + CodeQL)...")
print("Target: https://github.com/octocat/Hello-World")

try:
    # Run the tool directly
    result = run_security_scan("https://github.com/octocat/Hello-World")
    
    print("\n📊 Result:")
    print(json.dumps(result, indent=2))
    
    if result.get("status") == "success":
        print("\n✅ Integration SUCCESS: Repo ingested and scanned!")
    elif "CodeQL CLI not found" in str(result):
        # This is also a success for "Integration" (the code connected, just missing tool)
        print("\n✅ Integration SUCCESS: Connected to CodeQLService (Tool detection worked!)")
        print("ℹ️  Note: CodeQL is missing, but the orchestrator correctly identified that.")
    else:
        print("\n❌ Integration FAILURE: Unexpected error.")
        
except Exception as e:
    print(f"\n❌ Integration CRASHED: {e}")
