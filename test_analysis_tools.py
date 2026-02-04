import sys
import os

# Add local directory to path
sys.path.append(os.getcwd())

from services.tool_executor import execute_tool, run_code_analysis

def test_analysis_tools():
    print(f"\n{('=' * 60)}")
    print("🚀 TESTING CODE ANALYSIS TOOLS")
    print(f"{('=' * 60)}\n")

    # Target file: services/gemini_service.py (it exists)
    target = "services/gemini_service.py"
    
    # 1. Test Radon (Complexity) - Might fail if not installed, but checking error handling
    print("1️⃣  Testing 'radon'...")
    result = execute_tool("run_code_analysis", {"target_path": target, "tool": "radon"})
    print(f"Result: {str(result)[:100]}...")
    if "radon not installed" in str(result):
        print("⚠️ Radon missing (Expected if not in env), but logic handled.")
    else:
        print("✅ Radon execution attempted.")

    # 2. Test Manual Line Count (Fallback for Tokei)
    print("\n2️⃣  Testing 'tokei' (Fallback)...")
    result = execute_tool("run_code_analysis", {"target_path": "services", "tool": "tokei"})
    print(f"Result: {result}")
    
    # 3. Test Invalid Tool
    print("\n3️⃣  Testing Invalid Tool...")
    result = execute_tool("run_code_analysis", {"target_path": target, "tool": "fake_tool"})
    print(f"Result: {result}")

if __name__ == "__main__":
    test_analysis_tools()
