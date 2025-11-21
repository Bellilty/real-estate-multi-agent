"""
Router Agent v3 - Simplified JSON-based
Uses LLM to classify intent with JSON responses
"""

import json
import time
from typing import Dict, Any, List
from backend.utils.prompts import PromptTemplates


class IntentRouter:
    """Classifies user queries into intents using LLM with JSON output"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt_templates = PromptTemplates()
    
    def classify_intent(
        self, 
        user_query: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Classify user intent using LLM
        
        Args:
            user_query: The user's question
            chat_history: Previous conversation for context
            
        Returns:
            {
                "intent": str,
                "confidence": str (high/medium/low),
                "reason": str,
                "duration_ms": int
            }
        """
        start_time = time.time()
        
        try:
            # Build prompt
            base_prompt = self.prompt_templates.router_intent_classification(user_query)
            
            # Add chat history if available
            if chat_history:
                prompt = self.prompt_templates.add_chat_context(base_prompt, chat_history)
            else:
                prompt = base_prompt
            
            # Call LLM
            response = self.llm.invoke(prompt)
            
            # Parse JSON response
            result = self._parse_json_response(response)
            
            # Validate intent
            valid_intents = [
                "property_comparison", "temporal_comparison", "multi_entity_query",
                "pl_calculation", "property_details", "tenant_info",
                "general_query", "unsupported"
            ]
            
            if result.get("intent") not in valid_intents:
                result["intent"] = "general_query"
                result["confidence"] = "low"
                result["reason"] = "Unrecognized intent, defaulting to general_query"
            
            # Add metadata
            duration_ms = int((time.time() - start_time) * 1000)
            result["duration_ms"] = duration_ms
            
            return result
            
        except Exception as e:
            # Fallback on error
            return {
                "intent": "general_query",
                "confidence": "low",
                "reason": f"Error during classification: {str(e)}",
                "duration_ms": int((time.time() - start_time) * 1000)
            }
    
    def _parse_json_response(self, response) -> Dict[str, Any]:
        """Parse LLM JSON response with fallbacks"""
        # Handle both string and AIMessage
        if hasattr(response, 'content'):
            text = response.content
        else:
            text = str(response)
        
        try:
            # Try direct JSON parse
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            
            # Last resort: return error
            raise ValueError(f"Could not parse JSON from response: {text[:100]}")
    
    def format_for_tracker(self, result: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Format result for chain-of-thought tracker"""
        return {
            "step": "Router",
            "duration_ms": result.get("duration_ms", 0),
            "description": (
                f"Classified as '{result['intent']}' with {result['confidence']} confidence. "
                f"{result.get('reason', '')}"
            ),
            "metadata": {
                "intent": result["intent"],
                "confidence": result["confidence"],
                "user_query": user_query
            }
        }

