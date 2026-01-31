import pytest
from services.codeql_service import CodeQLService
from models.responses import CodeQLFinding, SeverityEnum

def test_count_severities_correctness():
    """Test findings are counted correctly by severity"""
    findings = [
        CodeQLFinding(
            rule_id="1", severity=SeverityEnum.CRITICAL, message="msg",
            file_path="f", start_line=1, end_line=1
        ),
        CodeQLFinding(
            rule_id="2", severity=SeverityEnum.CRITICAL, message="msg",
            file_path="f", start_line=1, end_line=1
        ),
        CodeQLFinding(
            rule_id="3", severity=SeverityEnum.MEDIUM, message="msg",
            file_path="f", start_line=1, end_line=1
        ),
    ]
    
    service = CodeQLService()
    counts = service._count_severities(findings)
    
    assert counts["critical"] == 2
    assert counts["medium"] == 1
    assert counts["high"] == 0
    assert counts["low"] == 0

def test_response_invariant():
    """Test that manual counting matches total_findings"""
    service = CodeQLService()
    
    findings = [
        CodeQLFinding(
            rule_id="1", severity=SeverityEnum.HIGH, message="msg",
            file_path="f", start_line=1, end_line=1
        ),
        CodeQLFinding(
            rule_id="2", severity=SeverityEnum.LOW, message="msg",
            file_path="f", start_line=1, end_line=1
        )
    ]
    
    response = service._create_response("repo_123", "python", findings)
    
    # Check counts
    assert response.high_count == 1
    assert response.low_count == 1
    assert response.total_findings == 2
    
    # Verify Sum = Total (Invariant)
    count_sum = (
        response.critical_count + 
        response.high_count + 
        response.medium_count + 
        response.low_count
    )
    assert count_sum == response.total_findings

def test_empty_findings():
    """Test aggregation with empty finding list"""
    service = CodeQLService()
    response = service._create_response("repo_123", "python", [])
    
    assert response.total_findings == 0
    assert response.critical_count == 0
    assert response.high_count == 0
    assert response.medium_count == 0
    assert response.low_count == 0
