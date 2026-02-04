import sys
import os
import time

# Add local directory to path
sys.path.append(os.getcwd())

from services.gemini_service import GeminiService
from services.gemini_schemas import AnalysisPlanSchema

def print_header(title):
    print(f"\n{('=' * 60)}")
    print(f"🚀 {title}")
    print(f"{('=' * 60)}\n")

def test_macro_planning():
    print_header("TESTING MACRO-PLANNING AGENT")
    
    try:
        # 1. Initialize
        print("1️⃣  Initializing Gemini Service...")
        service = GeminiService()
        if not service.gemini_available:
            print("❌ Gemini Service failed to initialize (No valid keys?)")
            return

        # 2. Define Goal
        user_goal = "Find a python library for parsing PDF files and explain how to extract text from them."
        print(f"🎯 Use Case: '{user_goal}'")
        
        # 3. Run Agent
        print("\n2️⃣  Running Marathon Agent (Synchronous Mode)...")
        start_time = time.time()
        
        result = service.marathon_agent(user_goal)
        
        duration = time.time() - start_time
        
        # 4. Analyze Result
        print_header("TEST RESULTS")
        
        if result.get("status") == "completed":
            print(f"✅ Status: SUCCESS")
            print(f"⏱️  Total Duration: {duration:.2f}s")
            
            tool_calls = result.get("tool_calls", [])
            print(f"🛠️  Tools Executed Locally: {len(tool_calls)}")
            for i, tc in enumerate(tool_calls):
                print(f"   {i+1}. {tc['tool']}")
            
            print("\n📜 FINAL REPORT:")
            print("-" * 40)
            print(result.get("response"))
            print("-" * 40)
            
        else:
            print(f"❌ Status: FAILED")
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_macro_planning()
