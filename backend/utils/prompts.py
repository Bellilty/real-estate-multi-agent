"""
Robust Prompt Templates for Multi-Agent System
Strict JSON rules + analytics_query support
"""

from typing import List, Dict, Any


class PromptTemplates:
    """Prompt templates for Router, Extractor, Formatter"""

    # ------------------------------------------------------------------
    # ROUTER PROMPT
    # ------------------------------------------------------------------
    @staticmethod
    def router_intent_classification(user_query: str) -> str:
        return f"""
You are the ROUTER agent of a real estate multi-agent system.

Your job: classify the user's intent INTO EXACTLY ONE CATEGORY.

AVAILABLE INTENTS:
1. temporal_comparison   → Compare SAME property across DIFFERENT time periods.
2. property_comparison   → Compare DIFFERENT properties.
3. multi_entity_query    → Multiple requests combined (AND / ALSO).
4. pl_calculation        → Profit, Loss, P&L for ONE entity/timeframe.
5. property_details      → Information about ONE property.
6. tenant_info           → Information about tenants / occupancy.
7. analytics_query       → Requests for: list, all items, max, min, top, bottom,
                           rankings, sorting, aggregations (sum, average).
8. general_query         → Real estate related but not fitting above.
9. unsupported           → Cannot be handled.

INTENT DECISION RULES (IN THIS ORDER):

1. TEMPORAL_COMPARISON
   - MUST contain: one property + at least two time periods + comparison word.
   - Keywords: compare, between, vs, versus.

2. MULTI_ENTITY_QUERY
   - Query requests 2+ different things (AND / ALSO).
   - Example: "PropCo in Q1 AND Building 180 in Dec".

3. PROPERTY_COMPARISON
   - Comparing different properties.

4. ANALYTICS_QUERY
   - User asks for:
     - "list all ...", "give me all ...", "show all ..." (WITHOUT specific timeframe)
     - top / bottom / max / min / highest / lowest / most / least (even WITH timeframe)
     - "highest expense category", "most profit", "which property made the most"
     - any aggregation: sum, average, count
   - Example: "List all tenants", "Give me the highest rent", "Which property made the most profit in 2024?", "highest expense category in 2024".
   - Analytics queries ask for RANKING, COMPARISON, or AGGREGATION across multiple entities.
   - NOT analytics_query if query asks for revenue/expenses/P&L for a SINGLE specific entity/timeframe (e.g., "What is the revenue for Building X in 2024").

5. P&L (pl_calculation)
   - profit, loss, P&L, revenue, expenses for a specific entity/timeframe.
   - "What is the revenue for all properties in Q1 2025?" → pl_calculation (has timeframe Q1 2025)
   - "Revenue for Building X in 2024" → pl_calculation
   - "What is the P&L for Building 180 in 2025?" → pl_calculation (follow-up enriched with property + year)
   - "All properties" can be treated as PropCo (portfolio-level).
   - If query mentions a property AND a year/quarter/month → pl_calculation (even if query is short like "And in 2025?")

6. PROPERTY_DETAILS
7. TENANT_INFO
8. GENERAL_QUERY

USER QUERY:
"{user_query}"

Respond ONLY with a JSON object:
{{
  "intent": "...",
  "confidence": "high|medium|low",
  "reason": "short explanation"
}}
"""

    # ------------------------------------------------------------------
    # EXTRACTOR PROMPT
    # ------------------------------------------------------------------
    @staticmethod
    def extractor_entities(user_query: str, intent: str, available_properties: List[str]) -> str:
        props_sample = ", ".join(available_properties[:5]) + ", ..."

        return f"""
You are the EXTRACTOR agent.

MISSION:
Extract ALL entities mentioned in the user query EXACTLY AS WRITTEN.
Do NOT validate. Extraction only.

RULES:
1. NEVER hallucinate entities.
2. Preserve original case, numbers, formatting.
3. For follow-ups: you MAY use chat history context (provided separately).
4. Extract relative dates:
   - "this year" → year: "this year"
   - "current year" → year: "current year"
   - "last year" → year: "last year"
5. For temporal_comparison:
   - If multiple years/quarters/months → RETURN LISTS, e.g. ["2024","2025"].
6. For analytics_query:
   - Extract filters if mentioned (e.g., property, tenant, year).
   - If query is generic ("list all properties"), return null for filters.
7. For tenant_info:
   - If query asks for "tenants FOR Building X" → extract property, NOT tenant.
   - If query asks for "properties OF Tenant X" → extract tenant.

AVAILABLE PROPERTIES (REFERENCE ONLY): {props_sample}

USER QUERY: "{user_query}"
INTENT: {intent}

Return ONLY JSON:
{{
  "properties": [... or null],
  "year": "...", ["...", "..."] or null,
  "quarter": "...", ["...", "..."] or null,
  "month": "...", ["...", "..."] or null,
  "tenants": [... or null]
}}
"""

    # ------------------------------------------------------------------
    # FORMATTER PROMPT
    # ------------------------------------------------------------------
    @staticmethod
    def formatter_response(user_query: str, intent: str, query_result: Dict[str, Any]) -> str:
        return f"""
You are the FORMATTER agent.

Your job: produce a SHORT, CLEAR natural language answer
STRICTLY based on the data provided.

RULES:
1. Plain text only (NO markdown).
2. 2–4 sentences max.
3. NEVER invent data or properties.
4. For analytics:
   - If listing: return clean comma-separated values.
   - If max/min: say which value and which entity.

USER QUERY: "{user_query}"
INTENT: {intent}
DATA: {query_result}

Write the final answer below:
"""

    # ------------------------------------------------------------------
    # CHAT HISTORY ADDER
    # ------------------------------------------------------------------
    @staticmethod
    def add_chat_context(prompt: str, chat_history: List[Dict[str, Any]] = None) -> str:
        if not chat_history:
            return prompt

        context = "\n\n=== CHAT HISTORY (use ONLY for references like 'it', 'that', 'same property') ===\n"
        for msg in (chat_history[-6:] if chat_history else []):
            if msg and isinstance(msg, dict):
                if "user" in msg:
                    context += f"User: {msg['user']}\n"
                if "assistant" in msg:
                    context += f"Assistant: {msg['assistant'][:200]}\n"

        context += "\n=== END HISTORY ===\n"
        return prompt + context
