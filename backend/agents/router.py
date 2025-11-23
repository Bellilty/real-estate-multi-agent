"""
Intent Router Agent – improved, robust, hallucination-safe.
Uses LLM to classify user intent via STRICT JSON schema.
"""

import json
import time
from typing import Dict, Any, List
from backend.utils.prompts import PromptTemplates


class IntentRouter:
    """Classifies user queries into intents using LLM and strict JSON output."""

    VALID_INTENTS = {
        "temporal_comparison",
        "property_comparison",
        "multi_entity_query",
        "pl_calculation",
        "property_details",
        "tenant_info",
        "analytics_query",      # NEW ❗ for list/min/max/sort/aggregations
        "general_query",
        "unsupported"
    }

    VALID_CONFIDENCE = {"high", "medium", "low"}

    def __init__(self, llm):
        self.llm = llm
        self.prompt_templates = PromptTemplates()

    # ------------------------------------------------------------------
    # MAIN INTENT CLASSIFIER
    # ------------------------------------------------------------------
    def classify_intent(
        self,
        user_query: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:

        start = time.time()

        try:
            base_prompt = self.prompt_templates.router_intent_classification(user_query)

            # Add chat history if provided
            prompt = (
                self.prompt_templates.add_chat_context(base_prompt, chat_history)
                if chat_history else base_prompt
            )

            # Strict JSON constraints
            prompt += """
IMPORTANT JSON RULES:
- You MUST return ONLY a valid JSON object.
- Allowed intents (choose ONE): 
  ["temporal_comparison", "property_comparison", "multi_entity_query",
   "pl_calculation", "property_details", "tenant_info",
   "analytics_query", "general_query", "unsupported"]
- "confidence" must be one of: ["high", "medium", "low"].
- Do NOT add text outside the JSON object.
"""

            # Call LLM
            llm_response = self.llm.invoke(prompt)

            # Parse JSON
            parsed = self._parse_json_response(llm_response)

            # Enforce schema
            parsed = self._normalize_result(parsed)

            parsed["duration_ms"] = int((time.time() - start) * 1000)
            return parsed

        except Exception as e:
            # Graceful fallback
            return {
                "intent": "general_query",
                "confidence": "low",
                "reason": f"Router fallback due to error: {str(e)}",
                "duration_ms": int((time.time() - start) * 1000),
            }

    # ------------------------------------------------------------------
    # JSON PARSER WITH MULTIPLE FALLBACKS
    # ------------------------------------------------------------------
    def _parse_json_response(self, response) -> Dict[str, Any]:
        text = response.content if hasattr(response, "content") else str(response)
        text = text.strip()

        # 1. Direct strict JSON
        try:
            return json.loads(text)
        except:
            pass

        # 2. JSON inside ``` blocks
        if "```" in text:
            sections = text.split("```")
            for section in sections:
                if "{" in section and "}" in section:
                    try:
                        json_str = section[section.find("{"): section.rfind("}") + 1]
                        return json.loads(json_str)
                    except:
                        pass

        # 3. First {...} found in response
        if "{" in text and "}" in text:
            try:
                json_str = text[text.find("{"): text.rfind("}") + 1]
                return json.loads(json_str)
            except:
                pass

        raise ValueError(f"Invalid JSON returned by LLM: {text[:160]}")

    # ------------------------------------------------------------------
    # NORMALIZE RESULT (STRICTER THAN BEFORE)
    # ------------------------------------------------------------------
    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        intent = result.get("intent", "general_query")
        confidence = result.get("confidence", "low")
        reason = result.get("reason", "")

        # Validate intent
        if intent not in self.VALID_INTENTS:
            reason = f"Invalid intent '{intent}' returned. Forced to general_query."
            intent = "general_query"
            confidence = "low"

        # Validate confidence
        confidence = confidence.lower().strip()
        if confidence not in self.VALID_CONFIDENCE:
            confidence = "low"

        return {
            "intent": intent,
            "confidence": confidence,
            "reason": reason,
        }

    # Optional tracker helper
    def format_for_tracker(self, result: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        return {
            "step": "Router",
            "duration_ms": result.get("duration_ms", 0),
            "description": (
                f"Intent classified as '{result['intent']}' "
                f"with {result['confidence']} confidence. {result.get('reason', '')}"
            ),
            "metadata": result,
        }
