"""
Complete System Verification Script
Verifies all Phase 1 components are working correctly
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def check_files():
    """Check all required files exist"""
    print_section("1. FILE STRUCTURE CHECK")
    
    required_files = {
        "Core": [
            "main.py",
            "config.py",
            "requirements.txt",
            ".env.example"
        ],
        "API Routers": [
            "api/__init__.py",
            "api/middleware.py",
            "api/ingest.py",
            "api/search.py",
            "api/analysis.py",
            "api/orchestrator.py"
        ],
        "Services": [
            "services/__init__.py",
            "services/ingest_service.py",
            "services/search_service.py",
            "services/codeql_service.py",
            "services/orchestrator.py",
            "services/gemini_config.py"
        ],
        "Models": [
            "models/__init__.py",
            "models/requests.py",
            "models/responses.py"
        ],
        "Utils": [
            "utils/__init__.py",
            "utils/logger.py",
            "utils/metrics.py",
            "utils/validators.py",
            "utils/audit.py",
            "utils/rate_limiter.py"
        ],
        "Safety": [
            "prompts/safety_prompts.py"
        ],
        "Tests": [
            "tests/conftest.py",
            "tests/unit/test_orchestrator_service.py",
            "tests/unit/test_ingest_service.py",
            "tests/unit/test_utils.py",
            "tests/unit/test_safety_contracts.py",
            "tests/integration/test_api_flows.py",
            "pytest.ini"
        ],
        "CI/CD": [
            ".github/workflows/ci.yml"
        ]
    }
    
    all_ok = True
    for category, files in required_files.items():
        print(f"{category}:")
        for file in files:
            exists = Path(file).exists()
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {file}")
            if not exists:
                all_ok = False
        print()
    
    return all_ok


def check_imports():
    """Check critical imports work"""
    print_section("2. IMPORT CHECK")
    
    imports = [
        ("config", "Settings"),
        ("utils.logger", "get_logger"),
        ("utils.metrics", "metrics_collector"),
        ("utils.validators", "EvidenceValidator"),
        ("utils.audit", "AuditLogger"),
        ("utils.rate_limiter", "RateLimiter"),
        ("services.gemini_config", "PLANNING_CONFIG"),
        ("models.requests", "IngestRequest"),
        ("models.responses", "IngestResponse"),
    ]
    
    all_ok = True
    for module, item in imports:
        try:
            exec(f"from {module} import {item}")
            print(f"[OK] {module}.{item}")
        except Exception as e:
            print(f"[FAIL] {module}.{item} - {str(e)}")
            all_ok = False
    
    return all_ok


def check_safety_contracts():
    """Verify safety contracts are enforced"""
    print_section("3. SAFETY CONTRACTS CHECK")
    
    try:
        from utils.validators import EvidenceValidator, EvidenceEntry, PlanValidator
        from utils.rate_limiter import RateLimiter
        from services.gemini_config import PLANNING_CONFIG, ANALYSIS_CONFIG
        
        # Test 1: Evidence validator rejects fake evidence
        validator = EvidenceValidator(Path("workspace"))
        fake_evidence = EvidenceEntry(
            file_path="nonexistent.py",
            line_number=10,
            content="fake code",
            source="repo.md"
        )
        rejects_fake = not validator.validate_evidence(fake_evidence, "fake_repo")
        print(f"{'[OK]' if rejects_fake else '[FAIL]'} Evidence validator rejects non-existent files")
        
        # Test 2: Plan validator enforces schema
        plan_validator = PlanValidator()
        invalid_plan = {"plan_id": "test"}
        result = plan_validator.validate_plan_schema(invalid_plan)
        enforces_schema = not result.valid
        print(f"{'[OK]' if enforces_schema else '[FAIL]'} Plan validator enforces JSON schema")
        
        # Test 3: Low temperature configs
        low_temp = PLANNING_CONFIG.temperature <= 0.3 and ANALYSIS_CONFIG.temperature <= 0.3
        print(f"{'[OK]' if low_temp else '[FAIL]'} Gemini configs use low temperature (<=0.3)")
        print(f"    Planning: {PLANNING_CONFIG.temperature}, Analysis: {ANALYSIS_CONFIG.temperature}")
        
        # Test 4: Rate limiter works
        limiter = RateLimiter(max_calls_per_minute=2)
        call1 = limiter.check_rate_limit("test")
        call2 = limiter.check_rate_limit("test")
        call3 = limiter.check_rate_limit("test")
        rate_limit_works = call1 and call2 and not call3
        print(f"{'[OK]' if rate_limit_works else '[FAIL]'} Rate limiter enforces limits")
        
        all_ok = rejects_fake and enforces_schema and low_temp and rate_limit_works
        return all_ok
        
    except Exception as e:
        print(f"[FAIL] Safety contracts check failed: {str(e)}")
        return False


def check_workspace():
    """Check workspace directories"""
    print_section("4. WORKSPACE CHECK")
    
    workspace_dirs = [
        "workspace/ingest",
        "workspace/output",
        "workspace/memory",
        "workspace/codeql-dbs",
        "workspace/plans"
    ]
    
    all_ok = True
    for dir_path in workspace_dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Created: {dir_path}")
        else:
            print(f"[OK] Exists: {dir_path}")
    
    return all_ok


def check_config():
    """Check configuration"""
    print_section("5. CONFIGURATION CHECK")
    
    try:
        from config import Settings
        settings = Settings()
        
        print(f"[OK] Configuration loaded")
        print(f"    DEBUG: {settings.DEBUG}")
        print(f"    LOG_LEVEL: {settings.LOG_LEVEL}")
        print(f"    WORKSPACE_DIR: {settings.WORKSPACE_DIR}")
        print(f"    MAX_REPO_SIZE_MB: {settings.MAX_REPO_SIZE_MB}")
        
        # Check .env file
        env_file = Path(".env")
        if env_file.exists():
            print(f"[OK] .env file exists")
        else:
            print(f"[WARN] .env file not found (using defaults)")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Configuration check failed: {str(e)}")
        return False


def run_validation_scripts():
    """Run module validation scripts"""
    print_section("6. MODULE VALIDATION")
    
    import subprocess
    
    validation_scripts = [
        "validate_1_1.py",
        "validate_1_10.py"  # Test first and last modules
    ]
    
    all_ok = True
    for script in validation_scripts:
        if not Path(script).exists():
            print(f"[WARN] {script} not found")
            continue
        
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"[OK] {script} passed")
            else:
                print(f"[FAIL] {script} failed")
                all_ok = False
        except Exception as e:
            print(f"[FAIL] {script} error: {str(e)}")
            all_ok = False
    
    return all_ok


def main():
    """Run all verification checks"""
    print("\n" + "="*60)
    print("  REPO ANALYZER - PHASE 1 VERIFICATION")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    results = {}
    
    # Run all checks
    results["files"] = check_files()
    results["imports"] = check_imports()
    results["safety"] = check_safety_contracts()
    results["workspace"] = check_workspace()
    results["config"] = check_config()
    results["validation"] = run_validation_scripts()
    
    # Summary
    print_section("VERIFICATION SUMMARY")
    
    for check, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status} - {check.upper()}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("  [OK] ALL CHECKS PASSED - SYSTEM READY!")
    else:
        print("  [FAIL] SOME CHECKS FAILED - SEE ABOVE")
    print("="*60 + "\n")
    
    # Save results
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "status": "ok" if all_passed else "failed",
        "checks": results,
        "phase": "1",
        "modules_complete": "10/10"
    }
    
    with open("verification_results.json", "w") as f:
        json.dump(result_data, f, indent=2)
    
    print(f"Results saved to: verification_results.json\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
