"""Quick test to debug search service"""
from services.search_service import SearchService

MOCK_OUTPUT = """src/auth/login.py:42:def authenticate_user(username, password):
src/auth/login.py:43:    if not username or not password:
src/utils/helpers.py:10:def validate_credentials(user, pwd):
"""

service = SearchService()
results = service._parse_seagoat_output(MOCK_OUTPUT, 10)

print(f"Number of results: {len(results)}")
for i, r in enumerate(results):
    print(f"\nResult {i+1}:")
    print(f"  File: {r.file_path}")
    print(f"  Line: {r.line_number}")
    print(f"  Score: {r.relevance_score}")
    print(f"  Snippet: {r.code_snippet[:50]}...")
