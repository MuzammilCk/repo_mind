import pytest
import json
import tempfile
from pathlib import Path
from services.codeql_service import CodeQLService, SARIF_SEVERITY_MAP
from models.responses import SeverityEnum

SAMPLE_SARIF = {
    "runs": [{
        "tool": {
            "driver": {
                "name": "CodeQL",
                "rules": [{
                    "id": "py/sql-injection",
                    "shortDescription": {"text": "SQL injection vulnerability"},
                    "help": {"text": "Use parameterized queries instead"}
                }]
            }
        },
        "results": [{
            "ruleId": "py/sql-injection",
            "level": "error",
            "message": {"text": "Potential SQL injection"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": "src/db.py"},
                    "region": {"startLine": 45, "endLine": 47}
                }
            }]
        }]
    }]
}

def test_sarif_parsing():
    """Test SARIF parsing with fixture"""
    # Write fixture to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sarif', delete=False) as f:
        json.dump(SAMPLE_SARIF, f)
        sarif_path = Path(f.name)
    
    try:
        service = CodeQLService()
        # Mock availability to avoid init checks if they were stricter, 
        # but init only checks version which is fine if available. 
        # Actually init calls _verify_codeql which might fail if not installed.
        # But we are testing _parse_sarif which doesn't need CLI.
        # To be safe, we can mock _verify_codeql or just ignore it if it sets available=False.
        
        findings = service._parse_sarif(sarif_path)
        
        assert len(findings) == 1
        finding = findings[0]
        
        assert finding.rule_id == "py/sql-injection"
        assert finding.severity == SeverityEnum.CRITICAL  # error -> critical
        assert finding.file_path == "src/db.py"
        assert finding.start_line == 45
        assert "parameterized queries" in finding.recommendation
        
    finally:
        if sarif_path.exists():
            sarif_path.unlink()

def test_missing_locations_skipped():
    """Test that results without locations are skipped"""
    sarif_no_locations = {
        "runs": [{
            "tool": {"driver": {"rules": []}},
            "results": [{
                "ruleId": "test",
                "level": "warning",
                "message": {"text": "Test"},
                "locations": []  # No locations!
            }]
        }]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sarif', delete=False) as f:
        json.dump(sarif_no_locations, f)
        sarif_path = Path(f.name)
        
    try:
        service = CodeQLService()
        findings = service._parse_sarif(sarif_path)
        assert len(findings) == 0
        
    finally:
        if sarif_path.exists():
            sarif_path.unlink()

def test_unknown_severity_default():
    """Test defaulting unknown severity to medium"""
    sarif_unknown = {
        "runs": [{
            "tool": {"driver": {"rules": []}},
            "results": [{
                "ruleId": "test",
                "level": "critical-error-unknown",  # Unknown
                "message": {"text": "Test"},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": "test.py"},
                        "region": {"startLine": 1}
                    }
                }]
            }]
        }]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sarif', delete=False) as f:
        json.dump(sarif_unknown, f)
        sarif_path = Path(f.name)
        
    try:
        service = CodeQLService()
        findings = service._parse_sarif(sarif_path)
        assert len(findings) == 1
        assert findings[0].severity == SeverityEnum.MEDIUM
        
    finally:
        if sarif_path.exists():
            sarif_path.unlink()
