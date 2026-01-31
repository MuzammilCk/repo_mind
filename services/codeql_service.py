"""
CodeQL Service - Static analysis using CodeQL with SARIF parsing
Implements database creation, analysis, and SARIF JSON parsing
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from config import settings
from models.requests import CodeQLScanRequest
from models.responses import CodeQLResponse, CodeQLFinding, SeverityEnum


# Constants for safety guardrails
DB_CREATE_TIMEOUT = 600  # 10 minutes for database creation
ANALYZE_TIMEOUT = 600  # 10 minutes for analysis
VERSION_CHECK_TIMEOUT = 10  # 10 seconds for version check

# Explicit SARIF severity mapping
SARIF_SEVERITY_MAP = {
    "error": SeverityEnum.CRITICAL,
    "warning": SeverityEnum.HIGH,
    "note": SeverityEnum.MEDIUM,
    "none": SeverityEnum.LOW
}


class CodeQLService:
    """Service for CodeQL static analysis"""
    
    def __init__(self):
        self.codeql_path = getattr(settings, 'CODEQL_PATH', 'codeql')
        self.db_dir = Path(settings.WORKSPACE_DIR) / "codeql_dbs"
        self.ingest_dir = Path(settings.INGEST_DIR)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify CodeQL installation on init
        self._verify_codeql()
    
    def _verify_codeql(self) -> None:
        """
        Verify CodeQL CLI is installed and accessible
        
        Raises:
            RuntimeError: If CodeQL is not found or not working
        """
        try:
            result = subprocess.run(
                [self.codeql_path, "version"],
                capture_output=True,
                text=True,
                timeout=VERSION_CHECK_TIMEOUT,
                shell=False  # CRITICAL: Never use shell=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    "CodeQL CLI not working properly. "
                    "Please reinstall CodeQL."
                )
                
        except FileNotFoundError:
            raise RuntimeError(
                "CodeQL CLI not found. Install from: "
                "https://github.com/github/codeql-cli-binaries/releases"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "CodeQL version check timeout. "
                "CodeQL may not be installed correctly."
            )
        except Exception as e:
            raise RuntimeError(
                f"CodeQL verification failed: {str(e)}"
            )
    
    def analyze_repository(
        self, 
        request: CodeQLScanRequest
    ) -> CodeQLResponse:
        """
        Run CodeQL analysis on a repository
        
        Args:
            request: CodeQLScanRequest with repo_id, language, query_suite
            
        Returns:
            CodeQLResponse with findings and severity counts
            
        Raises:
            FileNotFoundError: If repository source not found
            RuntimeError: If analysis fails
        """
        repo_source_dir = self.ingest_dir / request.repo_id / "source"
        
        if not repo_source_dir.exists():
            raise FileNotFoundError(
                f"Repository source not found: {request.repo_id}. "
                f"Please ingest the repository first."
            )
        
        db_name = f"{request.repo_id}-{request.language}-db"
        db_path = self.db_dir / db_name
        results_path = self.db_dir / f"{request.repo_id}-{request.language}.sarif"
        
        try:
            # Step 1: Create CodeQL database
            self._create_database(repo_source_dir, db_path, request.language)
            
            # Step 2: Run queries and generate SARIF
            self._run_queries(
                db_path, 
                request.language, 
                request.query_suite, 
                results_path
            )
            
            # Step 3: Parse SARIF results
            findings = self._parse_sarif(results_path)
            
            # Step 4: Count severity levels
            severity_counts = self._count_severities(findings)
            
            return CodeQLResponse(
                repo_id=request.repo_id,
                language=request.language,
                findings=findings,
                total_findings=len(findings),
                critical_count=severity_counts.get("critical", 0),
                high_count=severity_counts.get("high", 0),
                medium_count=severity_counts.get("medium", 0),
                low_count=severity_counts.get("low", 0)
            )
            
        except Exception as e:
            # Return sanitized error message (no stacktrace)
            raise RuntimeError(
                f"CodeQL analysis failed for {request.repo_id}: {str(e)}"
            )
    
    def _create_database(
        self, 
        source_dir: Path, 
        db_path: Path, 
        language: str
    ) -> None:
        """
        Create CodeQL database from source code
        
        Args:
            source_dir: Path to source code
            db_path: Path where database will be created
            language: Programming language (python, javascript, java, etc.)
            
        Raises:
            RuntimeError: If database creation fails
        """
        # Remove existing database if present
        if db_path.exists():
            shutil.rmtree(db_path)
        
        try:
            result = subprocess.run(
                [
                    self.codeql_path, "database", "create",
                    str(db_path),
                    f"--language={language}",
                    f"--source-root={source_dir}",
                    "--overwrite"
                ],
                capture_output=True,
                text=True,
                timeout=DB_CREATE_TIMEOUT,
                shell=False  # CRITICAL: Never use shell=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"CodeQL database creation failed for {language}. "
                    f"Ensure source code is valid."
                )
                
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"CodeQL database creation timeout exceeded ({DB_CREATE_TIMEOUT}s). "
                f"Repository may be too large."
            )
    
    def _run_queries(
        self, 
        db_path: Path, 
        language: str, 
        query_suite: str, 
        output_path: Path
    ) -> None:
        """
        Run CodeQL queries on the database
        
        Args:
            db_path: Path to CodeQL database
            language: Programming language
            query_suite: Query suite to run (e.g., 'security-extended')
            output_path: Path where SARIF results will be saved
            
        Raises:
            RuntimeError: If query execution fails
        """
        try:
            # Construct query suite path
            suite_path = f"{language}-{query_suite}.qls"
            
            result = subprocess.run(
                [
                    self.codeql_path, "database", "analyze",
                    str(db_path),
                    suite_path,
                    "--format=sarif-latest",  # CRITICAL: Always use SARIF JSON
                    f"--output={output_path}",
                    "--rerun"
                ],
                capture_output=True,
                text=True,
                timeout=ANALYZE_TIMEOUT,
                shell=False  # CRITICAL: Never use shell=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"CodeQL query execution failed. "
                    f"Query suite '{suite_path}' may not exist."
                )
                
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"CodeQL analysis timeout exceeded ({ANALYZE_TIMEOUT}s). "
                f"Repository may be too large or queries too complex."
            )
    
    def _parse_sarif(self, sarif_path: Path) -> List[CodeQLFinding]:
        """
        Parse SARIF format results into CodeQLFinding objects
        SARIF JSON parsing only - no text parsing
        
        Args:
            sarif_path: Path to SARIF JSON file
            
        Returns:
            List of CodeQLFinding objects
            
        Raises:
            RuntimeError: If SARIF parsing fails
        """
        try:
            with open(sarif_path, 'r', encoding='utf-8') as f:
                sarif_data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid SARIF JSON: {str(e)}")
        except FileNotFoundError:
            raise RuntimeError(f"SARIF file not found: {sarif_path}")
        
        findings = []
        
        # Iterate through runs
        for run in sarif_data.get("runs", []):
            # Iterate through results
            for result in run.get("results", []):
                # Extract rule ID
                rule_id = result.get("ruleId", "unknown")
                
                # Extract message
                message_obj = result.get("message", {})
                message = message_obj.get("text", "No description available")
                
                # Extract and map severity level
                sarif_level = result.get("level", "note")
                severity = self._map_severity(sarif_level)
                
                # Extract location information
                locations = result.get("locations", [])
                
                if not locations:
                    # Skip findings without location
                    continue
                
                for location in locations:
                    physical_location = location.get("physicalLocation", {})
                    artifact_location = physical_location.get("artifactLocation", {})
                    region = physical_location.get("region", {})
                    
                    # Extract file path (preserve exactly as in SARIF)
                    file_path = artifact_location.get("uri", "unknown")
                    
                    # Extract line numbers (preserve exactly as in SARIF)
                    start_line = region.get("startLine", 0)
                    end_line = region.get("endLine", start_line)
                    
                    # Get recommendation from rule help
                    recommendation = self._get_recommendation(rule_id, run)
                    
                    findings.append(CodeQLFinding(
                        rule_id=rule_id,
                        severity=severity,
                        message=message,
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        recommendation=recommendation
                    ))
        
        return findings
    
    def _map_severity(self, sarif_level: str) -> SeverityEnum:
        """
        Map SARIF severity level to our severity taxonomy
        Explicit mapping as per guardrails
        
        Args:
            sarif_level: SARIF level (error, warning, note, none)
            
        Returns:
            SeverityEnum value
        """
        return SARIF_SEVERITY_MAP.get(
            sarif_level.lower(), 
            SeverityEnum.MEDIUM  # Default to medium if unknown
        )
    
    def _get_recommendation(self, rule_id: str, run: Dict) -> Optional[str]:
        """
        Extract recommendation from rule metadata in SARIF
        
        Args:
            rule_id: CodeQL rule ID
            run: SARIF run object
            
        Returns:
            Recommendation text or None
        """
        tool = run.get("tool", {})
        driver = tool.get("driver", {})
        rules = driver.get("rules", [])
        
        for rule in rules:
            if rule.get("id") == rule_id:
                help_obj = rule.get("help", {})
                return help_obj.get("text", None)
        
        return None
    
    def _count_severities(self, findings: List[CodeQLFinding]) -> Dict[str, int]:
        """
        Count findings by severity level
        
        Args:
            findings: List of CodeQLFinding objects
            
        Returns:
            Dictionary with severity counts
        """
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for finding in findings:
            severity_str = finding.severity.value
            if severity_str in counts:
                counts[severity_str] += 1
        
        return counts
