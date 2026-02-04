import sys
import os
import time
import json

# Add current dir to path
sys.path.append(os.getcwd())

from services.tool_executor import run_security_scan, check_scan_status

print("🧪 Testing Async Integration...")
print("Target: https://github.com/octocat/Hello-World")

# 1. Start Job
print("\n[Step 1] Starting background scan...")
start_result = run_security_scan("https://github.com/octocat/Hello-World", background=True)
print(json.dumps(start_result, indent=2))

job_id = start_result.get("job_id")
if not job_id:
    print("❌ Failed to start job")
    sys.exit(1)

# 2. Poll Status
print(f"\n[Step 2] Polling Job ID: {job_id}")
for i in range(5):
    status = check_scan_status(job_id)
    print(f"   Poll {i+1}: Status = {status.get('status')} | Message = {status.get('message') or status.get('error')}")
    
    if status.get("status") in ["completed", "failed", "error"]:
        print("\n✅ Job Finished!")
        print("Final Result:", json.dumps(status, indent=2))
        break
    
    time.sleep(2)
