"""
FollowUp Resolver Agent - First Node in Graph
Detects and resolves follow-up questions using conversation context
"""

import time
from typing import Dict, Any, List, Optional


class FollowUpResolverAgent:
    """
    Intelligent follow-up resolution agent
    
    Responsibilities:
    1. Detect if query is a follow-up
    2. Extract missing context from chat history
    3. Rewrite query to be self-contained
    4. Tag query metadata for downstream agents
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def process(
        self, 
        user_query: str, 
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process query to detect and resolve follow-ups
        
        Returns:
        {
            "status": "ok" | "error",
            "is_followup": bool,
            "updated_query": str,
            "original_query": str,
            "context_used": dict,
            "notes": str,
            "needs_clarification": bool,
            "duration_ms": int
        }
        """
        start_time = time.time()
        
        # If no history, it's not a follow-up
        if not chat_history or len(chat_history) == 0:
            return {
                "status": "ok",
                "is_followup": False,
                "updated_query": user_query,
                "original_query": user_query,
                "context_used": {},
                "notes": "No chat history available",
                "needs_clarification": False,
                "duration_ms": int((time.time() - start_time) * 1000)
            }
        
        # Detect follow-up indicators
        followup_indicators = [
            "and what about", "what about", "how about",
            "and for", "also for", "same for",
            "compare to", "versus", "vs",
            "in that case", "then",
            "both", "all of them", "those",
            "it", "its", "that", "this", "these", "those",
            "and", "also", "too", "as well"
        ]
        
        query_lower = user_query.lower().strip()
        has_indicator = any(ind in query_lower for ind in followup_indicators)
        
        # If very short or has indicators, likely a follow-up
        is_short = len(user_query.split()) <= 5
        likely_followup = has_indicator or (is_short and len(chat_history) > 0)
        
        if not likely_followup:
            return {
                "status": "ok",
                "is_followup": False,
                "updated_query": user_query,
                "original_query": user_query,
                "context_used": {},
                "notes": "Query appears self-contained",
                "needs_clarification": False,
                "duration_ms": int((time.time() - start_time) * 1000)
            }
        
        # Build enrichment prompt
        prompt = self._build_enrichment_prompt(user_query, chat_history)
        
        try:
            # Call LLM to enrich query
            response = self.llm.invoke(prompt)
            
            # Extract enriched query
            enriched_query = self._parse_response(response)
            
            # Extract context used
            context_used = self._extract_context(chat_history)
            
            duration_ms = int((time.time() - start_time) * 1000)            
            return {
                "status": "ok",
                "is_followup": True,
                "updated_query": enriched_query,
                "original_query": user_query,
                "context_used": context_used,
                "notes": f"Follow-up detected, enriched with context from {len(chat_history)} previous turns",
                "needs_clarification": False,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)            
            # Fallback: return original query
            return {
                "status": "error",
                "is_followup": likely_followup,
                "updated_query": user_query,
                "original_query": user_query,
                "context_used": {},
                "notes": f"Enrichment failed: {e}",
                "needs_clarification": False,
                "duration_ms": duration_ms,
                "error": str(e)
            }
    
    def _build_enrichment_prompt(
        self, 
        user_query: str, 
        chat_history: List[Dict[str, str]]
    ) -> str:
        """Build prompt for query enrichment"""
        
        # Get last 3 turns
        recent_history = chat_history[-3:] if len(chat_history) > 3 else chat_history
        
        history_text = ""
        for i, turn in enumerate(recent_history, 1):
            user_msg = turn.get('user', turn.get('role') == 'user' and turn.get('content', ''))
            assistant_msg = turn.get('assistant', turn.get('role') == 'assistant' and turn.get('content', ''))
            
            if user_msg:
                history_text += f"User: {user_msg}\n"
            if assistant_msg:
                history_text += f"Assistant: {assistant_msg[:200]}...\n\n"
        
        prompt = f"""You are a follow-up query resolver.

TASK: Rewrite the user's current query to be SELF-CONTAINED by adding missing context from chat history.

CHAT HISTORY:
{history_text}

CURRENT USER QUERY: "{user_query}"

RULES:
1. If query references "it", "that", "them" → replace with actual entity names
2. If query says "and what about X" → make it "What is the P&L for X" (with timeframe if needed)
3. If query says "compare to Y" → make it "Compare [previous entity] to Y"
4. Preserve the user's intent and requested information
5. Add missing timeframes if they were in previous queries
6. Output ONLY the rewritten query, nothing else

REWRITTEN QUERY:"""
        
        return prompt
    
    def _parse_response(self, response) -> str:
        """Parse LLM response to extract enriched query"""
        # Extract content from AIMessage
        if hasattr(response, 'content'):
            text = response.content
        else:
            text = str(response)
        
        # Clean up
        text = text.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "rewritten query:",
            "enriched query:",
            "self-contained query:",
            "query:",
        ]
        
        text_lower = text.lower()
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        
        # Remove quotes if present
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        
        return text
    
    def _extract_context(self, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract key context from chat history"""
        context = {
            "previous_entities": [],
            "previous_timeframes": [],
            "previous_intents": []
        }
        
        # Get last 2 turns
        recent = chat_history[-2:] if len(chat_history) > 2 else chat_history
        
        for turn in recent:
            user_msg = turn.get('user', turn.get('content', ''))
            
            # Extract entities (simple heuristic)
            if 'building' in user_msg.lower():
                import re
                buildings = re.findall(r'building\s+(\d+)', user_msg.lower())
                context["previous_entities"].extend([f"Building {b}" for b in buildings])
            
            if 'tenant' in user_msg.lower():
                import re
                tenants = re.findall(r'tenant\s+(\d+)', user_msg.lower())
                context["previous_entities"].extend([f"Tenant {t}" for t in tenants])
            
            # Extract timeframes
            if '2024' in user_msg:
                context["previous_timeframes"].append("2024")
            if '2025' in user_msg:
                context["previous_timeframes"].append("2025")
            if 'q1' in user_msg.lower():
                context["previous_timeframes"].append("Q1")
            if 'q2' in user_msg.lower():
                context["previous_timeframes"].append("Q2")
        
        return context

