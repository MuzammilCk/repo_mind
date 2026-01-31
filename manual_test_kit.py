import requests
import json
import hmac
import hashlib
import sys
import time
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
SECRET_KEY = "dev-secret-key-change-in-production-use-strong-random-key"  # Matches config.py default

def print_header(text):
    print(f"\n{'='*50}")
    print(f" {text}")
    print(f"{'='*50}\n")

def check_health():
    try:
        resp = requests.get(f"{API_URL}/health")
        if resp.status_code == 200:
            print("✅ API is Healthy")
            data = resp.json()
            print(f"   - Gemini Available: {data.get('gemini_available')}")
            print(f"   - Orchestrator: {data.get('services', {}).get('orchestrator')}")
            return True
        else:
            print(f"❌ API Unhealthy: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to API: {e}")
        return False

def ingest_repo():
    print_header("Step 1: Ingest Repository")
    repo_path = input("Enter local path to repo (or press Enter for this repo 'd:/projects/cli'): ").strip()
    if not repo_path:
        repo_path = "d:/projects/cli"
        
    repo_id = input("Enter a ID for this repo (e.g., 'cli-test'): ").strip() or "cli-test"
    
    payload = {
        "source": {
            "url": repo_path if repo_path.startswith("http") else None,
            "local_path": repo_path if not repo_path.startswith("http") else None
        },
        "repo_id": repo_id
    }
    
    print(f"Sending Ingest Request for {repo_id}...")
    resp = requests.post(f"{API_URL}/api/ingest", json=payload)
    
    if resp.status_code == 200:
        print("✅ Ingest Success!")
        print(json.dumps(resp.json(), indent=2))
        return repo_id
    else:
        print(f"❌ Ingest Failed: {resp.text}")
        return None

def run_deep_analysis(repo_id):
    print_header("Step 2: Deep Analysis (Plan & Execute)")
    
    if not repo_id:
        repo_id = input("Enter repo_id to analyze: ").strip()
        
    query = input("Enter your analysis query (e.g., 'Find security flaws in auth'): ").strip()
    if not query:
        query = "Identify potential security risks and architectural issues."
        
    # 1. Create Plan
    print("\n[1/3] Creating Analysis Plan...")
    plan_payload = {
        "repo_id": repo_id,
        "analysis_type": "deep",
        "custom_instructions": query
    }
    
    resp = requests.post(f"{API_URL}/api/orchestrate/plan", json=plan_payload)
    if resp.status_code != 200:
        print(f"❌ Plan Creation Failed: {resp.text}")
        return
        
    plan_data = resp.json()
    plan_id = plan_data["plan_id"]
    print(f"✅ Plan Created: {plan_id}")
    print(f"   Actions: {[a['action'] for a in plan_data['actions']]}")
    
    # 2. Approve Plan (HMAC Signature)
    print("\n[2/3] Approving Plan...")
    approved_by = "admin"
    
    # Calculate HMAC
    # Signature = HMAC(plan_json + approved_by, secret_key)
    # Note: We need the EXACT JSON that server uses. 
    # In a real app, the server gives us the payload to sign, or we sign the ID.
    # Our Orchestrator expects HMAC(plan_json_string + ":admin", key).
    # Since we can't easily reproduce the exact JSON string formatting of Python's json.dumps on the server side 
    # without risk of whitespace mismatch, the Orchestrator verification is strict.
    # However, meant for manual verification.
    
    # WAIT: The orchestrator's `_verify_signature` does `json.dumps(plan, sort_keys=True)`.
    # We can replicate that here.
    
    # We must use the plan data returned from the server, but ensure we don't modify it.
    plan_json_str = json.dumps(plan_data, sort_keys=True)
    message = f"{plan_json_str}:{approved_by}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"   Signature: {signature[:8]}...")
    
    # 3. Execute Plan
    print("\n[3/3] Executing Plan (This may take time)...")
    exec_payload = {
        "plan_id": plan_id,
        "approved_by": approved_by,
        "approval_signature": signature
    }
    
    start_time = time.time()
    resp = requests.post(f"{API_URL}/api/orchestrate/execute", json=exec_payload)
    duration = time.time() - start_time
    
    if resp.status_code == 200:
        print(f"✅ Execution Complete ({duration:.1f}s)!")
        result_data = resp.json()
        print("\n--- ANALYSIS RESULTS ---")
        
        # Extract Gemini Results
        results_list = result_data.get("results", {}).get("action_results", [])
        for action in results_list:
            if action["action"] == "gemini_analyze":
                print("\n👀 GEMINI FINDINGS:")
                analysis = action.get("result", {}).get("analysis", {})
                print(f"Summary: {analysis.get('summary')}")
                print("\nFindings:")
                for finding in analysis.get("findings", []):
                    print(f" - {finding}")
                print(f"\nConfidence: {analysis.get('confidence_score')}")
    else:
        print(f"❌ Execution Failed: {resp.text}")

def main():
    print_header("Repo Analyzer - Manual Test Kit")
    
    if not check_health():
        print("\n⚠️  Server not verified. Make sure 'uvicorn main:app' is running!")
        return

    while True:
        print("\nOptions:")
        print("1. Ingest Repository")
        print("2. Run Deep Analysis")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            ingest_repo()
        elif choice == "2":
            run_deep_analysis(None)
        elif choice == "3":
            print("Bye!")
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
