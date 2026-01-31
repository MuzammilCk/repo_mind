# Manual Testing Guide (Phases 1-3)

This guide helps you manually verify the capabilities built in Phases 1, 2, and 3.

## ⚡ Quick Start

We have created an interactive Python script to make testing easy (handling HMAC signatures automatically).

1. **Start the API Server** (in a separate terminal):
   ```bash
   uvicorn main:app --reload
   ```

2. **Run the Test Kit**:
   ```bash
   python manual_test_kit.py
   ```

---

## 🧪 Detailed Test Scenarios

### Scenario 1: Basic Ingestion (Phase 1)
**Goal**: Verify the system can read and parse a repository.

1. Select **Option 1 (Ingest Repository)** in the script.
2. Enter the path to this project (e.g., `d:/projects/cli`) or any other git repo.
3. **Verify**:
   - You receive a JSON response with `status: success`.
   - A `repo.md` file is created in `workspace/ingest/<repo_id>/`.

### Scenario 2: Deep Analysis with Gemini (Phase 3)
**Goal**: Verify the Orchestrator + Gemini "Thinking" workflow.

1. Select **Option 2 (Run Deep Analysis)**.
2. Enter the `repo_id` you used in Scenario 1.
3. Enter a query, e.g., *"Analyze the architecture of the services module"*.
4. **Observe the Workflow**:
   - **Step 1 (Plan)**: The system asks Gemini to create a plan. You'll see a `plan_id` and actions like `gemini_think`.
   - **Step 2 (Approve)**: The script automatically signs the plan (HMAC-SHA256) acting as "admin".
   - **Step 3 (Execute)**: The Orchestrator runs the plan.
     - It calls `gemini_think` to select files.
     - It calls `gemini_analyze` to read those files and generate findings.
5. **Verify**:
   - The script prints **GEMINI FINDINGS**.
   - You see a "Summary", specific "Findings" with line numbers, and a "Confidence Score".

### Scenario 3: API Health Check (Phase 1-3)
**Goal**: Verify all services are online.

1. Curl the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```
2. **Verify**:
   - `gemini_available`: `true`
   - `codeql_available`: `false` (Expected, unless CodeQL CLI is in path)
   - `services.orchestrator`: `available`

---

## 🔍 Troubleshooting

- **Server Access**: Ensure `localhost:8000` is reachable.
- **Gemini Error**: If analysis fails, check your API key in `.env`.
- **HMAC Error**: If "Invalid Signature", ensure `SECRET_KEY` in `manual_test_kit.py` matches `settings.ORCHESTRATOR_SECRET_KEY` (default: "test-secret-key").
