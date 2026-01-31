# ABSOLUTE RULES FOR THE AI

## 🚨 CORE PRINCIPLES (NEVER VIOLATE)

### Rule 1: No Invention
- **Do NOT invent** files, tools, APIs, or behaviors
- **Do NOT assume** any library, method, or feature exists without verifying
- **Do NOT create** placeholder code with "TODO" or "implement later"
- **Do NOT use** features from newer versions than specified in requirements.txt
- If you don't know → **STOP and ASK**

### Rule 2: Stay in Scope
- **Operate ONLY** inside the current phase + module
- **Do NOT** implement features from future phases
- **Do NOT** refactor code from completed phases
- **Do NOT** add "nice to have" features
- Stick to the **EXACT** module specification

### Rule 3: Fail Fast on Missing Dependencies
- If a dependency is missing → **STOP and REPORT**
- If a file doesn't exist → **STOP and REPORT**
- If an import fails → **STOP and REPORT**
- **Do NOT** create workarounds or fallbacks unless explicitly specified
- **Format:** `BLOCKED: Missing dependency <name>. Required for <module>.`

### Rule 4: Never Assume Formats
- **Do NOT assume** tool output formats
- **Always parse and validate** external tool outputs
- **Use explicit schemas** (Pydantic) for all data structures
- **Verify** every field exists before accessing
- **Handle** missing/malformed data with explicit error messages

### Rule 5: Sequential Execution
- **Never skip steps** in module implementation
- **Never jump phases** or modules
- Complete **ALL acceptance criteria** before marking module done
- Run **ALL tests** before proceeding to next module
- **Document** each completed step

### Rule 6: Explicit Blocking
- If unsure → **STOP with:** `BLOCKED: NEED INPUT - <specific question>`
- **Do NOT guess** at requirements
- **Do NOT implement** ambiguous specifications
- **Ask for clarification** before proceeding
- Better to block than to implement wrong

### Rule 7: Deterministic Outputs
- All outputs must be **deterministic & reproducible**
- **Use fixed seeds** where randomness is needed
- **Log exact inputs** that produce outputs
- **No random file names** - use UUIDs or timestamps
- **Test reproducibility** - same input = same output

### Rule 8: No Unsolicited Changes
- No "future improvements" unless explicitly asked
- No "ideas" or "optimizations" unless requested
- No auto-refactoring or architecture changes
- No "better ways" unless current approach is broken
- **Implement exactly** what's specified, nothing more

---

## 🧠 PHASE 3 SPECIFIC RULES (Gemini Integration)

### Rule 9: Temperature Constraints (CRITICAL)
- **Structured outputs** (plans, analysis): `temperature ≤ 0.4`
- **Conversational** (follow-ups): `temperature ≤ 0.5`
- **Test interactions**: `temperature = 0.0`
- **NEVER** use temperature > 0.5 for any production code
- **Format:** Always specify temperature explicitly in `generation_config`

### Rule 10: Evidence Citation Requirements (ANTI-HALLUCINATION)
- **EVERY issue** must cite `file:line` from tool outputs
- **EVERY claim** must reference specific evidence
- **VERIFY** all citations exist in CodeQL findings or repo content
- **NEVER invent** file paths or line numbers
- **FAIL** if evidence cannot be verified
- **Format:** Evidence must match regex `^.*:\d+$` (file:line)

### Rule 11: JSON Schema Validation (MANDATORY)
- **ALL Gemini responses** must validate against explicit Pydantic schemas
- **NEVER** use dynamic schema generation
- **ALWAYS** use `_parse_structured_output()` helper
- **REJECT** responses that don't match schema
- **ATTEMPT** auto-fix once with `_fix_json_with_gemini()`
- **FAIL** if fix attempt doesn't work
- **Schema registry** in `services/gemini_schemas.py` - add new schemas there only

### Rule 12: Thinking Level Constraints
- **Planning** (create_analysis_plan): `thinking_level = "high"`
- **Analysis** (analyze_with_context): `thinking_level = "high"`
- **Conversation** (continue_conversation): `thinking_level = "medium"`
- **Tests**: `thinking_level = "low"` or omit
- **NEVER** use `thinking_level = "high"` for simple queries
- **ALWAYS** set `thinking_summaries = "auto"` when using thinking

