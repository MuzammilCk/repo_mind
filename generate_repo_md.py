import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from services.ingest_service import IngestService
from models.requests import IngestRequest, RepoSource

def main():
    repo_url = "https://github.com/MuzammilCk/repo_mind"
    print(f"Ingesting {repo_url}...")
    
    service = IngestService()
    request = IngestRequest(source=RepoSource(url=repo_url))
    
    try:
        response = service.ingest_repository(request)
        print(f"Ingestion complete!")
        print(f"Repo ID: {response.repo_id}")
        print(f"Repo MD Path: {response.repo_md_path}")
        
        # Read content to confirm
        with open(response.repo_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Content length: {len(content)} bytes")
            print("-" * 20)
            print("First 500 characters:")
            print(content[:500])
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
