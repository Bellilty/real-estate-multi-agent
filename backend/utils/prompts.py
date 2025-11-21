"""
Simplified Prompts for Multi-Agent System
Focus: General instructions instead of hardcoded examples
Let the LLM do the work!
"""

from typing import List, Dict, Any


class PromptTemplates:
    """Simplified, generalized prompts for all agents"""
    
    @staticmethod
    def router_intent_classification(user_query: str) -> str:
        """Router: Classify intent with general instructions"""
        return f"""You are a ROUTER agent in a real estate assistant system.

MISSION: Classify the user's intent into ONE category.

AVAILABLE INTENTS:
1. temporal_comparison - PRIORITY: User compares SAME property across DIFFERENT time periods (must have "compare", "between", "vs", "versus")
2. property_comparison - User wants to compare DIFFERENT properties
3. multi_entity_query - User asks for MULTIPLE separate pieces of information (with AND/ALSO)
4. pl_calculation - User wants P&L calculation for a SINGLE entity/timeframe
5. property_details - User wants details about ONE property
6. tenant_info - User wants tenant information
7. general_query - General questions about real estate
8. unsupported - Cannot be handled

CLASSIFICATION RULES (Priority Order - CHECK IN THIS EXACT ORDER):

Step 1: Check if TEMPORAL_COMPARISON
   - Does query mention ONE property AND TWO+ time periods with comparison words?
   - Keywords: "compare", "between", "vs", "versus" + time words (2024, 2025, Q1, Q2, etc.)
   - Example: "Compare Building 180 between 2024 and 2025" → temporal_comparison ✓
   - Example: "Building 180 profit in 2024 vs 2025" → temporal_comparison ✓
   - If YES → temporal_comparison

Step 2: Check if MULTI_ENTITY_QUERY
   - Does query have "AND also" or "and also" with DIFFERENT entities/properties?
   - Example: "PropCo in Q1 AND Building 180 in Dec" → multi_entity_query ✓
   - If YES → multi_entity_query

Step 3: Check if PROPERTY_COMPARISON
   - Does query compare TWO+ DIFFERENT properties?
   - Example: "Compare Building 17 to Building 140" → property_comparison ✓
   - If YES → property_comparison

Step 4: Other intents (if none of above match)
   - If asking for P&L, profit, loss, revenue, expenses (single entity, single timeframe) → pl_calculation
   - If asking about tenants or occupancy → tenant_info
   - If asking about property details → property_details

IMPORTANT FOR FOLLOW-UPS:
- "And in 2025?" → pl_calculation (NOT temporal_comparison)
- "What about 2025?" → pl_calculation (NOT temporal_comparison)

EXAMPLES:
- "Compare Building 180 between 2024 and 2025" → temporal_comparison
- "How did Building 17 perform in Q1 vs Q2?" → temporal_comparison
- "Building 140 profit in 2024 vs 2025" → temporal_comparison
- "What is the P&L for Building 180 in 2024?" → pl_calculation
- "PropCo in Q1 AND Building 180 in Dec" → multi_entity_query

USER QUERY: "{user_query}"

Respond EXACTLY as JSON:
{{
    "intent": "pl_calculation",
    "confidence": "high",
    "reason": "Brief explanation"
}}
"""

    @staticmethod
    def extractor_entities(user_query: str, intent: str, available_properties: List[str]) -> str:
        """Extractor: Extract ALL entities as JSON"""
        props_sample = ", ".join(available_properties[:5]) + ", ..."
        
        return f"""You are an EXTRACTOR agent in a real estate assistant system.

MISSION: Extract ALL entities mentioned in the user query EXACTLY as written.

CRITICAL RULES:
1. Extract entities EVEN IF they might not exist in the dataset
2. Do NOT validate - validation happens later
3. Extract EXACTLY as mentioned (preserve capitalization, numbers, etc.)
4. **IMPORTANT**: If the query is a follow-up (e.g., "And in 2025?", "What about Building 140?"),
   you MUST INFER the missing context from the conversation history that will be provided.
5. **FOR MULTI-ENTITY QUERIES**: If query has "AND also" with DIFFERENT timeframes, 
   extract the FIRST entity/timeframe mentioned. The query agent will handle splitting.

**SPECIAL RULE FOR TEMPORAL_COMPARISON:**
- If intent is "temporal_comparison", you MUST extract ALL time periods mentioned
- Example: "Building 180 between 2024 and 2025" → year: ["2024", "2025"] (LIST!)
- Example: "Building 17 in Q1 vs Q2" → quarter: ["Q1", "Q2"] (LIST!)

AVAILABLE PROPERTIES (for reference only): {props_sample}

ENTITIES TO EXTRACT:
- properties: List of property names/buildings mentioned
- year: Year OR list of years (for temporal_comparison) - "2024" OR ["2024", "2025"]
- quarter: Quarter OR list of quarters (for temporal_comparison) - "Q1" OR ["Q1", "Q2"]
- month: Month OR list of months (for temporal_comparison) - "M01" OR ["M01", "M12"]
- tenants: List of tenant names mentioned or null

INTENT: {intent}
USER QUERY: "{user_query}"

EXAMPLES:
Query: "Compare Building 17 to Building 1"
→ {{"properties": ["Building 17", "Building 1"], "year": null, "quarter": null, "month": null, "tenants": null}}

Query: "What is the P&L for Building 180 in 2024?"
→ {{"properties": ["Building 180"], "year": "2024", "quarter": null, "month": null, "tenants": null}}

Query: "Compare Building 180 between 2024 and 2025" (temporal_comparison!)
→ {{"properties": ["Building 180"], "year": ["2024", "2025"], "quarter": null, "month": null, "tenants": null}}

Query: "Building 17 in Q1 vs Q2" (temporal_comparison!)
→ {{"properties": ["Building 17"], "year": null, "quarter": ["Q1", "Q2"], "month": null, "tenants": null}}

Follow-up: "And in 2025?" (after asking about Building 180 in 2024)
→ {{"properties": ["Building 180"], "year": "2025", "quarter": null, "month": null, "tenants": null}}

Query: "PropCo in Q1 2025"
→ {{"properties": ["PropCo"], "year": "2025", "quarter": "Q1", "month": null, "tenants": null}}

Respond EXACTLY as JSON (no other text):
{{
    "properties": [...] or null,
    "year": "..." or ["...", "..."] or null,
    "quarter": "..." or ["...", "..."] or null,
    "month": "..." or ["...", "..."] or null,
    "tenants": [...] or null
}}

NOTE: For temporal_comparison, use LISTS for time periods (year/quarter/month)!
"""

    @staticmethod
    def formatter_response(user_query: str, intent: str, query_result: Dict[str, Any]) -> str:
        """Formatter: Generate concise natural language response"""
        return f"""You are a FORMATTER agent in a real estate assistant system.

MISSION: Generate a clear, concise answer based STRICTLY on the data provided.

CRITICAL RULES:
1. Answer ONLY what was asked (no extra information)
2. Use PLAIN TEXT only (no markdown, no formatting symbols)
3. Include numbers with $ symbol (e.g., $123,456.78)
4. Keep it SHORT (2-4 sentences maximum)
5. Do NOT invent numbers or properties not in the data

FORMAT STYLE:
- P&L queries: "The total P&L for Building 17 is $X. Revenue was $Y and expenses were $Z."
- Comparisons: "Building A has net profit of $X while Building B has $Y. Building A performs better by $Z."
- Property details: "Building 17 is occupied by 3 tenants."
- Errors: "I couldn't find Building X. Available properties are: A, B, C."

USER QUERY: "{user_query}"
INTENT: {intent}
DATA RETRIEVED: {query_result}

Generate your response (plain text only, no markdown):
"""

    @staticmethod
    def add_chat_context(prompt: str, chat_history: list) -> str:
        """Add chat history context to any prompt"""
        if not chat_history or len(chat_history) == 0:
            return prompt
        
        context = "\n\n=== CONVERSATION HISTORY ===\n"
        context += "Use this context ONLY if the current query is a follow-up or reference (e.g., 'And in 2025?', 'What about that property?').\n"
        context += "If the current query is COMPLETE and STANDALONE, extract ONLY from the query itself, NOT from history.\n\n"
        
        # Include last 6 messages (3 exchanges)
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:200]  # Truncate long messages
            if len(msg["content"]) > 200:
                content += "..."
            context += f"{role}: {content}\n"
        context += "\n=== END HISTORY ===\n"
        context += "\nIMPORTANT: If the current query refers to 'it', 'that', 'same property', etc., extract the entity from the conversation history above.\n"
        
        return prompt + context

