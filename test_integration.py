"""
Quick Test Script - Gemini Interactions API Integration
Tests the fixed orchestrator with real Gemini API
"""

import requests
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if server is running"""
    print("\\n1️⃣ Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Server is running: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Server not running: {e}")
        print("\\nStart server with: uvicorn main:app --reload")
        return False

def test_gemini_status():
    """Test Gemini API connection"""
    print("\\n2️⃣ Testing Gemini API status...")
    try:
        response = requests.get(f"{BASE_URL}/health/gemini")
        data = response.json()
        print(f"   Status: {data}")
        
        if not data.get("available"):
            print("\\n❌ Gemini not available!")
            print("   Check your GEMINI_API_KEY in .env file")
            return False
        
        print("✅ Gemini API is ready!")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_ingest_repo():
    """Ingest a test repository"""
    print("\\n3️⃣ Ingesting test repository...")
    
    # Use current repo as test case
    current_dir = str(Path(__file__).parent.absolute())
    
    payload = {
        "source": {
            "local_path": current_dir
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ingest", json=payload)
        data = response.json()
        
        if response.status_code == 200:
            print(f"✅ Repository ingested!")
            print(f"   Repo ID: {data['repo_id']}")
            return data['repo_id']
        else:
            print(f"❌ Ingest failed: {data}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_orchestrator_plan(repo_id):
    """Test orchestrator plan creation (gemini_think)"""
    print("\\n4️⃣ Testing Orchestrator Plan Creation...")
    
    payload = {
        "repo_id": repo_id,
        "analysis_type": "deep",
        "instructions": "Find potential security issues in this codebase"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/orchestrate/plan", json=payload)
        data = response.json()
        
        if response.status_code == 200:
            print("✅ Plan created successfully!")
            print(f"   Plan ID: {data['plan_id']}")
            print(f"   Actions: {len(data['plan']['actions'])} steps")
            print(f"   Interaction ID: {data['plan'].get('interaction_id', 'N/A')}")
            
            # Show first action
            if data['plan']['actions']:
                first_action = data['plan']['actions'][0]
                print(f"\\n   First action: {first_action.get('type', 'unknown')}")
            
            return data
        else:
            print(f"❌ Plan creation failed: {data}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_continue_conversation(interaction_id):
    """Test stateful conversation with previous_interaction_id"""
    print("\\n5️⃣ Testing Stateful Conversation...")
    
    if not interaction_id:
        print("⚠️  No interaction_id, skipping")
        return
    
    # This would be a follow-up endpoint (not implemented yet)
    print(f"   Previous interaction: {interaction_id}")
    print("   ℹ️  Follow-up conversation endpoint not yet implemented")
    print("   (This would use Gemini's continue_conversation method)")

def main():
    print("="*60)
    print("🧪 GEMINI INTERACTIONS API - INTEGRATION TEST")
    print("="*60)
    
    # Step 1: Health check
    if not test_health():
        return
    
    # Step 2: Gemini status
    if not test_gemini_status():
        return
    
    # Step 3: Ingest repository
    repo_id = test_ingest_repo()
    if not repo_id:
        print("\\n⚠️  Skipping orchestrator tests (no repo)")
        return
    
    # Step 4: Test plan creation
    plan_data = test_orchestrator_plan(repo_id)
    
    # Step 5: Test stateful conversation
    if plan_data and plan_data['plan'].get('interaction_id'):
        test_continue_conversation(plan_data['plan']['interaction_id'])
    
    print("\\n" + "="*60)
    print("✅ INTEGRATION TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Test interrupted by user")
        sys.exit(0)
