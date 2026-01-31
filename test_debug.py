"""Quick test to debug ingest service"""
import tempfile
from pathlib import Path
from services.ingest_service import IngestService
from models.requests import IngestRequest, RepoSource

# Create a temp repo
tmp_dir = Path(tempfile.mkdtemp())
repo_dir = tmp_dir / "test_repo"
repo_dir.mkdir()

# Create a simple file
(repo_dir / "test.py").write_text("print('hello')\n")

# Try to ingest
service = IngestService()
request = IngestRequest(
    source=RepoSource(local_path=str(repo_dir))
)

try:
    response = service.ingest_repository(request)
    print(f"SUCCESS: {response.repo_id}")
    print(f"Files: {response.file_count}")
    print(f"Lines: {response.total_lines}")
    print(f"Languages: {response.languages}")
    print(f"repo_md_path: {response.repo_md_path}")
    print(f"tree_json_path: {response.tree_json_path}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