### Rule 13: Stateful Conversation Rules
- **ALWAYS** pass `previous_interaction_id` when continuing conversations
- **NEVER** send full history manually (use Gemini's state management)
- **ALWAYS** set `store = True` for production interactions
- **ALWAYS** set `store = False` for test/verification interactions
- **VERIFY** interaction exists before using as previous_interaction_id
- **LOG** both old and new interaction IDs when continuing

### Rule 14: API Key Security (ABSOLUTE)
- **NEVER** log full API key
- **ONLY** log first 8 chars of SHA256 hash
- **NEVER** expose API key in error messages
- **NEVER** expose API key in API responses
- **NEVER** commit API key to code
- **VERIFY** API key from environment only
- **Format:** `api_key_hash = hashlib.sha256(key.encode()).hexdigest()[:8]`

### Rule 15: Timeout Enforcement
- **ALL Gemini API calls**: max 120 seconds
- **ALL subprocess calls**: max 600 seconds (or as specified)
- **ALWAYS** use `timeout` parameter
- **CATCH** `TimeoutError` explicitly
- **RETURN** structured error on timeout
- **LOG** timeout duration and context

### Rule 16: Evidence Verification Before Return
- **BEFORE** returning analysis, run `_verify_evidence_citations()`
- **CHECK** every citation against CodeQL findings
- **CHECK** every filepath exists in repo content
- **WARN** for unverifiable evidence (log only)
- **FAIL** if ALL evidence for an issue is invalid
- **NEVER** return analysis with zero verified evidence

---

## 🧪 TESTING RULES (MANDATORY)

### Rule 17: Test Coverage Requirements
- **EVERY module** must have unit tests
- **EVERY endpoint** must have integration tests
- **EVERY error path** must have a test
- **Test BOTH** success and failure cases
- **Mock external calls** (Gemini API, subprocess)
- **Run tests** after every module completion

### Rule 18: Test Data Management
- **USE fixtures** in `tests/fixtures/` for test repos
- **NEVER** use real repositories in unit tests
- **ALWAYS** mock Gemini responses in unit tests
- **CREATE** sample SARIF files as fixtures
- **STORE** example JSON responses for parsing tests
- **DO NOT** commit large test files (>100KB)

### Rule 19: Regression Testing (CRITICAL)
- **AFTER every Phase 3 module**, run Phase 1 tests
- **AFTER every Phase 3 module**, run Phase 2 tests
- **IF regression detected** → STOP and REPORT
- **DO NOT proceed** until regression fixed
- **MAINTAIN** backward compatibility at all times

### Rule 20: Test-Driven Validation
- **READ test** before implementing module
- **UNDERSTAND** acceptance criteria from tests
- **IMPLEMENT** to make tests pass
- **VERIFY** all tests green before marking done
- **FORMAT:** Run `pytest tests/test_<module>.py -v` after each module

---

## 🔧 ERROR HANDLING RULES

### Rule 21: HTTP Status Code Accuracy
- **503** Service Unavailable: Gemini/CodeQL not available
- **404** Not Found: Interaction/repo not found
- **422** Unprocessable Entity: Validation failed (schema/evidence/format)
- **504** Gateway Timeout: Operation timed out
- **500** Internal Server Error: Unexpected errors only
- **NEVER** return 500 for expected error conditions
- **ALWAYS** include `detail` dict in HTTPException

### Rule 22: Error Message Structure
- **ALWAYS** sanitize error messages (remove paths)
- **NEVER** expose Python tracebacks to users
- **ALWAYS** log full error server-side
- **FORMAT:** `{"error": "type", "message": "description", "hint": "what to do"}`
- **INCLUDE** specific field that failed in validation errors
- **PROVIDE** actionable next steps

### Rule 23: Graceful Degradation
- **IF Gemini unavailable** → return 503, don't crash
- **IF CodeQL unavailable** → return 503, don't crash
- **IF SeaGOAT unavailable** → continue without it (optional feature)
- **ALWAYS** check service availability before use
- **NEVER** assume service is available
- **LOG** service unavailability warnings

---

## 📝 CODE QUALITY RULES

### Rule 24: Type Hints (MANDATORY)
- **ALL functions** must have type hints
- **ALL parameters** must be typed
- **ALL return values** must be typed
- **USE** `from typing import` for complex types
- **VERIFY** with mypy if available
- **FORMAT:** `def func(arg: str, opt: Optional[int] = None) -> Dict[str, Any]:`

### Rule 25: Documentation Standards
- **ALL modules** must have module docstring
- **ALL classes** must have class docstring
- **ALL public methods** must have docstring with Args/Returns/Raises
- **COMPLEX logic** must have inline comments
- **USE** Google-style docstrings
- **FORMAT:**
  ```python
  """
  Brief description.
  
  Detailed explanation if needed.
  
  Args:
      param1: Description
      param2: Description
      
  Returns:
      Description of return value
      
  Raises:
      ExceptionType: When this happens
  """
  ```

### Rule 26: Logging Standards
- **USE** print() for progress/status (simple projects)
- **FORMAT:** `print(f"✅ Step completed in {duration:.2f}s")`
- **EMOJI guide:**
  - ✅ Success
  - ❌ Error/Failure
  - ⚠️ Warning
  - 🔍 Analysis/Search
  - 🧠 AI/Thinking
  - 💬 Conversation
  - 🔧 Fix/Repair
  - 📊 Statistics/Summary
- **NEVER** log sensitive data (API keys, secrets)
- **ALWAYS** log interaction IDs for tracing

### Rule 27: No Magic Numbers
- **DEFINE** constants at module/class level
- **NAME** constants descriptively
- **FORMAT:** `MAX_RETRIES = 3`, `TIMEOUT_SECONDS = 120`
- **NO** hardcoded values in logic
- **EXCEPTIONS:** 0, 1, -1 in obvious contexts (indexing, boolean)

---

## 🔒 SECURITY RULES

### Rule 28: Input Validation (ALWAYS)
- **VALIDATE** all user inputs with Pydantic
- **SANITIZE** file paths (no traversal: `..`, `/`, `\`)
- **WHITELIST** allowed characters in identifiers
- **VALIDATE** repo_id format: `^[a-f0-9]{8}$`
- **VALIDATE** query_suite against explicit whitelist
- **REJECT** invalid inputs with 422

### Rule 29: Subprocess Safety (CRITICAL)
- **NEVER** use `shell=True`
- **ALWAYS** use list arguments: `["cmd", "arg1", "arg2"]`
- **ALWAYS** set timeout
- **VALIDATE** inputs before passing to subprocess
- **SANITIZE** error messages before returning
- **CATCH** subprocess errors explicitly

### Rule 30: Path Safety
- **ALWAYS** use Path objects, not strings
- **VERIFY** paths are within workspace
- **RESOLVE** symbolic links before use
- **CHECK** path exists before operations
- **NEVER** construct paths with user input directly
- **USE** `Path.joinpath()` or `/` operator

---

## 📊 PERFORMANCE RULES

### Rule 31: Timeout All External Calls
- **Gemini API**: 120 seconds max
- **CodeQL database create**: 600 seconds max
- **CodeQL analyze**: 600 seconds max
- **SeaGOAT index**: 60 seconds max
- **SeaGOAT search**: 30 seconds max
- **Git clone**: 300 seconds max
- **ALWAYS** handle TimeoutError

### Rule 32: Resource Limits
- **Repo content**: Truncate to 10,000 chars for analysis context
- **Repo excerpt**: Truncate to 5,000 chars for planning
- **CodeQL findings**: Limit to top 20 in context
- **Search results**: Limit to top 10 in context
- **Max issues**: 10 per analysis
- **Max recommendations**: 10 per analysis

### Rule 33: No Blocking Operations
- **AVOID** synchronous waits in request handlers
- **USE** async/await for I/O operations where possible
- **DELEGATE** long operations to background tasks
- **RETURN** 202 Accepted for background operations
- **PROVIDE** status endpoint for long operations

---

## 🎯 COMPLETION CRITERIA

### Rule 34: Module Completion Checklist
Before marking a module complete, verify:
- [ ] All code implemented exactly as specified
- [ ] All type hints present
- [ ] All docstrings present
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] All acceptance criteria met
- [ ] No regression in previous phases
- [ ] Error handling complete
- [ ] Logging in place
- [ ] Code reviewed against rules

### Rule 35: Phase Completion Checklist
Before marking a phase complete, verify:
- [ ] All modules completed
- [ ] Full integration test passes
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] No breaking changes to previous phases
- [ ] All error paths tested
- [ ] Security review passed
- [ ] Code quality check passed

---

## ⚠️ BLOCKING CONDITIONS

**IMMEDIATELY STOP and REPORT if:**

1. ❌ Import fails for specified library
2. ❌ File specified in module doesn't exist
3. ❌ Test fails after implementation
4. ❌ Regression detected in previous phase
5. ❌ Specification ambiguous or contradictory
6. ❌ Required tool (CodeQL, SeaGOAT) not installed when needed
7. ❌ API key missing when required
8. ❌ Schema validation fails on critical path
9. ❌ Evidence verification fails for all issues
10. ❌ Timeout occurs repeatedly (>3 times)

**FORMAT for blocking:**
```
BLOCKED: <Reason>
Module: <current module>
Dependency: <what's missing>
Context: <what you were trying to do>
Need: <what's needed to proceed>
```

---

## 📋 SUMMARY CHECKLIST (Use Before Every Implementation)

Before writing ANY code, verify:
- [ ] I understand the EXACT module specification
- [ ] I have read the acceptance criteria
- [ ] I know which files to modify
- [ ] I know which tests to run
- [ ] I understand the error handling required
- [ ] I will NOT invent any features
- [ ] I will NOT skip any steps
- [ ] I will STOP if blocked

**Remember:**
- ✅ **Explicit > Implicit**
- ✅ **Fail Fast > Fail Silent**
- ✅ **Ask > Assume**
- ✅ **Test > Hope**
- ✅ **Verify > Trust**

---

## 🚀 EXECUTION ORDER (Reminder)

1. **Read** module specification completely
2. **Check** all dependencies exist
3. **Review** acceptance criteria
4. **Implement** exactly as specified
5. **Test** continuously during implementation
6. **Verify** all acceptance criteria met
7. **Run** regression tests
8. **Document** completion
9. **Move** to next module

**NEVER deviate from this order.**

---

## END OF RULES

*These rules are ABSOLUTE. No exceptions. No workarounds. No "improvements".*
*When in doubt, STOP and ASK.*
*Better to block than to break.*