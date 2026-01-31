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
# Explicit SARIF severity mapping
SARIF_SEVERITY_MAP = {
    "error": SeverityEnum.CRITICAL,
    "warning": SeverityEnum.HIGH,
    "note": SeverityEnum.MEDIUM,
    "none": SeverityEnum.LOW
}


class CodeQLService:
    """Service for CodeQL static analysis"""

    # Module 2.3: Whitelisted query suites
    ALLOWED_QUERY_SUITES = {
        "security-extended",
        "security-and-quality", 
        "security",
        "code-scanning"
    }

    def __init__(self):
        self.codeql_path = getattr(settings, 'CODEQL_PATH', 'codeql')
        self.db_dir = Path(settings.WORKSPACE_DIR) / "codeql_dbs"
        self.ingest_dir = Path(settings.INGEST_DIR)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Module 2.1: Verify CodeQL installation
        self.codeql_available = False
        self.codeql_version = None
        self._verify_codeql()
        
    def _validate_query_suite(self, query_suite: str) -> str:
        """
        Validate and normalize query suite name.
        
        Args:
            query_suite: Query suite identifier
            
        Returns:
            Validated query suite name
            
        Raises:
            ValueError: If query suite not in whitelist
        """
        if query_suite not in self.ALLOWED_QUERY_SUITES:
            raise ValueError(
                f"Invalid query suite: {query_suite}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_QUERY_SUITES))}"
            )
        
        return query_suite
    
    def _verify_codeql(self) -> None:
        """
        Verify CodeQL CLI is installed and accessible.
        Stores availability status without crashing if not found.
        """
        try:
            # Run codeql version command with timeout
            result = subprocess.run(
                [self.codeql_path, "version"],  # NO shell=True!
                capture_output=True,
                text=True,
                timeout=VERSION_CHECK_TIMEOUT
            )
            
            if result.returncode == 0:
                # Parse version from stdout
                # Expected format: "CodeQL command-line toolchain release 2.x.x"
                version_line = result.stdout.strip().split('\n')[0]
                self.codeql_version = version_line
                self.codeql_available = True
                print(f"✅ CodeQL CLI verified: {self.codeql_version}")
            else:
                self.codeql_available = False
                self.codeql_version = None
                print(f"⚠️  CodeQL CLI returned non-zero: {result.stderr}")
                
        except FileNotFoundError:
            # Binary not found at specified path
            error_msg = (
                f"CodeQL CLI not found at {self.codeql_path}. "
                f"Download from: https://github.com/github/codeql-cli-binaries"
            )
            print(f"⚠️  {error_msg}")
            self.codeql_available = False
            self.codeql_version = None
            
        except subprocess.TimeoutExpired:
            print(f"⚠️  CodeQL version check timed out")
            self.codeql_available = False
            self.codeql_version = None
            
        except Exception as e:
            print(f"⚠️  CodeQL verification failed: {str(e)}")
            self.codeql_available = False
            self.codeql_version = None

    def get_status(self) -> Dict[str, any]:
        """Get CodeQL service status for health checks"""
        return {
            "codeql_available": self.codeql_available,
            "codeql_version": self.codeql_version,
            "codeql_path": self.codeql_path if self.codeql_available else None
        }

    def _ensure_codeql_available(self):
        """
        Raise exception if CodeQL is not available.
        Use this at the start of any method that requires CodeQL.
        """
        if not self.codeql_available:
            raise RuntimeError(
                "CodeQL CLI is not available. "
                "Download from: https://github.com/github/codeql-cli-binaries"
            )
    
    def _validate_repo_id(self, repo_id: str) -> Path:
        """
        Validate repo_id format and return source directory path.
        
        Args:
            repo_id: Repository ID from Phase 1 ingest
            
        Returns:
            Path to repository source directory
            
        Raises:
            ValueError: If repo_id format is invalid
            FileNotFoundError: If repository not ingested
        """
        import re
        
        # Validate format: must be lowercase hex, 8 characters (from Phase 1 UUID)
        if not re.match(r'^[a-f0-9]{8}$', repo_id):
            raise ValueError(
                f"Invalid repo_id format: {repo_id}. "
                f"Must be 8-character lowercase hex (from Phase 1 ingest)"
            )
        
        # Check if repository was ingested
        repo_source_dir = self.ingest_dir / repo_id / "source"
        
        if not repo_source_dir.exists():
            raise FileNotFoundError(
                f"Repository {repo_id} not found. "
                f"Run ingest endpoint first (/api/ingest)."
            )
        
        return repo_source_dir
    def analyze_repository(self, request: CodeQLScanRequest) -> CodeQLResponse:
        """
        Complete CodeQL analysis pipeline.
        
        This is the main entry point that coordinates all modules:
        1. Validate repo_id (Module 2.2)
        2. Create database (Module 2.2)
        3. Run queries (Module 2.3)
        4. Parse SARIF (Module 2.4)
        5. Aggregate response (Module 2.5)
        
        Args:
            request: CodeQL scan request
            
        Returns:
            Complete CodeQL response with findings
            
        Raises:
            FileNotFoundError: Repository not ingested
            ValueError: Invalid parameters
            RuntimeError: CodeQL execution failed
            TimeoutError: Operation timed out
        """
        print(f"\n{'='*60}")
        print(f"🔍 Starting CodeQL Analysis")
        print(f"   Repo ID: {request.repo_id}")
        print(f"   Language: {request.language}")
        print(f"   Query Suite: {request.query_suite}")
        print(f"{'='*60}\n")
        
        # Module 2.1: Check availability
        self._ensure_codeql_available()
        
        # Module 2.2: Validate and locate repository
        repo_source_dir = self._validate_repo_id(request.repo_id)
        
        # Module 2.2: Set up database path
        db_name = f"{request.repo_id}-{request.language}-db"
        db_path = self.db_dir / db_name
        
        # Module 2.2: Create database
        db_metadata = self._create_database(
            repo_source_dir,
            db_path,
            request.language
        )
        
        # Module 2.3: Validate query suite
        validated_suite = self._validate_query_suite(request.query_suite)
        
        # Module 2.3: Run queries
        results_path = self.db_dir / f"{request.repo_id}-{request.language}.sarif"
        query_metadata = self._run_queries(
            db_path,
            request.language,
            validated_suite,
            results_path
        )
        
        # Module 2.4: Parse SARIF
        findings = self._parse_sarif(results_path)
        
        # Module 2.5: Create response
        response = self._create_response(
            request.repo_id,
            request.language,
            findings
        )
        
        print(f"\n{'='*60}")
        print(f"✅ CodeQL Analysis Complete")
        print(f"   Total Findings: {response.total_findings}")
        print(f"   Database: {db_metadata['duration_seconds']:.2f}s")
        print(f"   Queries: {query_metadata['duration_seconds']:.2f}s")
        print(f"{'='*60}\n")
        
        return response
    
    def _create_database(
        self, 
        source_dir: Path, 
        db_path: Path, 
        language: str
    ) -> Dict[str, any]:
        """
        Create CodeQL database from source code.
        
        Args:
            source_dir: Path to repository source
            db_path: Target path for database
            language: Programming language (e.g., "python", "javascript")
            
        Returns:
            Dict with creation metadata (success, duration, etc.)
            
        Raises:
            RuntimeError: If database creation fails
        """
        # Ensure CodeQL is available
        self._ensure_codeql_available()
        
        # Remove existing database if present
        if db_path.exists():
            print(f"🗑️  Removing existing database at {db_path}")
            shutil.rmtree(db_path)
        
        start_time = datetime.utcnow()
        
        try:
            # Build command as list (NO shell=True!)
            command = [
                self.codeql_path,
                "database",
                "create",
                str(db_path),
                f"--language={language}",
                f"--source-root={source_dir}",
                "--overwrite"
            ]
            
            print(f"🔨 Creating CodeQL database for {language}...")
            print(f"   Command: {' '.join(command)}")
            
            # Run with timeout
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=DB_CREATE_TIMEOUT,
                cwd=str(source_dir)  # Run from source directory
            )
            
            # Check if successful
            if result.returncode != 0:
                # Sanitize error message (remove absolute paths)
                error_msg = result.stderr.replace(str(source_dir), "[SOURCE]")
                error_msg = error_msg.replace(str(db_path), "[DB_PATH]")
                raise RuntimeError(f"Database creation failed: {error_msg}")
            
            # Verify database was created (check for marker file)
            marker_file = db_path / "codeql-database.yml"
            if not marker_file.exists():
                raise RuntimeError(
                    "Database creation appeared successful but marker file not found. "
                    "Database may be corrupted."
                )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Database created successfully in {duration:.2f}s")
            
            return {
                "success": True,
                "duration_seconds": duration,
                "db_path": str(db_path),
                "marker_file_exists": True
            }
            
        except subprocess.TimeoutExpired:
            # Cleanup partial database
            if db_path.exists():
                shutil.rmtree(db_path)
            
            raise RuntimeError(
                f"Database creation timed out after {DB_CREATE_TIMEOUT}seconds. "
                f"Repository may be too large or complex."
            )
            
        except Exception as e:
            # Cleanup on any error
            if db_path.exists():
                shutil.rmtree(db_path)
            raise
    
    def _run_queries(
        self, 
        db_path: Path, 
        language: str, 
        query_suite: str, 
        output_path: Path
    ) -> Dict[str, any]:
        """
        Run CodeQL queries and produce SARIF output.
        
        Args:
            db_path: Path to CodeQL database
            language: Programming language
            query_suite: Query suite to run (already validated)
            output_path: Where to write SARIF file
            
        Returns:
            Dict with execution metadata
            
        Raises:
            RuntimeError: If query execution fails
        """
        # Ensure CodeQL is available
        self._ensure_codeql_available()
        
        # Construct query suite identifier
        # Format: {language}-{query_suite}.qls
        query_suite_id = f"{language}-{query_suite}.qls"
        
        start_time = datetime.utcnow()
        
        try:
            # Build command
            command = [
                self.codeql_path,
                "database",
                "analyze",
                str(db_path),
                query_suite_id,
                "--format=sarif-latest",
                f"--output={output_path}",
                "--rerun"
            ]
            
            print(f"🔍 Running CodeQL queries: {query_suite_id}")
            print(f"   Command: {' '.join(command)}")
            
            # Execute with timeout
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=ANALYZE_TIMEOUT
            )
            
            if result.returncode != 0:
                # Sanitize error
                error_msg = result.stderr.replace(str(db_path), "[DB_PATH]")
                error_msg = error_msg.replace(str(output_path), "[OUTPUT]")
                
                # Check for common errors
                if "Could not resolve query suite" in result.stderr:
                    raise ValueError(
                        f"Query suite {query_suite_id} not found for language {language}. "
                        f"Verify language/suite combination is valid."
                    )
                
                raise RuntimeError(f"Query execution failed: {error_msg}")
            
            # Validate output file exists
            if not output_path.exists():
                raise RuntimeError(
                    "Query execution completed but SARIF file not created"
                )
            
            # Validate SARIF is valid JSON
            try:
                with open(output_path, 'r') as f:
                    sarif_data = json.load(f)
                
                # Count results for logging
                total_results = 0
                for run in sarif_data.get("runs", []):
                    total_results += len(run.get("results", []))
                
                print(f"✅ Query execution complete: {total_results} findings")
                
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"SARIF file is not valid JSON: {str(e)}"
                )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "duration_seconds": duration,
                "output_path": str(output_path),
                "total_results": total_results
            }
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Query execution timed out after {ANALYZE_TIMEOUT} seconds"
            )
    
    def _parse_sarif(self, sarif_path: Path) -> List[CodeQLFinding]:
        """
        Parse SARIF format into CodeQLFinding objects.
        
        Args:
            sarif_path: Path to SARIF JSON file
            
        Returns:
            List of validated CodeQLFinding objects
            
        Note:
            - Skips results with missing locations
            - Defaults unknown severity levels to "medium"
            - Validates all findings through Pydantic
        """
        findings = []
        
        try:
            # Load SARIF file
            with open(sarif_path, 'r', encoding='utf-8') as f:
                sarif_data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid SARIF JSON: {str(e)}")
        except FileNotFoundError:
            raise RuntimeError(f"SARIF file not found: {sarif_path}")
        
        # Iterate over runs
        for run in sarif_data.get("runs", []):
            # Extract rule metadata for recommendations
            rule_metadata = self._extract_rule_metadata(run)
            
            for result in run.get("results", []):
                try:
                    # Extract basic fields
                    rule_id = result.get("ruleId", "unknown")
                    message = result.get("message", {}).get("text", "No description")
                    
                    # Map severity level
                    level = result.get("level", "note")
                    severity = self._map_severity(level)
                    
                    # Log unknown severity levels (optional, for visibility)
                    if level.lower() not in SARIF_SEVERITY_MAP:
                        print(f"⚠️  Unknown severity level '{level}', defaulting to 'medium'")
                    
                    # Extract location information
                    locations = result.get("locations", [])
                    
                    if not locations:
                        print(f"⚠️  Skipping result {rule_id}: no locations")
                        continue
                    
                    for location in locations:
                        physical_location = location.get("physicalLocation", {})
                        artifact_location = physical_location.get("artifactLocation", {})
                        region = physical_location.get("region", {})
                        
                        file_path = artifact_location.get("uri", "unknown")
                        start_line = region.get("startLine", 0)
                        end_line = region.get("endLine", start_line)
                        
                        # Get recommendation from metadata
                        recommendation = rule_metadata.get(
                            rule_id,
                            "Review and fix the identified issue"
                        )
                        
                        # Create and validate finding
                        try:
                            finding = CodeQLFinding(
                                rule_id=rule_id,
                                severity=severity,
                                message=message,
                                file_path=file_path,
                                start_line=start_line,
                                end_line=end_line,
                                recommendation=recommendation
                            )
                            findings.append(finding)
                            
                        except Exception as validation_error:
                            print(
                                f"⚠️  Skipping finding {rule_id}: "
                                f"validation failed - {str(validation_error)}"
                            )
                            continue
                
                except Exception as e:
                    print(f"⚠️  Error parsing result: {str(e)}")
                    continue
        
        print(f"📊 Parsed {len(findings)} valid findings from SARIF")
        return findings
    
    def _extract_rule_metadata(self, run: Dict) -> Dict[str, str]:
        """
        Extract rule metadata (recommendations) from SARIF run.
        
        Args:
            run: SARIF run object
            
        Returns:
            Dict mapping rule_id to recommendation text
        """
        metadata = {}
        
        tool = run.get("tool", {})
        driver = tool.get("driver", {})
        rules = driver.get("rules", [])
        
        for rule in rules:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            
            # Priority: help.text > shortDescription.text > fallback
            recommendation = (
                rule.get("help", {}).get("text", "") or
                rule.get("shortDescription", {}).get("text", "") or
                "Review and fix the identified issue"
            )
            
            metadata[rule_id] = recommendation
        
        return metadata
    
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
    
    def _count_severities(self, findings: List[CodeQLFinding]) -> Dict[str, int]:
        """
        Count findings by severity level.
        
        Args:
            findings: List of CodeQL findings
            
        Returns:
            Dict with counts: {severity_level: count}
            
        Note:
            Explicit loop (no library) for readability and debugging
        """
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for finding in findings:
            severity = finding.severity.value
            if severity in counts:
                counts[severity] += 1
            else:
                # Should never happen due to Pydantic validation
                print(f"⚠️  Unexpected severity: {severity}")
        
        return counts
    
    def _create_response(
        self,
        repo_id: str,
        language: str,
        findings: List[CodeQLFinding]
    ) -> CodeQLResponse:
        """
        Create CodeQLResponse with aggregated findings and counts.
        
        Args:
            repo_id: Repository identifier
            language: Programming language
            findings: List of findings
            
        Returns:
            Validated CodeQLResponse
        """
        # Count severities
        counts = self._count_severities(findings)
        
        # Create response (Pydantic auto-validates)
        response = CodeQLResponse(
            repo_id=repo_id,
            language=language,
            findings=findings,
            total_findings=len(findings),
            critical_count=counts["critical"],
            high_count=counts["high"],
            medium_count=counts["medium"],
            low_count=counts["low"]
        )
        
        # Log summary
        print(
            f"📊 CodeQL scan for {repo_id}: {response.total_findings} findings "
            f"({response.critical_count} critical, {response.high_count} high, "
            f"{response.medium_count} medium, {response.low_count} low)"
        )
        
        # Assert invariant: counts sum to total
        count_sum = (
            response.critical_count + 
            response.high_count + 
            response.medium_count + 
            response.low_count
        )
        assert count_sum == response.total_findings, (
            f"Count invariant violated: {count_sum} != {response.total_findings}"
        )
        
        return response
