"""
FollowUp Resolver Agent - Improved Version
Detects and resolves follow-up questions using conversation context
"""

import time
from typing import Dict, Any, List


class FollowUpResolverAgent:
    """
    Intelligent follow-up resolution agent

    Responsibilities:
    1. Detect if query is a follow-up
    2. Extract context from chat history
    3. Rewrite current query to be self-contained
    4. Signal metadata to downstream agents
    """

    def __init__(self, llm):
        self.llm = llm

    def process(self, user_query: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        start_time = time.time()

        # No history → cannot be follow-up
        if not chat_history:
            return self._ok(
                is_followup=False,
                updated_query=user_query,
                original_query=user_query,
                context_used={},
                notes="No chat history available",
                start_time=start_time
            )

        # ---- FOLLOW-UP DETECTION (IMPROVED HEURISTICS) ----
        followup_indicators = [
            "and for", "also for",
            "what about", "how about",
            "same for", "and what about",
            "then what", "in that case",
            "and in", "and for", "and what",  # Added patterns like "And in 2025?"
            "what is", "show me", "give me",  # Questions that might reference previous context
            "compare", "compare it", "compare that", "compare them"  # Comparison follow-ups
        ]

        # Only strong signals, no "and", "also" alone (avoid false positives)
        q_lower = user_query.lower().strip()
        has_indicator = any(ind in q_lower for ind in followup_indicators)

        # Referring words detection (improved - not limited to short queries)
        referring_terms = ["it", "that", "this", "them", "those"]
        has_referring_term = any(t in q_lower for t in referring_terms)
        
        # Short queries → suspicious if:
        # 1. Has referring words
        # 2. Starts with "and" or "what" (common follow-up patterns)
        # 3. Contains time references without property (e.g., "in 2025?")
        is_short_ref = len(user_query.split()) <= 4 and has_referring_term
        
        # Queries with referring terms + action verbs (e.g., "Compare it to...", "Show me that...")
        action_verbs = ["compare", "show", "give", "tell", "what", "how"]
        has_action_with_ref = has_referring_term and any(verb in q_lower for verb in action_verbs)
        
        # Check for time-only queries (likely follow-ups)
        time_only_patterns = ["in 202", "in q", "for 202", "in march", "in january"]
        is_time_only = any(pattern in q_lower for pattern in time_only_patterns) and len(user_query.split()) <= 5
        
        # Check if starts with common follow-up words
        starts_with_followup = q_lower.startswith(("and ", "what ", "how ", "show ", "give ", "tell ", "compare "))

        likely_followup = has_indicator or is_short_ref or is_time_only or starts_with_followup or has_action_with_ref

        if not likely_followup:
            return self._ok(
                is_followup=False,
                updated_query=user_query,
                original_query=user_query,
                context_used={},
                notes="Query appears self-contained",
                start_time=start_time
            )

        # ---- BUILD LLM PROMPT ----
        prompt = self._build_enrichment_prompt(user_query, chat_history)

        try:
            llm_response = self.llm.invoke(prompt)
            enriched_query = self._parse_response(llm_response)

            if not enriched_query:  # robustness
                enriched_query = user_query

            context_used = self._extract_context(chat_history)

            # ---- OVERALL LOGIC (IMPROVED) ----
            overall_indicators = ["overall", "all years", "all time"]
            has_overall = any(term in q_lower for term in overall_indicators)

            if has_overall:
                context_used["clear_timeframes"] = True

            return {
                "status": "ok",
                "is_followup": True,
                "updated_query": enriched_query,
                "original_query": user_query,
                "context_used": context_used,
                "needs_clarification": False,
                "notes": f"Follow-up detected, enriched using last {len(chat_history)} turns",
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            return {
                "status": "error",
                "is_followup": likely_followup,
                "updated_query": user_query,
                "original_query": user_query,
                "context_used": {},
                "needs_clarification": False,
                "notes": f"Enrichment failed: {e}",
                "error": str(e),
                "duration_ms": int((time.time() - start_time) * 1000)
            }

    # -----------------------------------------------------
    # INTERNAL HELPERS
    # -----------------------------------------------------

    def _ok(self, is_followup, updated_query, original_query, context_used, notes, start_time):
        return {
            "status": "ok",
            "is_followup": is_followup,
            "updated_query": updated_query,
            "original_query": original_query,
            "context_used": context_used,
            "notes": notes,
            "needs_clarification": False,
            "duration_ms": int((time.time() - start_time) * 1000)
        }

    def _build_enrichment_prompt(self, user_query: str, chat_history: List[Dict[str, str]]) -> str:
        history_text = ""
        for turn in chat_history[-3:]:  # last 3 exchanges
            if "user" in turn:
                history_text += f"User: {turn['user']}\n"
            if "assistant" in turn:
                history_text += f"Assistant: {turn['assistant']}\n\n"

        return f"""
You are a FOLLOW-UP QUERY RESOLVER.

Your task is to rewrite the CURRENT QUERY so that it becomes **fully self-contained**,
INCLUDING any missing entities or dates from the previous conversation.

CHAT HISTORY:
{history_text}

CURRENT QUERY:
"{user_query}"

RULES:
1. Do NOT change the user's intent.
2. Replace vague references ("it", "that", "them") with the actual property/period from history.
3. If the user says "and for X" or "and in X", rewrite as a full standalone query with ALL context from history.
   - Example: Previous "What is the P&L for Building 180 in 2024?" + "And in 2025?" → "What is the P&L for Building 180 in 2025?"
4. If user says "all buildings / all properties" → rewrite using generic "all properties" (Do NOT enumerate names).
5. Add missing timeframes ONLY if they were mentioned before.
6. NEVER invent entities, properties, or years.
7. For temporal comparison follow-ups (e.g., "What about Q3?" after "Compare Q1 and Q2"):
   - If previous query compared periods, ADD the new period to the comparison.
   - Example: Previous "Compare Q1 and Q2 2024 for Building 180" + "What about Q3?" → "Compare Q1, Q2, and Q3 2024 for Building 180"
8. For property comparison follow-ups (e.g., "What about Q1?" after "Compare Building 120 and Building 140 in 2024"):
   - KEEP the same properties from the previous query.
   - Example: Previous "Compare Building 120 and Building 140 in 2024" + "What about Q1?" → "Compare Building 120 and Building 140 in Q1 2024"
9. For P&L follow-ups (e.g., "And in 2025?" after "What is the P&L for Building 180 in 2024?"):
   - KEEP the property from history, CHANGE the timeframe.
   - Example: Previous "What is the P&L for Building 180 in 2024?" + "And in 2025?" → "What is the P&L for Building 180 in 2025?"
10. For property comparison follow-ups with pronouns (e.g., "Compare it to building 180" after "Give me the details for Building 120"):
   - REPLACE "it" with the property from the previous query.
   - Example: Previous "Give me the details for Building 120" + "Compare it to building 180" → "Compare Building 120 to Building 180"
11. Output ONLY the rewritten query. Make it COMPLETE and SELF-CONTAINED.

Rewritten query:
"""

    def _parse_response(self, response) -> str:
        text = response.content if hasattr(response, "content") else str(response)
        text = text.strip()

        lower = text.lower()
        for prefix in ["rewritten query:", "enriched query:", "query:"]:
            if lower.startswith(prefix):
                return text[len(prefix):].strip()

        return text.strip('"').strip("'")

    def _extract_context(self, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        context = {"previous_entities": [], "previous_timeframes": []}

        recent = chat_history[-2:]

        for turn in recent:
            u = turn.get("user", "").lower()

            # simple entity extraction
            import re
            for b in re.findall(r"building\s+(\d+)", u):
                context["previous_entities"].append(f"Building {b}")

            for year in ["2023", "2024", "2025"]:
                if year in u:
                    context["previous_timeframes"].append(year)

            for q in ["q1", "q2", "q3", "q4"]:
                if q in u:
                    context["previous_timeframes"].append(q.upper())

        return context
