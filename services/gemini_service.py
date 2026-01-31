from google import genai
from typing import Dict, Any, Optional
import os
import json
import hashlib
import uuid
from typing import Dict, Any, Optional

from config import settings

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
            if test_interaction.outputs and len(test_interaction.outputs) > 0:
                self.gemini_available = True
                print(f"✅ Gemini API verified: model={self.gemini_model}, key_hash={key_hash}")
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
        try:
            # 1. Strip markdown code blocks
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                # Remove opening ```json or ```
                first_newline = clean_text.find("\n")
                if first_newline != -1:
                    clean_text = clean_text[first_newline+1:]
                
                # Remove closing ```
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # 2. Parse JSON
            data = json.loads(clean_text)
            
            # 3. Validate against schema
            if hasattr(schema, 'model_validate'):
                return schema.model_validate(data)
            else:
                return schema.parse_obj(data)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Gemini response: {e}\nResponse was: {response_text[:100]}...")

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
        self._ensure_gemini_available()
        from services.prompts import PLANNER_SYSTEM_PROMPT
        from models.gemini import AnalysisPlan
        
        full_prompt = (
            f"CONTEXT:\n{file_context}\n\n"
            f"USER QUERY:\n{query}\n\n"
            "Generate your investigation plan in JSON."
        )
        
        try:
            response = self.client.interactions.create(
                model=self.gemini_model,
                input=full_prompt,
                system_instruction=PLANNER_SYSTEM_PROMPT,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 1024
                }
            )
            
            response_text = self._get_text_from_interaction(response)
            return self.parse_response(response_text, AnalysisPlan)
            
        except Exception as e:
            if isinstance(e, ValueError): pass # Re-raise
            raise ValueError(f"Plan generation failed: {str(e)}") from e

    def perform_analysis(self, query: str, plan: Any, file_contents: Dict[str, str]) -> Any:
        self._ensure_gemini_available()
        from services.prompts import ANALYST_SYSTEM_PROMPT
        from models.gemini import AnalysisResult
        
        evidence_str = self._format_evidence(file_contents)
        
        full_prompt = (
            f"USER QUERY:\n{query}\n\n"
            f"PLAN:\n{json.dumps(plan.model_dump() if hasattr(plan, 'model_dump') else plan, indent=2)}\n\n"
            f"EVIDENCE:\n{evidence_str}\n\n"
            "Analyze the evidence and provide findings in JSON."
        )
        
        try:
            response = self.client.interactions.create(
                model=self.gemini_model,
                input=full_prompt,
                system_instruction=ANALYST_SYSTEM_PROMPT,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 4096
                }
            )
            
            response_text = self._get_text_from_interaction(response)
            return self.parse_response(response_text, AnalysisResult)
            
        except Exception as e:
            if isinstance(e, ValueError): pass
            raise ValueError(f"Analysis failed: {str(e)}") from e

    def start_chat(self, system_prompt: Optional[str] = None) -> str:
        """
        Start a new chat session using Interactions API.
        For Interactions, 'starting' a chat just means generating a session ID 
        and optionally sending the first message OR just preparing the state.
        
        Since our API separates 'start' from 'message', we'll just generate an ID 
        and store the system prompt for later use if needed, 
        BUT Interactions API sends system_instruction with EACH turn if stateless, 
        OR we can just assume the first interaction sets it? 
        Actually, doc says: "only conversation history is preserved... system_instruction... apply only to specific interaction".
        So we must store the system prompt and resend it every time? 
        OR we rely on the model remembering context from history?
        Usually valid system prompt is needed each time for strict adherence.
        Let's store it.
        """
        self._ensure_gemini_available()
        
        conversation_id = str(uuid.uuid4())
        self.active_chats[conversation_id] = {
            "last_interaction_id": None,
            "system_instruction": system_prompt
        }
        return conversation_id
            
    def continue_chat(self, conversation_id: str, message: str) -> str:
        """
        Send a message using previous_interaction_id for context.
        """
        self._ensure_gemini_available()
        
        if conversation_id not in self.active_chats:
            raise ValueError(f"Conversation ID {conversation_id} not found")
            
        session_data = self.active_chats[conversation_id]
        last_id = session_data.get("last_interaction_id")
        sys_prompt = session_data.get("system_instruction")
        
        try:
            # Prepare kwargs
            kwargs = {
                "model": self.gemini_model,
                "input": message,
                "generation_config": {
                    "temperature": 0.5,
                    "max_output_tokens": 2048
                }
            }
            if last_id:
                kwargs["previous_interaction_id"] = last_id
            
            if sys_prompt:
                # Re-sending system prompt might be redundant if using previous_interaction_id? 
                # Doc says: "You must re-specify these parameters in each new interaction if you want them to apply."
                kwargs["system_instruction"] = sys_prompt

            response = self.client.interactions.create(**kwargs)
            
            # Update state
            session_data["last_interaction_id"] = response.id
            
            return self._get_text_from_interaction(response)
            
        except Exception as e:
            raise ValueError(f"Chat failed: {str(e)}")

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
