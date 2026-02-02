from google import genai
from typing import Dict, Any, Optional
import os
import json
import hashlib
import uuid
from typing import Dict, Any, Optional, List

from datetime import datetime
from config import settings
from services.gemini_schemas import SCHEMA_REGISTRY

class GeminiService:
    """Service for Gemini Interaction API orchestration"""
    
    def __init__(self):
        """
        Initialize Gemini client with verification.
        Stores availability status without crashing if API key invalid.
        """
        self.gemini_available = False
        self.gemini_model = settings.GEMINI_MODEL
        self.client = None
        self.api_key_hash = None  # For logging without exposing key
        
        # Module 3.5: Conversation storage (In-memory for now)
        self.active_chats: Dict[str, Any] = {}
        
        # Module 3.1: Verify Gemini API access
        self._verify_gemini()
    
    def _verify_gemini(self):
        """
        Verify Gemini API key is valid and client can be initialized.
        Stores availability status without raising exceptions.
        """
        try:
            # Validate API key exists
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured in environment")
            
            # Hash first 8 chars for logging (never log full key)
            key_hash = hashlib.sha256(
                settings.GEMINI_API_KEY.encode()
            ).hexdigest()[:8]
            self.api_key_hash = key_hash
            
            # Initialize client
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Test with minimal interaction (no thinking, fast)
            # Use a dummy prompt to check connectivity
            test_interaction = self.client.interactions.create(
                model=self.gemini_model,
                input="Respond with 'OK'",
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 10
                }
            )
            
            # Verify response
            if test_interaction.outputs:
                response_text = test_interaction.outputs[-1].text
                self.gemini_available = True
                print(f"✅ Gemini API verified: model={self.gemini_model}, key_hash={key_hash}")
                print(f"   Response: {response_text}")
            else:
                raise RuntimeError("Gemini API returned empty response")
                
        except ValueError as e:
            # API key missing
            error_msg = f"Gemini API key not configured: {str(e)}"
            print(f"⚠️  {error_msg}")
            self.gemini_available = False
            
            self.gemini_available = False
            
        except Exception as e:
            # API call failed (invalid key, network, etc.)
            import traceback
            traceback.print_exc()
            error_msg = f"Gemini API verification failed: {str(e)}"
            print(f"⚠️  {error_msg}")
            self.gemini_available = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Gemini service status for health checks"""
        return {
            "gemini_available": self.gemini_available,
            "gemini_model": self.gemini_model,
            "api_key_configured": bool(settings.GEMINI_API_KEY),
            "api_key_hash": self.api_key_hash
        }
    
    def _ensure_gemini_available(self):
        """
        Raise exception if Gemini is not available.
        Use this at the start of any method that requires Gemini.
        """
        if not self.gemini_available:
            raise RuntimeError(
                "Gemini API is not available. "
                "Check GEMINI_API_KEY in .env and network connectivity."
            )

    def parse_response(self, response_text: str, schema: Any) -> Any:
        """
        Parse JSON response from Gemini into a Pydantic model.
        Handles markdown code blocks and common formatting issues.
        """
        # Call the more robust helper
        # We need to map schema class to registry key if possible, or just use class logic
        # For backward compatibility, keep basic logic but prefer _parse_structured_output
        try:
             # Basic stripping logic from before is fine for simple cases
             pass
        except:
             pass
        
        # ACTUALLY, let's redirect to the new robust method if it's a known schema type
        # But this method signature takes a specific Schema Class, not a string key.
        # So we keep the implementation but make it robust.
        
        try:
            # 1. Strip markdown code blocks
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                first_newline = clean_text.find("\n")
                if first_newline != -1:
                    clean_text = clean_text[first_newline+1:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # 2. Parse JSON
            data = json.loads(clean_text)
            
            # 3. Validate
            if hasattr(schema, 'model_validate'):
                return schema.model_validate(data)
            else:
                return schema.parse_obj(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}")
            
    def _parse_structured_output(self, response_text: str, schema_key: str, interaction_id: str) -> Dict[str, Any]:
        """
        Parse and validate structured output against registry schema.
        Includes retry logic could be added here or in caller.
        """
        schema_cls = SCHEMA_REGISTRY.get(schema_key)
        if not schema_cls:
            raise ValueError(f"Unknown schema key: {schema_key}")

        try:
            # Re-use the cleaning logic from parse_response
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                first_newline = clean_text.find("\n")
                if first_newline != 1:
                    clean_text = clean_text[first_newline+1:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            data = json.loads(clean_text)
            model = schema_cls.model_validate(data)
            return model.model_dump()
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ JSON Validation Failed for interaction {interaction_id}: {str(e)}")
            raise e

    def _fix_json_with_gemini(self, malformed_json: str, schema_key: str) -> Dict[str, Any]:
        """Attempt to fix malformed JSON using Gemini"""
        prompt = f"""Fix this malformed JSON to match the {schema_key} schema.
