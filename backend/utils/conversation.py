"""
Conversation Management for Multi-Agent System
Handles chat history, context, and follow-up questions
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """A single message in the conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ConversationContext:
    """
    Maintains conversation state and context
    Helps with follow-up questions and clarifications
    """
    messages: List[Message] = field(default_factory=list)
    last_intent: Optional[str] = None
    last_entities: Dict[str, Any] = field(default_factory=dict)
    last_query_result: Dict[str, Any] = field(default_factory=dict)
    
    def add_user_message(self, content: str, metadata: Dict[str, Any] = None):
        """Add a user message to history"""
        message = Message(
            role="user",
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
    
    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None):
        """Add an assistant message to history"""
        message = Message(
            role="assistant",
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
    
    def add_turn(self, user_query: str, intent: str, entities: Dict[str, Any], response: str):
        """
        Add a complete turn (user query + assistant response) to conversation
        
        Args:
            user_query: User's original question
            intent: Classified intent from router
            entities: Extracted entities from extractor
            response: Final assistant response
        """
        # Add user message
        self.add_user_message(user_query, metadata={"intent": intent, "entities": entities})
        
        # Add assistant response
        self.add_assistant_message(response)
        
        # Update context for next turn
        self.last_intent = intent
        self.last_entities = entities
    
    def update_context(self, intent: str, entities: Dict[str, Any], query_result: Dict[str, Any]):
        """Update context after a query"""
        self.last_intent = intent
        self.last_entities = entities
        self.last_query_result = query_result
    
    def get_recent_messages(self, n: int = 5) -> List[Message]:
        """Get the n most recent messages"""
        return self.messages[-n:] if len(self.messages) > n else self.messages
    
    def get_context_summary(self) -> str:
        """Generate a summary of recent context for LLM"""
        if not self.messages:
            return "No previous conversation"
        
        recent = self.get_recent_messages(3)
        summary_parts = []
        
        for msg in recent:
            summary_parts.append(f"{msg.role.upper()}: {msg.content[:100]}")
        
        if self.last_intent:
            summary_parts.append(f"Last intent: {self.last_intent}")
        
        if self.last_entities:
            entities_str = ", ".join([f"{k}={v}" for k, v in self.last_entities.items() if v])
            summary_parts.append(f"Last entities: {entities_str}")
        
        return "\n".join(summary_parts)
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.last_intent = None
        self.last_entities = {}
        self.last_query_result = {}
    
    def is_follow_up_question(self, query: str) -> bool:
        """
        Detect if this is a follow-up question based on context
        Examples:
        - "What about Building 180?" (after asking about Building 140)
        - "And in 2025?" (after asking about 2024)
        - "Compare them" (after mentioning two properties)
        """
        if not self.messages or len(self.messages) < 2:
            return False
        
        query_lower = query.lower()
        
        # Indicators of follow-up questions
        follow_up_indicators = [
            "what about",
            "how about",
            "and",
            "also",
            "compare them",
            "what's the difference",
            "which one",
            "between them",
            "and for",
            "same for",
            "but you said",
            "you said",
        ]
        
        # Check for pronouns or references
        pronouns = ["it", "them", "that", "this", "these", "those"]
        
        for indicator in follow_up_indicators:
            if indicator in query_lower:
                return True
        
        for pronoun in pronouns:
            if f" {pronoun} " in f" {query_lower} ":
                return True
        
        return False
    
    def resolve_references(self, query: str) -> str:
        """
        Resolve references in follow-up questions using context
        Example: "And in 2025?" → "What is the P&L for Building 180 in 2025?"
        
        NOW ALWAYS TRIES TO RESOLVE, NOT JUST FOR DETECTED FOLLOW-UPS
        """
        query_lower = query.lower()
        resolved_query = query
        
        # If we have NO context, just return the original query
        if not self.last_entities or not self.last_intent:
            return query
        
        # Extract context
        property_name = self.last_entities.get("property")
        entity_name = self.last_entities.get("entity")  # e.g. PropCo
        scope = entity_name or property_name or "all properties"
            
        # ==== 1) Tenant-related follow‑ups after a property_details or P&L answer ====
        # e.g. "which tenants?", "wich tenants?", "is this all you know?"
        if property_name and any(kw in query_lower for kw in ["tenant", "tenants"]):
            resolved_query = f"Show me the details for {property_name}, especially the tenants."
            return resolved_query
            
        # ==== 2) Temporal follow‑up "Q1 vs Q2" or "what about Q2" based on previous P&L / PropCo ====
        if self.last_intent in ["pl_calculation", "temporal_comparison"]:
                has_q1 = "q1" in query_lower
                has_q2 = "q2" in query_lower
                has_q3 = "q3" in query_lower
                has_q4 = "q4" in query_lower
                
                # Broader comparison indicators
                mentions_compare = any(word in query_lower for word in [
                    "compare", "vs", "versus", "between", "comparison", "then compare"
                ])
                
                # Special case: "And what about Q2 2025? Then compare Q1 vs Q2."
                # This is TWO questions in one: first asking about Q2, then comparing.
                # We should treat this as a comparison request.
                if (has_q1 and has_q2) or mentions_compare:
                    # Try to infer year from current query, else fall back to last_entities
                    year = None
                    for y in ["2024", "2025"]:
                        if y in query_lower:
                            year = y
                            break
                    if not year:
                        # Try to use last known year or quarter
                        year = self.last_entities.get("year")
                        last_quarter = self.last_entities.get("quarter")
                        if not year and last_quarter and "-" in last_quarter:
                            year = last_quarter.split("-")[0]
                    
                    # Determine which quarters to compare
                    if has_q1 and has_q2 and year:
                        resolved_query = (
                            f"Compare the net profit for {scope} between {year}-Q1 and {year}-Q2."
                        )
                        return resolved_query
                    elif has_q3 and has_q4 and year:
                        resolved_query = (
                            f"Compare the net profit for {scope} between {year}-Q3 and {year}-Q4."
                        )
                        return resolved_query
                
                # Simple "what about Q2 2025?" style follow‑up (no comparison)
                if (has_q2 or has_q3 or has_q4) and not mentions_compare:
                    year = None
                    for y in ["2024", "2025"]:
                        if y in query_lower:
                            year = y
                            break
                    if not year:
                        year = self.last_entities.get("year")
                    
                    quarter_num = "2" if has_q2 else ("3" if has_q3 else "4")
                    if year:
                        resolved_query = f"What is the P&L for {scope} in {year}-Q{quarter_num}?"
                        return resolved_query
            
        # ==== 3) Extend previous property comparison with "include Building X" ====
        if self.last_intent == "property_comparison":
                props = self.last_entities.get("properties", []) or []
                
                if any(word in query_lower for word in ["include", "add", "plus", "as well"]):
                    # Find any "Building XXX" mentions in the new query
                    import re
                    new_buildings = re.findall(r'[Bb]uilding\s+\d+', query)
                    # Normalise spacing/case
                    new_buildings = [b.strip() for b in new_buildings]
                    
                    # Merge with previous list, keeping order and uniqueness
                    all_props: list[str] = []
                    for p in props + new_buildings:
                        if p and p not in all_props:
                            all_props.append(p)
                    
                    # Try to infer year if mentioned
                    year = None
                    for y in ["2024", "2025"]:
                        if y in query_lower:
                            year = y
                            break
                    
                    # Build an explicit ranking/comparison query
                    if all_props:
                        props_str = ", ".join(all_props[:-1]) + f" and {all_props[-1]}" if len(all_props) > 1 else all_props[0]
                        if year:
                            resolved_query = (
                                f"Compare the net profit of {props_str} in {year} and rank them from best to worst."
                            )
                        else:
                            resolved_query = (
                                f"Compare the net profit of {props_str} and rank them from best to worst."
                            )
                        return resolved_query
            
        # ==== 4) Vague calculation follow-ups like "What's the net result?" ====
        if self.last_intent == "pl_calculation":
                # Keywords that indicate user wants a calculation on the same scope
                calc_keywords = ["net result", "net profit", "total", "result", "profit", "loss"]
                if any(kw in query_lower for kw in calc_keywords):
                    # Check if there's already a property/year mentioned in the new query
                    has_building = "building" in query_lower
                    has_year = any(y in query_lower for y in ["2024", "2025"])
                    
                    # If not, use the previous context
                    if not has_building and not has_year:
                        year = self.last_entities.get("year")
                        if property_name:
                            resolved_query = f"What is the net profit for {property_name} in {year}?" if year else f"What is the net profit for {property_name}?"
                        elif entity_name:
                            resolved_query = f"What is the net profit for {entity_name} in {year}?" if year else f"What is the net profit for {entity_name}?"
                        else:
                            # Keep original if we can't infer context
                            pass
                        return resolved_query
            
        # ==== 5) If query starts with "And" or "Also", construct full query (generic) ====
        if query_lower.startswith(("and ", "also ")):
                # Extract what's after "and/also"
                remaining = query[query.find(" ") + 1:].strip()
                
                # Reconstruct query based on previous intent
                if self.last_intent == "pl_calculation" and property_name:
                    # "and in 2025?" → "What is the P&L for Building 180 in 2025?"
                    resolved_query = f"What is the P&L for {property_name} {remaining}?"
                elif property_name:
                    resolved_query = f"{remaining} for {property_name}"
                else:
                    resolved_query = f"{remaining}"
            
        # ==== 6) Handle "What about X?" queries ====
        if "what about" in query_lower:
                # If asking "what about Building 999?" after a comparison, try to extend the comparison
                if self.last_intent == "property_comparison":
                    import re
                    mentioned_buildings = re.findall(r'[Bb]uilding\s+\d+', query)
                    if mentioned_buildings:
                        props = self.last_entities.get("properties", [])
                        year = self.last_entities.get("year") or "2024"
                        
                        # Build a new comparison query
                        new_building = mentioned_buildings[0]
                        if props:
                            all_props = props + [new_building]
                            props_str = ", ".join(all_props[:-1]) + f" and {all_props[-1]}"
                            resolved_query = f"Compare the net profit of {props_str} in {year}."
                            return resolved_query
        
        return resolved_query
    
    def to_dict(self) -> Dict[str, Any]:
        """Export conversation to dictionary"""
        return {
            "messages": [msg.to_dict() for msg in self.messages],
            "last_intent": self.last_intent,
            "last_entities": self.last_entities,
            "last_query_result": self.last_query_result
        }


class ConversationManager:
    """Manages multiple conversation contexts (for different users/sessions)"""
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
    
    def get_context(self, session_id: str) -> ConversationContext:
        """Get or create a conversation context for a session"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext()
        return self.contexts[session_id]
    
    def clear_context(self, session_id: str):
        """Clear a specific conversation context"""
        if session_id in self.contexts:
            self.contexts[session_id].clear()
    
    def clear_all(self):
        """Clear all conversation contexts"""
        self.contexts = {}

