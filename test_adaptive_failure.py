import sys
import os
import time

# Add local directory to path
sys.path.append(os.getcwd())

from services.gemini_service import GeminiService

def test_adaptive_agent():
    print(f"\n{('=' * 60)}")
    print("🚀 TESTING ADAPTIVE RE-PLANNING AGENT")
    print(f"{('=' * 60)}\n")
    
    service = GeminiService()
    
    # Goal that is likely to fail initial search if we force it 
    # Or we can mock the failure. 
    # Let's try a query for something very obscure OR modify the tool executor to mock a fail?
    # Better: Use a query that returns 0 results on GitHub?
    # actually, 'search_github_repos' is using real GitHub API.
    # Searching for a random string that doesn't exist.
    
    random_str = "ghjkl_non_existent_library_12345_xyz"
    user_goal = f"Find the library named '{random_str}' and analyze it."
    
    print(f"🎯 Goal: {user_goal}")
    print("ℹ️  Expectation: Search should fail (0 results), Trigger Re-Plan, Try broader search.")
    
    result = service.marathon_agent(user_goal)
    
    print("\n📜 FINAL REPORT:")
    print("-" * 40)
    print(result.get("response", "No response"))
    print("-" * 40)
    
    # Check if "replan" happened
    logs = result.get("tool_calls", [])
    replanned = any(not t.get("success") for t in logs)
    
    if replanned or len(logs) > 3: # If logs grew because of inserted steps
        print("\n✅ ADAPTIVE BEHAVIOR DETECTED!")
    else:
        print("\n⚠️ No adaptive behavior matched (or initial search unexpectedly succeeded).")

if __name__ == "__main__":
    test_adaptive_agent()
