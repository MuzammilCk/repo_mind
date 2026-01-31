"""
Prompt templates enforcing safety contracts
Contract: AI must cite evidence for all claims
"""

EVIDENCE_BASED_ANALYSIS_PROMPT = """
You are analyzing a code repository. You must follow these STRICT rules:

1. **EVIDENCE-ONLY CLAIMS**: You may ONLY make claims about the repository based on the provided tool outputs below. Never invent or assume facts.

2. **CITE YOUR SOURCES**: For EVERY claim you make, you MUST:
   - Quote the exact file path and line number
   - Include the relevant code snippet
   - Reference which tool output it came from (repo.md, CodeQL, SeaGOAT)

3. **JSON OUTPUT ONLY**: Your response MUST be valid JSON with this structure:
   ```json
   {{
     "analysis": "Your analysis here",
     "findings": [
       {{
         "description": "Finding description",
         "evidence": {{
           "file_path": "path/to/file.py",
           "line_number": 42,
           "content": "actual code line",
           "source": "repo.md"
         }}
       }}
     ]
   }}
   ```

4. **NO SPECULATION**: If you don't have evidence for something, explicitly state "No evidence found in provided outputs."

## Tool Outputs:

{tool_outputs}

## Your Task:

{task_description}

Remember: Every claim must be backed by evidence from the tool outputs above. Quote file paths and line numbers.
"""

PLAN_GENERATION_PROMPT = """
You are creating an analysis plan for a code repository. Follow these STRICT rules:

1. **JSON-ONLY OUTPUT**: Your response MUST be valid JSON matching this exact schema:
   ```json
   {{
     "plan_id": "generated_id",
     "actions": [
       {{
         "action": "action_name",
         "params": {{}},
         "rationale": "why this action"
       }}
     ],
     "approval_required": true,
     "evidence": []
   }}
   ```

2. **NO EXECUTION**: You are ONLY creating a plan. Do NOT execute any actions.

3. **APPROVAL REQUIRED**: Set `approval_required: true` for ANY action that:
   - Runs external tools
   - Modifies files
   - Makes network requests

4. **EVIDENCE-BASED**: If referencing repository contents, include evidence entries.

## Repository Context:

{repo_context}

## Analysis Request:

{analysis_request}

Generate the plan as valid JSON.
"""

FIX_JSON_PROMPT = """
The JSON you provided was invalid. Here is the error:

{validation_error}

Please fix the JSON to match the required schema. Return ONLY valid JSON, no explanations.

Original JSON:
{original_json}

Required schema:
{schema}
"""

EVIDENCE_CITATION_RULES = """
## Evidence Citation Rules

When making ANY claim about the repository, you MUST:

1. **Cite the source**: Specify which tool output (repo.md, CodeQL SARIF, SeaGOAT JSON)
2. **Quote the file path**: Exact path as it appears in the tool output
3. **Provide line number**: Specific line number where the evidence appears
4. **Include the content**: The actual code or text that supports your claim

Example:
"The authentication function uses bcrypt for password hashing (file: auth/password.py, line: 42, source: repo.md, content: 'bcrypt.hashpw(password, salt)')"

**NEVER** make claims like:
- "The code probably uses..."
- "It appears that..."
- "Based on common patterns..."

**ALWAYS** make claims like:
- "According to repo.md, file auth/password.py line 42..."
- "The CodeQL analysis shows in file api/routes.py line 15..."
"""
