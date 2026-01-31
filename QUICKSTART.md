# Quick Start Guide - Repo Analyzer

## Prerequisites

1. **Python 3.11+** installed
2. **Git** installed (for repository cloning)
3. **Virtual environment** (recommended)

---

## Installation

### 1. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add your API keys
# Required:
# - GEMINI_API_KEY (for future Phase 2)
# Optional:
# - DEBUG=true (for verbose logging)
# - LOG_LEVEL=INFO
```

---

## Running the Application

### Start the FastAPI Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server will start at: **http://localhost:8000**

---

## Verify Everything Works

### 1. Check Health Endpoint

```bash
# Using curl
curl http://localhost:8000/health

# Using PowerShell
Invoke-WebRequest http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-01-31T...",
  "version": "1.0.0"
}
```

### 2. Check Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

**Expected Response:**
```json
{
  "total_requests": 1,
  "avg_response_time": 0.001,
  "requests_by_endpoint": {...}
}
```

### 3. View API Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Test the API Endpoints

### 1. Ingest a Repository

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\": \"https://github.com/octocat/Hello-World\", \"repo_id\": \"test_repo\"}"
```

**Expected Response:**
```json
{
  "repo_id": "test_repo",
  "status": "success",
  "markdown_path": "workspace/ingest/test_repo/repo.md",
  "stats": {
    "total_files": 5,
    "total_lines": 100,
    "total_size_bytes": 5000
  }
}
```

### 2. Create an Analysis Plan

```bash
curl -X POST http://localhost:8000/api/orchestrator/plan \
  -H "Content-Type: application/json" \
  -d "{\"repo_id\": \"test_repo\", \"query\": \"Analyze security issues\"}"
```

**Expected Response:**
```json
{
  "plan_id": "plan_...",
  "actions": [...],
  "approval_required": true,
  "created_at": "2026-01-31T..."
}
```

### 3. Get Plan Details

```bash
curl http://localhost:8000/api/orchestrator/plan/{plan_id}
```

---

## Run Tests

### Run All Tests

```bash
# Run all tests with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run safety contract tests
pytest tests/unit/test_safety_contracts.py -v
```

### Run Module Validation Scripts

```bash
# Validate specific modules
python validate_1_1.py
python validate_1_2.py
# ... through ...
python validate_1_10.py

# All validation scripts should output:
# {"status": "ok", ...}
```

---

## Verify Safety Contracts

### Test Evidence Validation

```python
from utils.validators import EvidenceValidator, EvidenceEntry
from pathlib import Path

validator = EvidenceValidator(Path("workspace"))

# This should FAIL (non-existent evidence)
fake_evidence = EvidenceEntry(
    file_path="fake.py",
    line_number=1,
    content="fake code",
    source="repo.md"
)
print(validator.validate_evidence(fake_evidence, "test_repo"))  # False
```

### Test Rate Limiting

```python
from utils.rate_limiter import RateLimiter

limiter = RateLimiter(max_calls_per_minute=2)

print(limiter.check_rate_limit("test_tool"))  # True
print(limiter.check_rate_limit("test_tool"))  # True
print(limiter.check_rate_limit("test_tool"))  # False (rate limited!)
```

---

## Project Structure Verification

```bash
# Check all required files exist
dir utils\validators.py
dir services\gemini_config.py
dir utils\audit.py
dir utils\rate_limiter.py
dir prompts\safety_prompts.py
dir tests\unit\test_safety_contracts.py
```

---

## Common Issues

### Issue: Import Errors

**Solution:**
```bash
# Make sure you're in the project directory
cd d:\projects\cli

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Port Already in Use

**Solution:**
```bash
# Use a different port
uvicorn main:app --reload --port 8001
```

### Issue: Workspace Directory Missing

**Solution:**
```bash
# Create workspace directories
mkdir workspace\ingest
mkdir workspace\output
mkdir workspace\memory
mkdir workspace\codeql-dbs
mkdir workspace\plans
mkdir workspace\audit
```

---

## Debug Mode

Enable debug mode for verbose logging:

```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart the server. You'll see detailed JSON logs for every request.

---

## Next Steps

1. ✅ **Phase 1 Complete** - All 10 modules implemented
2. 🔜 **Phase 2** - Gemini Interaction API Integration
3. 🔜 **Phase 3** - Memory Layer (FAISS)
4. 🔜 **Phase 4** - Advanced Features

---

## Quick Health Check Script

```bash
# Run this to verify everything
python -c "
import sys
from pathlib import Path

checks = [
    ('utils/validators.py', 'Evidence validator'),
    ('services/gemini_config.py', 'Gemini config'),
    ('utils/audit.py', 'Audit logger'),
    ('utils/rate_limiter.py', 'Rate limiter'),
    ('prompts/safety_prompts.py', 'Safety prompts'),
    ('tests/unit/test_safety_contracts.py', 'Safety tests'),
]

print('Checking Phase 1 files...')
all_ok = True
for file, name in checks:
    exists = Path(file).exists()
    status = '✅' if exists else '❌'
    print(f'{status} {name}: {file}')
    if not exists:
        all_ok = False

if all_ok:
    print('\n✅ All Phase 1 files present!')
else:
    print('\n❌ Some files missing!')
    sys.exit(1)
"
```

---

## Support

For issues or questions:
1. Check `error.md` for known issues
2. Review `build.md` for implementation details
3. See module reports in `.gemini/antigravity/brain/*/module_*_report.md`
