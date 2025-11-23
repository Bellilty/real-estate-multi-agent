"""
INTELLIGENT MULTI-AGENT ORCHESTRATOR
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict, List, Literal, Tuple
import time

# Import all agents
from backend.agents.followup_resolver import FollowUpResolverAgent
from backend.agents.router import IntentRouter
from backend.agents.extractor import EntityExtractor
from backend.agents.naturaldate_agent import NaturalDateAgent
from backend.agents.validation_agent import ValidationAgent
from backend.agents.disambiguation_agent import DisambiguationAgent
from backend.agents.query import QueryAgent  # ✅ use clean QueryAgent
from backend.agents.formatter import ResponseFormatter
from backend.utils.tracking import ChainOfThoughtTracker


class IntelligentWorkflowState(TypedDict):
    """Enhanced state for intelligent workflow"""
    # Input
    user_query: str
    original_query: str
    chat_history: List[Dict[str, str]]
    
    # Follow-up resolution
    is_followup: bool
    updated_query: str
    clear_timeframes: bool
    
    # Intent & Entities
    intent: str
    confidence: str
    entities: Dict[str, Any]
    
    # Validation routing
    validation_status: Literal["ok", "missing", "ambiguous"]
    missing_fields: List[str]
    ambiguous_entities: Dict[str, Any]
    
    # Disambiguation
    disambiguation_result: Dict[str, Any]
    
    # Query execution
    query_result: Dict[str, Any]
    
    # Response
    final_response: str
    
    # Metadata
    loop_count: int
    agent_path: List[str]
    clarifications_requested: int
    debug_mode: bool


class RealEstateOrchestrator:
    """
    🧠 INTELLIGENT MULTI-AGENT ORCHESTRATOR
    
    ARCHITECTURE:
    
    FollowUpResolver → Router → Extractor → NaturalDate → Validation
                                                              ↓
                                                    ┌─────────┼─────────┐
                                                    ↓         ↓         ↓
                                                 MISSING  AMBIGUOUS   VALID
                                                    ↓         ↓         ↓
                                               Clarifier  Disambig   Query
                                                    ↓         ↓         ↓
                                                  END      Query    Formatter
                                                            ↓         ↓
                                                        Formatter    END
                                                            ↓
                                                           END
    
    ✅ FOLLOW-UP DETECTION
    ✅ NATURAL DATE PARSING
    ✅ 3-WAY VALIDATION ROUTING
    ✅ DISAMBIGUATION
    ✅ AGENT PATH TRACKING
    """
    
    def __init__(self, llm, data_loader, debug_mode: bool = False):
        """
        Initialize orchestrator with all agents
        
        Args:
            llm: LLM instance (ChatOpenAI or compatible)
            data_loader: Data loader instance
            debug_mode: Enable debug prints
        """
        self.llm = llm
        self.data_loader = data_loader
        self.debug_mode = debug_mode
        
        # Initialize all agents
        available_properties = data_loader.get_properties()
        
        self.followup_resolver = FollowUpResolverAgent(llm)
        self.router = IntentRouter(llm)
        self.extractor = EntityExtractor(llm, available_properties)
        self.naturaldate_agent = NaturalDateAgent()
        self.validation_agent = ValidationAgent(data_loader)
        self.disambiguation_agent = DisambiguationAgent(data_loader)
        self.query_agent = QueryAgent(data_loader)  # ✅ clean query layer
        self.formatter = ResponseFormatter(llm)
        
        # Build workflow
        self.workflow = self._build_graph()
        
        # Tracker for current execution
        self.current_tracker = None
    
    def _build_graph(self) -> StateGraph:
        """Build the intelligent graph"""
        workflow = StateGraph(IntelligentWorkflowState)
        
        # === NODES ===
        workflow.add_node("followup_resolver", self._followup_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("extractor", self._extractor_node)
        workflow.add_node("naturaldate", self._naturaldate_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("disambiguation", self._disambiguation_node)
        workflow.add_node("query", self._query_node)
        workflow.add_node("formatter", self._formatter_node)
        workflow.add_node("clarification", self._clarification_node)
        
        # === EDGES ===
        workflow.set_entry_point("followup_resolver")
        workflow.add_edge("followup_resolver", "router")
        workflow.add_edge("router", "extractor")
        workflow.add_edge("extractor", "naturaldate")
        workflow.add_edge("naturaldate", "validation")
        
        # === CONDITIONAL ROUTING ===
        workflow.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {
                "ok": "query",
                "missing": "clarification",
                "ambiguous": "disambiguation"
            }
        )
        
        workflow.add_conditional_edges(
            "disambiguation",
            self._route_after_disambiguation,
            {
                "resolved": "query",
                "needs_clarification": "clarification"
            }
        )
        
        workflow.add_edge("query", "formatter")
        workflow.add_edge("clarification", "formatter")
        workflow.add_edge("formatter", END)
        
        return workflow.compile()
    
    # === ROUTING FUNCTIONS ===
    
    def _route_after_validation(self, state: IntelligentWorkflowState) -> str:
        """Route based on validation status"""
        return state.get("validation_status", "ok")
    
    def _route_after_disambiguation(self, state: IntelligentWorkflowState) -> str:
        """Route after disambiguation"""
        disambiguation_result = state.get("disambiguation_result", {})
        needs_clarification = disambiguation_result.get("needs_clarification", False)
        return "needs_clarification" if needs_clarification else "resolved"
    
    # === NODE IMPLEMENTATIONS ===
    
    def _followup_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 1: Resolve follow-up questions"""
        result = self.followup_resolver.process(
            state["user_query"],
            state.get("chat_history", [])
        )
        
        state["is_followup"] = result["is_followup"]
        state["updated_query"] = result["updated_query"]
        
        # Check if we need to clear timeframes (for "overall" queries)
        context_used = result.get("context_used", {})
        if context_used.get("clear_timeframes"):
            state["clear_timeframes"] = True
        
        state["agent_path"].append("FollowUpResolver")
        
        # Track this step
        self.current_tracker.add_step(
            agent="FollowUpResolver",
            action="resolve_followup",
            input_data={"query": state["user_query"]},
            output_data={
                "is_followup": result["is_followup"],
                "clear_timeframes": state.get("clear_timeframes", False)
            },
            reasoning=result.get("notes", ""),
            duration_ms=result["duration_ms"],
            success=result["status"] == "ok"
        )
        
        return state
    
    def _router_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 2: Route intent"""
        query_to_route = state["updated_query"] if state["is_followup"] else state["user_query"]
        
        result = self.router.classify_intent(query_to_route, state.get("chat_history", []))
        
        state["intent"] = result["intent"]
        state["confidence"] = result["confidence"]
        state["agent_path"].append("Router")
        
        # Track this step
        self.current_tracker.add_step(
            agent="Router",
            action="classify_intent",
            input_data={"query": query_to_route},
            output_data={
                "intent": result["intent"],
                "confidence": result["confidence"]
            },
            reasoning=result.get("reason", ""),
            duration_ms=result.get("duration_ms", 0),
            success=True
        )
        
        return state
    
    def _extractor_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 3: Extract entities"""
        query_to_extract = state["updated_query"] if state["is_followup"] else state["user_query"]
        
        result = self.extractor.extract_entities(
            query_to_extract,
            state["intent"],
            state.get("chat_history", [])
        )
        
        state["entities"] = result.get("entities", {})
        # Store raw query for analytics queries that need it
        if state["intent"] == "analytics_query":
            state["entities"]["raw_query"] = query_to_extract
        
        # If clear_timeframes flag is set, remove all time-related entities
        if state.get("clear_timeframes"):
            state["entities"].pop("year", None)
            state["entities"].pop("quarter", None)
            state["entities"].pop("month", None)
            state["entities"].pop("periods", None)
        
        state["agent_path"].append("Extractor")
        
        # Track this step
        self.current_tracker.add_step(
            agent="Extractor",
            action="extract_entities",
            input_data={"query": query_to_extract, "intent": state["intent"]},
            output_data=result.get("entities", {}),
            reasoning=(
                f"Extracted entities for {state['intent']}"
                + (" (timeframes cleared for overall query)" if state.get("clear_timeframes") else "")
            ),
            duration_ms=result.get("duration_ms", 0),
            success=result["success"]
        )
        
        return state
    
    def _naturaldate_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 4: Parse and normalize dates"""
        query_for_context = state["updated_query"] if state["is_followup"] else state["user_query"]
        
        result = self.naturaldate_agent.process(
            state["entities"],
            query_for_context
        )
        
        state["entities"] = result["entities"]
        
        # For temporal_comparison: Update periods with normalized quarters
        if state.get("intent") == "temporal_comparison":
            if isinstance(state["entities"].get("quarter"), list):
                # Quarters are now normalized to "2024-Q1" format
                state["entities"]["periods"] = state["entities"]["quarter"]
        
        # If clear_timeframes flag is set, remove time entities again
        if state.get("clear_timeframes"):
            state["entities"].pop("year", None)
            state["entities"].pop("quarter", None)
            state["entities"].pop("month", None)
            state["entities"].pop("periods", None)
        
        state["agent_path"].append("NaturalDateAgent")
        
        # Track this step
        self.current_tracker.add_step(
            agent="NaturalDateAgent",
            action="parse_dates",
            input_data={"entities": state["entities"]},
            output_data={"normalized": result["entities"]},
            reasoning=result.get("notes", "") + (
                " (timeframes cleared for overall query)" if state.get("clear_timeframes") else ""
            ),
            duration_ms=result["duration_ms"],
            success=result["status"] == "ok"
        )
        
        return state
    
    def _validation_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 5: Validate entities (3-way routing)"""
        result = self.validation_agent.validate(
            state["intent"],
            state["entities"]
        )
        
        # ✅ use validated entities for QueryAgent
        state["entities"] = result.get("entities", state["entities"])
        
        state["validation_status"] = result["status"]
        state["missing_fields"] = result.get("missing_fields", [])
        state["ambiguous_entities"] = result.get("ambiguous_entities", {})
        state["agent_path"].append("ValidationAgent")
        
        # Track this step
        self.current_tracker.add_step(
            agent="ValidationAgent",
            action="validate_entities",
            input_data={"intent": state["intent"], "entities": state["entities"]},
            output_data={"status": result["status"]},
            reasoning=result.get("notes", ""),
            duration_ms=result["duration_ms"],
            success=True
        )
        
        return state
    
    def _disambiguation_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 6: Disambiguate ambiguous entities"""
        result = self.disambiguation_agent.process(
            state["entities"],
            state["ambiguous_entities"]
        )
        
        if result["status"] == "ok":
            state["entities"] = result["entities"]
        
        state["disambiguation_result"] = result
        state["agent_path"].append("DisambiguationAgent")
        
        # Track this step
        self.current_tracker.add_step(
            agent="DisambiguationAgent",
            action="disambiguate",
            input_data={"ambiguous": state["ambiguous_entities"]},
            output_data={"resolved": result["status"] == "ok"},
            reasoning=result.get("notes", ""),
            duration_ms=result["duration_ms"],
            success=True
        )
        
        return state
    
    def _clarification_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 7: Handle clarification requests"""
        state["clarifications_requested"] += 1
        
        # Build detailed clarification message with available options
        clarification_parts: List[str] = []
        invalid_entities: Dict[str, Any] = {}
        suggestions: Dict[str, Any] = {}
        
        # Parse missing fields to extract entity names
        missing_fields = state.get("missing_fields") or []
        if missing_fields:
            for field in missing_fields:
                if "property:" in field:
                    prop_name = field.replace("property:", "").strip()
                    invalid_entities.setdefault("property", []).append(prop_name)
                    suggestions["property"] = self.data_loader.get_properties()[:10]
                elif "tenant:" in field:
                    tenant_name = field.replace("tenant:", "").strip()
                    invalid_entities.setdefault("tenant", []).append(tenant_name)
                    suggestions["tenant"] = self.data_loader.get_tenants()[:10]
                else:
                    clarification_parts.append(f"Missing: {field}")
        
        # Handle disambiguation results
        disambiguation_result = state.get("disambiguation_result", {})
        if disambiguation_result.get("clarification_message"):
            clarification_parts.append(disambiguation_result["clarification_message"])
        
        if not clarification_parts and not invalid_entities:
            clarification_parts.append("I need more information to process your request.")
        
        state["query_result"] = {
            "error": "clarification_needed",
            "clarification_message": " ".join(clarification_parts) if clarification_parts else "",
            "invalid_entities": invalid_entities,
            "suggestions": suggestions,
            "missing_fields": state.get("missing_fields", []),
            "ambiguous_entities": state.get("ambiguous_entities", {})
        }
        
        state["agent_path"].append("ClarificationHandler")
        
        # Track this step
        self.current_tracker.add_step(
            agent="ClarificationHandler",
            action="request_clarification",
            input_data={"missing": state["missing_fields"]},
            output_data={"message": " ".join(clarification_parts)[:100]},
            reasoning="Clarification needed",
            duration_ms=0,
            success=True
        )
        
        return state
    
    def _query_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 8: Execute query"""
        # Add user query to entities for analytics queries
        entities = state["entities"].copy()
        if state["intent"] == "analytics_query":
            entities["raw_query"] = state["updated_query"] if state["is_followup"] else state["user_query"]
        
        # ✅ QueryAgent.run(intent, entities) → dict (includes duration_ms)
        result = self.query_agent.run(
            state["intent"],
            entities
        )
        
        # Include raw_query in result for analytics queries (needed by formatter)
        if state["intent"] == "analytics_query" and "raw_query" in entities:
            result["raw_query"] = entities["raw_query"]
        
        duration_ms = result.get("duration_ms", 0)
        state["query_result"] = result
        state["agent_path"].append("QueryAgent")
        
        # Track this step
        self.current_tracker.add_step(
            agent="Query",
            action="execute_query",
            input_data={"intent": state["intent"], "entities": state["entities"]},
            output_data={"fields_count": len(result)},
            reasoning="Retrieved data",
            duration_ms=int(duration_ms),
            success="error" not in result
        )
        
        return state
    
    def _formatter_node(self, state: IntelligentWorkflowState) -> IntelligentWorkflowState:
        """Node 9: Format response"""
        result = self.formatter.format_response(
            state["original_query"],
            state["intent"],
            state["query_result"]
        )
        
        state["final_response"] = result.get("response", "")
        state["agent_path"].append("Formatter")
        
        # Track this step
        self.current_tracker.add_step(
            agent="Formatter",
            action="format_response",
            input_data={"intent": state["intent"]},
            output_data={"response_length": len(state["final_response"])},
            reasoning="Formatted response",
            duration_ms=result.get("duration_ms", 0),
            success=True
        )
        
        return state
    
    def run(
        self, 
        user_query: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Tuple[str, ChainOfThoughtTracker]:
        """
        Run the intelligent multi-agent workflow
        
        Args:
            user_query: User's question
            chat_history: Previous conversation
            
        Returns:
            (final_response, tracker)
        """
        print(f"\n[ORCHESTRATOR] ==== New query received ====")
        print(f"[ORCHESTRATOR] User query: {user_query}")
        
        # Handle empty query
        if not user_query or not user_query.strip():
            error_response = "Please provide a valid query. I can help you with P&L calculations, property comparisons, and more."
            self.current_tracker = ChainOfThoughtTracker()
            self.current_tracker.start_tracking()
            self.current_tracker.add_step(
                agent="Orchestrator",
                action="empty_query_handling",
                input_data={"query": user_query},
                output_data={"error": "Empty query"},
                reasoning="Query was empty or whitespace only",
                duration_ms=0,
                success=False,
                error="Empty query"
            )
            return error_response, self.current_tracker
        
        # Initialize tracker
        self.current_tracker = ChainOfThoughtTracker()
        self.current_tracker.start_tracking()
        
        # Prepare initial state
        initial_state: IntelligentWorkflowState = {
            "user_query": user_query,
            "original_query": user_query,
            "chat_history": chat_history or [],
            "is_followup": False,
            "updated_query": user_query,
            "clear_timeframes": False,       # ✅ init flag
            "intent": "",
            "confidence": "",
            "entities": {},
            "validation_status": "ok",
            "missing_fields": [],
            "ambiguous_entities": {},
            "disambiguation_result": {},
            "query_result": {},
            "final_response": "",
            "loop_count": 0,
            "agent_path": [],
            "clarifications_requested": 0,
            "debug_mode": self.debug_mode
        }
        
        try:
            # Run workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Extract response
            response = final_state.get("final_response", "")
            
            print(f"\n[ORCHESTRATOR] ---- Final state ----")
            print(f"[ORCHESTRATOR] Intent: {final_state.get('intent')}, confidence: {final_state.get('confidence')}")
            print(f"[ORCHESTRATOR] Entities: {final_state.get('entities')}")
            agent_path = final_state.get('agent_path') or []
            print(f"[ORCHESTRATOR] Agent Path: {' → '.join(agent_path) if agent_path else 'None'}")
            print(f"[ORCHESTRATOR] Final response: {response[:100] if response else 'None'}...")
            print(f"[ORCHESTRATOR] ==============================\n")
            
            return response, self.current_tracker
            
        except Exception as e:
            print(f"\n[ORCHESTRATOR] ERROR: {e}")
            error_response = f"❌ An error occurred: {str(e)}\n\nPlease try again."
            
            self.current_tracker.add_step(
                agent="Orchestrator",
                action="error_handling",
                input_data={"query": user_query},
                output_data={"error": str(e)},
                reasoning="Fatal error in workflow",
                duration_ms=0,
                success=False,
                error=str(e)
            )
            
            return error_response, self.current_tracker