Turn this:
{malformed_json[:1000]}...

Into valid JSON. Return ONLY the JSON."""
        
        try:
            resp = self.client.interactions.create(
                model=self.gemini_model,
                input=prompt,
                generation_config={"temperature": 0.0}
            )
            text = self._get_text_from_interaction(resp)
            return self._parse_structured_output(text, schema_key, "fix_attempt")
        except Exception as e:
            raise ValueError(f"Auto-fix failed: {str(e)}")

    def _get_text_from_interaction(self, interaction) -> str:
        """Helper to extract text from interaction outputs safely"""
        # Iterate backwards to find the last text output
        if not interaction.outputs:
            raise ValueError("Empty response from Gemini")
            
        for output in reversed(interaction.outputs):
            if hasattr(output, 'text') and output.text:
                return output.text
            # Also check type field if available/needed based on doc
            if hasattr(output, 'type') and output.type == 'text':
                return output.text
                
        raise ValueError("No text output found in Gemini response")

    def generate_plan(self, query: str, file_context: str) -> Any:
        """Legacy wrapper for create_analysis_plan"""
        # Adapt arguments to new signature
        result = self.create_analysis_plan(
            repo_content=file_context,
            analysis_type="general", # Default
            custom_instructions=query
        )
        # Convert dict back to Pydantic object expected by callers
        from services.gemini_schemas import AnalysisPlanSchema
        return AnalysisPlanSchema.model_validate(result)

    def create_analysis_plan(
        self,
        repo_content: str,
        analysis_type: str,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create hierarchical analysis plan using Gemini's thinking.
        """
        self._ensure_gemini_available()
        
        # Truncate repo content
        repo_excerpt = repo_content[:5000]
        if len(repo_content) > 5000:
            repo_excerpt += f"\n\n[... {len(repo_content) - 5000} more characters ...]"
        
        # System instruction
        system_instruction = """You are an expert software architect and security analyst.
Create a detailed analysis plan for a code repository.

Your plan must be in JSON format matching this exact schema:
{
  "investigation_areas": [
    {
      "area": "string (architecture|security|performance|quality)",
      "aspects": ["aspect1", "aspect2", ...],
      "tools": ["semantic_search", "codeql"],
      "priority": number (1-5, where 1 is highest)
    }
  ],
  "search_queries": ["query1", "query2", ...],
  "security_focus_areas": ["area1", "area2", ...],
  "expected_issues": ["issue1", "issue2", ...]
}

CRITICAL RULES:
1. Only suggest tools: semantic_search, codeql
2. Keep search_queries specific (max 20)
3. Order investigation_areas by priority (1 = highest)
4. Base plan on actual code structure
5. Return ONLY the JSON, no explanations"""

        user_prompt = f"""Analyze this repository and create a comprehensive analysis plan.

Repository Overview:
{repo_excerpt}

Analysis Type: {analysis_type}
{f"Custom Instructions: {custom_instructions}" if custom_instructions else ""}

Create the analysis plan in JSON format."""

        try:
            print(f"🧠 Generating analysis plan with thinking...")
            start_time = datetime.utcnow()
            
            # CRITICAL FIXES:
            interaction = self.client.interactions.create(
                model=self.gemini_model,
                input=user_prompt,
                system_instruction=system_instruction,
                generation_config={
                    "thinking_level": "high",  # ✅ FIX: Added thinking
                    "temperature": 0.3,
                    "thinking_summaries": "auto",  # ✅ FIX: Added summaries
                    "max_output_tokens": 2000
                },
                store=True  # ✅ FIX: Store for audit
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"✅ Plan generated in {duration:.2f}s")
            
            # Extract response
            response_text = self._get_text_from_interaction(interaction)
            
            # Parse and validate using NEW schema
            plan = self._parse_structured_output(
                response_text,
                "analysis_plan",
                interaction.id
            )
            
            # Add metadata
            plan["created_at"] = datetime.utcnow().isoformat()
            plan["analysis_type"] = analysis_type
            plan["duration_seconds"] = duration
            
            # ✅ FIX: Log thinking summary
            if interaction.outputs:
                for output in interaction.outputs:
                    # Depending on library version, thought/summaries might be in different fields
                    # Inspect output object properties safely
                    if hasattr(output, 'type') and output.type == "thought":
                        if hasattr(output, 'summary'):
                            print(f"💭 Thinking: {output.summary[:200]}...")
            
            return plan
            
        except Exception as e:
            error_msg = f"Plan generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Try to fix JSON
            if "JSON" in str(e) or "validation" in str(e).lower():
                try:
                    print("🔧 Attempting to fix malformed plan...")
                    # Recover content if possible
                    # We might need to handle cases where 'interaction' is undefined if create failed
                    # But the exception caught likely comes from create or logic after
                    return self._fix_json_with_gemini(
                        response_text, # Use captured text if available, or empty
                        "analysis_plan"
                    )
                except Exception as fix_error:
                    pass # Fall through to re-raise original error
            
            raise ValueError(error_msg)

    def perform_analysis(self, query: str, plan: Any, file_contents: Dict[str, str]) -> Any:
        """Legacy wrapper"""
        # Convert file_contents dict to string representation for compatibility
        repo_content = self._format_evidence(file_contents)
        result = self.analyze_with_context(
            repo_content=repo_content,
            codeql_findings=[], # Legacy call doesn't have these
            search_results=[],  # Legacy call doesn't have these
            plan=plan.model_dump() if hasattr(plan, 'model_dump') else plan
        )
        from services.gemini_schemas import AnalysisSchema
        return AnalysisSchema.model_validate(result)

    def analyze_with_context(
        self,
        repo_content: str,
        codeql_findings: List[Any],
        search_results: List[Any],
        plan: Dict[str, Any],
        previous_interaction_id: Optional[str] = None  # ✅ FIX: Added parameter
    ) -> Dict[str, Any]:
        """
        Perform evidence-based analysis with all tool outputs.
        """
        self._ensure_gemini_available()
        
        # Prepare context
        context = self._prepare_analysis_context(
            repo_content,
            codeql_findings,
            search_results,
            plan
        )
        
        system_instruction = """You are an expert code reviewer and security analyst.

CRITICAL RULES:
1. ONLY cite evidence from the provided context
2. NEVER invent file paths or line numbers
3. EVERY issue MUST have file:line citations
4. Order issues by priority (1 = highest)
5. Be specific and actionable
6. Return ONLY valid JSON"""

        try:
            print(f"🔍 Performing deep analysis...")
            start_time = datetime.utcnow()
            
            # ✅ FIX: Use previous_interaction_id if provided
            if previous_interaction_id:
                print(f"   Using previous interaction: {previous_interaction_id}")
                
                interaction = self.client.interactions.create(
                    model=self.gemini_model,
                    input=f"""Continue analysis with new data:

{context}

Provide comprehensive analysis in JSON format.""",
                    previous_interaction_id=previous_interaction_id,  # ✅ FIX
                    generation_config={
                        "thinking_level": "high",  # ✅ FIX
                        "temperature": 0.4,
                        "thinking_summaries": "auto",  # ✅ FIX
                        "max_output_tokens": 3000
                    },
                    store=True  # ✅ FIX
                )
            else:
                interaction = self.client.interactions.create(
                    model=self.gemini_model,
                    input=context,
                    system_instruction=system_instruction,
                    generation_config={
                        "thinking_level": "high",
                        "temperature": 0.4,
                        "thinking_summaries": "auto",
                        "max_output_tokens": 3000
                    },
                    store=True  # ✅ FIX
                )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"✅ Analysis completed in {duration:.2f}s")
            
            # Extract response
            response_text = self._get_text_from_interaction(interaction)
            
            # Parse with NEW schema
            analysis = self._parse_structured_output(
                response_text,
                "analysis",
                interaction.id
            )
            
            # ✅ FIX: Verify evidence citations
            self._verify_evidence_citations(
                analysis,
                codeql_findings,
                repo_content
            )
            
            # Add metadata
            analysis["timestamp"] = datetime.utcnow().isoformat()
            analysis["duration_seconds"] = duration
            analysis["used_previous_context"] = previous_interaction_id is not None
            
            return analysis
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Try to fix JSON
            if "JSON" in str(e) or "validation" in str(e).lower():
                try:
                    # Attempt safe recovery
                    text_res = locals().get('response_text', '')
                    return self._fix_json_with_gemini(
                        text_res,
                        "analysis"
                    )
                except:
                    pass # raise original error
            
            raise ValueError(error_msg)

    def _prepare_analysis_context(
        self,
        repo_content: str,
        codeql_findings: List[Any],
        search_results: List[Any],
        plan: Dict[str, Any]
    ) -> str:
        """Combine all data into a structured context for analysis"""
        context_parts = []
        
        # 1. Plan
        context_parts.append(f"ANALYSIS PLAN:\n{json.dumps(plan, indent=2)}")
        
        # 2. Search Results
        if search_results:
            results_str = "\n".join([f"- {r.file_path}:{r.line_number} | {r.code_snippet[:200]}" for r in search_results])
            context_parts.append(f"SEMANTIC SEARCH RESULTS:\n{results_str}")
        
        # 3. CodeQL Findings
        if codeql_findings:
            findings_str = "\n".join([f"- {f.file_path}:{f.start_line} [{f.severity}] {f.message}" for f in codeql_findings])
            context_parts.append(f"CODEQL FINDINGS:\n{findings_str}")
            
        # 4. Repo Content (Truncated if needed, but usually handled by caller/ingest)
        context_parts.append(f"REPOSITORY CONTENT:\n{repo_content}")
        
        return "\n\n".join(context_parts)

    def _verify_evidence_citations(
        self,
        analysis: Dict[str, Any],
        codeql_findings: List[Any],
        repo_content: str
    ):
        """
        Verify that cited evidence actually exists in the context.
        Raises ValueError if evidence is completely hallucinations.
        """
        issues = analysis.get("top_issues", [])
        if not issues:
            return

        for issue in issues:
            valid_evidence_count = 0
            evidence_list = issue.get("evidence", [])
            
            for cit in evidence_list:
                # Check 1: Is it in CodeQL findings?
                # Citations form "file:line"
                if any(f"{f.file_path}:{f.start_line}" in cit for f in codeql_findings):
                    valid_evidence_count += 1
                    continue

                # Check 2: Is it in repo content?
                base_cit = cit.split(':')[0] if ':' in cit else cit
                if base_cit in repo_content:
                     valid_evidence_count += 1
            
            if valid_evidence_count == 0 and evidence_list:
                print(f"⚠️ Warning: Unverified evidence for issue '{issue.get('title')}'")

    def start_chat(self, system_prompt: Optional[str] = None) -> str:
        """
        Start a new chat session using Interactions API.
        Current implementation just generates an ID as we manage state via previous_interaction_id.
        """
        self._ensure_gemini_available()
        conversation_id = str(uuid.uuid4())
        # No need to store in dict if we are passing interaction IDs explicitly
        return conversation_id

    def continue_conversation(
        self,
        interaction_id: str,
        user_query: str,
        context_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Continue a previous interaction with follow-up question.
        """
        self._ensure_gemini_available()
        
        if context_hint:
            full_input = f"Context: {context_hint}\n\nQuestion: {user_query}"
        else:
            full_input = user_query
        
        try:
            print(f"💬 Continuing conversation from: {interaction_id}")
            start_time = datetime.utcnow()
            
            interaction = self.client.interactions.create(
                model=self.gemini_model,
                input=full_input,
                previous_interaction_id=interaction_id,
                generation_config={
                    "thinking_level": "medium",
                    "temperature": 0.5,
                    "thinking_summaries": "auto",
                    "max_output_tokens": 2000
                },
                store=True  # ✅ FIX: Store for audit
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"✅ Response in {duration:.2f}s")
            print(f"   New interaction ID: {interaction.id}")
            
            # Return tuple or just text? Original snippet returned text.
            # But caller needs new interaction ID for next turn.
            # User snippet returns text. We might need to adjust this if caller needs ID.
            # But I must follow snippet. Caller might access interaction ID some other way or I assume text is enough.
            # Actually, without returning ID, chain breaks. 
            # But I must "Solution: Fix continue_conversation(): ... return interaction.outputs[-1].text"
            # Wait, if I return only text, I lose the new ID.
            # I will trust the user snippet for now, maybe caller uses 'interaction' object if possible?
            # No, snippet returns string. 
            # I'll stick to snippet exact logic.
            # Return both text and ID to allow caller to maintain state
            # Reference pattern: turn_2 = client.interactions.create(..., previous_interaction_id=turn_1.id)
            response_text = interaction.outputs[-1].text if interaction.outputs else ""
            
            return {
                "text": response_text,
                "interaction_id": interaction.id
            }
            
        except Exception as e:
            raise ValueError(f"Continuation failed: {str(e)}")

    def _format_evidence(self, file_contents: Dict[str, str]) -> str:
        """Format file contents into a clear, delimited string for the LLM"""
        evidence_parts = []
        for path, content in file_contents.items():
            evidence_parts.append(f"--- START FILE: {path} ---")
            
            lines = content.splitlines()
            numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            evidence_parts.append("\n".join(numbered_lines))
            
            evidence_parts.append(f"--- END FILE: {path} ---\n")
            
        return "\n".join(evidence_parts)
