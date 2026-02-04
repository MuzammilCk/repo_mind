"""
FixBot Day 1 Test - Verify Issue Fetching + Patch Generation
Tests the core workflow without PR creation
"""
import sys
import os
sys.path.append(os.getcwd())

from services.github_service import GitHubService
from services.code_patcher import CodePatcher
from services.gemini_service import GeminiService

def test_day1_milestone():
    print("=" * 60)
    print("🤖 FIXBOT DAY 1 MILESTONE TEST")
    print("=" * 60)
    
    # Test with a real, simple issue
    # Using a small repo with clear issues
    TEST_REPO = "https://github.com/octocat/Hello-World"
    TEST_ISSUE = 1  # Adjust based on actual issue
    
    print(f"\n📋 Test Configuration:")
    print(f"   Repo: {TEST_REPO}")
    print(f"   Issue: #{TEST_ISSUE}")
    
    # Step 1: Test GitHub Service
    print(f"\n{'='*60}")
    print("STEP 1: Testing GitHub Service")
    print(f"{'='*60}")
    
    github = GitHubService()
    
    print("   Fetching issue...")
    issue_data = github.fetch_issue(TEST_REPO, TEST_ISSUE)
    
    if "error" in issue_data:
        print(f"   ❌ FAILED: {issue_data['error']}")
        print("\n💡 TIP: This might be because:")
        print("   1. Issue #1 doesn't exist in Hello-World")
        print("   2. GitHub API rate limit (need GITHUB_TOKEN)")
        print("   3. Network issue")
        return False
    
    print(f"   ✅ Issue fetched successfully!")
    print(f"   Title: {issue_data['title']}")
    print(f"   Language: {issue_data.get('language', 'Unknown')}")
    print(f"   Files mentioned: {issue_data.get('files_mentioned', [])}")
    
    # Step 2: Test Repo Cloning
    print(f"\n{'='*60}")
    print("STEP 2: Testing Repo Cloning")
    print(f"{'='*60}")
    
    print("   Cloning repository...")
    clone_result = github.clone_repo(TEST_REPO)
    
    if not clone_result.get("success"):
        print(f"   ❌ FAILED: {clone_result.get('error')}")
        return False
    
    repo_path = clone_result["path"]
    repo_files = clone_result["files"]
    
    print(f"   ✅ Repo cloned successfully!")
    print(f"   Path: {repo_path}")
    print(f"   Files: {len(repo_files)} files found")
    print(f"   Sample files: {repo_files[:5]}")
    
    # Step 3: Test Code Patcher
    print(f"\n{'='*60}")
    print("STEP 3: Testing Code Patcher (Adaptive Planning)")
    print(f"{'='*60}")
    
    gemini = GeminiService()
    patcher = CodePatcher(gemini)
    
    print("   Generating patch using Gemini...")
    print("   (This will use your adaptive macro-planning engine)")
    
    try:
        patch_result = patcher.generate_patch(issue_data, repo_path, repo_files)
        
        if not patch_result.get("success"):
            print(f"   ⚠️  Patch generation had issues: {patch_result.get('error')}")
            print("   This is expected for Day 1 - we're still building the parser")
        else:
            print(f"   ✅ Patch generated!")
            print(f"   Patches: {len(patch_result['patches'])} file(s) to modify")
            print(f"   Reasoning: {patch_result.get('reasoning', '')[:200]}...")
        
    except Exception as e:
        print(f"   ⚠️  Exception during patch generation: {str(e)}")
        print("   This is OK for Day 1 - we're iterating on the implementation")
    
    # Cleanup
    print(f"\n{'='*60}")
    print("CLEANUP")
    print(f"{'='*60}")
    github.cleanup_repo(repo_path)
    print("   ✅ Temporary files cleaned up")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 DAY 1 MILESTONE SUMMARY")
    print(f"{'='*60}")
    print("✅ GitHub Service: WORKING")
    print("✅ Repo Cloning: WORKING")
    print("⚠️  Code Patcher: IN PROGRESS (expected)")
    print("\n🎯 NEXT STEPS (Day 2):")
    print("   1. Improve patch extraction from Gemini response")
    print("   2. Add test runner integration")
    print("   3. Connect test failures to _replan() trigger")
    
    return True

if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("FIXBOT - Autonomous GitHub Issue Solver")
    print("Day 1 Milestone: Issue Fetching + Patch Generation")
    print("🚀" * 30 + "\n")
    
    success = test_day1_milestone()
    
    if success:
        print("\n✅ Day 1 milestone test completed!")
        print("Ready to move to Day 2: Test Runner Integration")
    else:
        print("\n❌ Day 1 test encountered issues")
        print("Check the error messages above and fix before proceeding")
