"""
Orchestrator v3 - Simplified Multi-Agent System
Uses the new JSON-based agents
"""

from typing import Dict, Any, List, Tuple
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.router import IntentRouter
from agents.extractor import EntityExtractor
from agents.query import EnhancedQueryAgent
from agents.formatter import ResponseFormatter
from llm.llm_client import LLMClient
from data.data_loader import RealEstateDataLoader
from utils.tracking import ChainOfThoughtTracker


class WorkflowState(TypedDict):
    """State passed between agents"""
    user_query: str
    chat_history: List[Dict[str, str]]
    intent: str
    confidence: str
    entities: Dict[str, Any]
    query_result: Dict[str, Any]
    final_response: str
    error: str


class RealEstateOrchestrator:
    """
    Simplified orchestrator using JSON-based agents
    """
    
    def __init__(self, llm_client: LLMClient, data_loader: RealEstateDataLoader):
        self.llm = llm_client
        self.data_loader = data_loader
        
        # Initialize agents
        available_properties = data_loader.get_properties()
        
        self.router = IntentRouter(llm_client)
        self.extractor = EntityExtractor(llm_client, available_properties)
        self.query_agent = EnhancedQueryAgent(data_loader)
        self.formatter = ResponseFormatter(llm_client)
        
        # Build workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("router", self._route_intent)
        workflow.add_node("extractor", self._extract_entities)
        workflow.add_node("query", self._execute_query)
        workflow.add_node("formatter", self._format_response)
        workflow.add_node("fallback", self._handle_fallback)
        
        # Set entry point
        workflow.set_entry_point("router")
        
        # Add edges
        workflow.add_conditional_edges(
            "router",
            self._should_proceed,
            {
                "continue": "extractor",
                "fallback": "fallback"
            }
        )
        
        workflow.add_edge("extractor", "query")
        
        workflow.add_conditional_edges(
            "query",
            self._should_format_or_fallback,
            {
                "format": "formatter",
                "fallback": "fallback"
            }
        )
        
        workflow.add_edge("formatter", END)
        workflow.add_edge("fallback", END)
        
        return workflow.compile()
    
    def run(
        self, 
        user_query: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Tuple[str, ChainOfThoughtTracker]:
        """
        Run the multi-agent workflow
        
        Args:
            user_query: User's question
            chat_history: Previous conversation
            
        Returns:
            (final_response, tracker)
        """
        print(f"\n[ORCHESTRATOR] ==== New query received ====")
        print(f"[ORCHESTRATOR] User query: {user_query}")
        
        # Initialize tracker (store as instance variable so nodes can access it)
        self.current_tracker = ChainOfThoughtTracker()
        self.current_tracker.start_tracking()
        
        # Initialize state
        initial_state = {
            "user_query": user_query,
            "chat_history": chat_history or [],
            "intent": "",
            "confidence": "",
            "entities": {},
            "query_result": {},
            "final_response": "",
            "error": ""
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print(f"\n[ORCHESTRATOR] ---- Final state ----")
        print(f"[ORCHESTRATOR] Intent: {final_state.get('intent')}, confidence: {final_state.get('confidence')}")
        print(f"[ORCHESTRATOR] Entities: {final_state.get('entities')}")
        print(f"[ORCHESTRATOR] Error: {final_state.get('error')}")
        print(f"[ORCHESTRATOR] Final response: {final_state.get('final_response', '')[:100]}...")
        print(f"[ORCHESTRATOR] ==============================\n")
        
        return final_state.get("final_response", ""), self.current_tracker
    
    def _route_intent(self, state: WorkflowState) -> WorkflowState:
        """Router node"""
        print(f"\n[ROUTER] ---- Router called ----")
        print(f"[ROUTER] User query: {state['user_query']}")
        
        result = self.router.classify_intent(
            state["user_query"],
            state.get("chat_history")
        )
        
        print(f"[ROUTER] Intent: {result['intent']}, confidence: {result['confidence']}")
        print(f"[ROUTER] Reason: {result.get('reason', 'N/A')}")
        print(f"[ROUTER] Duration: {result.get('duration_ms', 0)} ms\n")
        
        state["intent"] = result["intent"]
        state["confidence"] = result["confidence"]
        
        # Track this step
        self.current_tracker.add_step(
            agent="Router",
            action="classify_intent",
            input_data={"query": state["user_query"]},
            output_data={"intent": result["intent"], "confidence": result["confidence"]},
            reasoning=f"Classified as '{result['intent']}' with {result['confidence']} confidence. {result.get('reason', '')}",
            duration_ms=result.get("duration_ms", 0),
            success=True
        )
        
        return state
    
    def _extract_entities(self, state: WorkflowState) -> WorkflowState:
        """Extractor node"""
        print(f"\n[EXTRACTOR] ---- Extractor called ----")
        print(f"[EXTRACTOR] Intent: {state['intent']}")
        print(f"[EXTRACTOR] User query: {state['user_query']}")
        
        result = self.extractor.extract_entities(
            state["user_query"],
            state["intent"],
            state.get("chat_history")
        )
        
        print(f"[EXTRACTOR] Success: {result['success']}")
        print(f"[EXTRACTOR] Entities: {result.get('entities', {})}")
        print(f"[EXTRACTOR] Duration: {result.get('duration_ms', 0)} ms\n")
        
        if result["success"]:
            state["entities"] = result["entities"]
            
            # Track this step
            entities = result["entities"]
            if state["intent"] == "property_comparison":
                props = entities.get("properties", [])
                desc = f"Extracted {len(props)} properties for comparison: {', '.join(props)}"
            elif state["intent"] == "pl_calculation":
                prop = entities.get("properties", ["None"])[0] if entities.get("properties") else "None"
                year = entities.get("year", "None")
                desc = f"Extracted P&L parameters: Property={prop}, Year={year}"
            else:
                desc = f"Extracted entities: {list(entities.keys())}"
            
            self.current_tracker.add_step(
                agent="Extractor",
                action="extract_entities",
                input_data={"query": state["user_query"], "intent": state["intent"]},
                output_data=entities,
                reasoning=desc,
                duration_ms=result.get("duration_ms", 0),
                success=True
            )
        else:
            state["error"] = "Failed to extract entities"
            print(f"[EXTRACTOR] ERROR: Failed to extract entities")
        
        return state
    
    def _execute_query(self, state: WorkflowState) -> WorkflowState:
        """Query node"""
        print(f"\n[QUERY] ---- Query agent called ----")
        print(f"[QUERY] Intent: {state['intent']}")
        print(f"[QUERY] Entities: {state['entities']}")
        
        # Query agent returns (result, duration_ms)
        result, duration_ms = self.query_agent.execute_query(
            state["intent"],
            state["entities"]
        )
        
        print(f"[QUERY] Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        print(f"[QUERY] Success: {result.get('success', True)}")
        if result.get("error"):
            print(f"[QUERY] Error: {result.get('error')}")
        print(f"[QUERY] Duration: {duration_ms} ms\n")
        
        state["query_result"] = result
        
        if not result.get("success", True) and result.get("error"):
            state["error"] = result["error"]
            self.current_tracker.add_step(
                agent="Query",
                action="execute_query",
                input_data={"intent": state["intent"], "entities": state["entities"]},
                output_data={"error": result.get("error")},
                reasoning=f"Query failed: {result.get('error', 'Unknown error')}",
                duration_ms=int(duration_ms),
                success=False,
                error=result.get("error")
            )
        else:
            # Success
            desc = f"Retrieved data: {len(result)} fields"
            self.current_tracker.add_step(
                agent="Query",
                action="execute_query",
                input_data={"intent": state["intent"], "entities": state["entities"]},
                output_data={"fields_count": len(result)},
                reasoning=desc,
                duration_ms=int(duration_ms),
                success=True
            )
        
        return state
    
    def _format_response(self, state: WorkflowState) -> WorkflowState:
        """Formatter node"""
        print(f"\n[FORMATTER] ---- Formatter called ----")
        print(f"[FORMATTER] Intent: {state['intent']}")
        print(f"[FORMATTER] Query result keys: {list(state['query_result'].keys()) if isinstance(state['query_result'], dict) else 'N/A'}")
        
        result = self.formatter.format_response(
            state["user_query"],
            state["intent"],
            state["query_result"]
        )
        
        response_len = len(result.get("response", ""))
        print(f"[FORMATTER] Response length: {response_len} characters")
        print(f"[FORMATTER] Duration: {result.get('duration_ms', 0)} ms\n")
        
        state["final_response"] = result["response"]
        
        # Track this step
        self.current_tracker.add_step(
            agent="Formatter",
            action="format_response",
            input_data={"intent": state["intent"], "has_error": "error" in state["query_result"]},
            output_data={"response_length": response_len},
            reasoning=f"Generated {response_len} character response",
            duration_ms=result.get("duration_ms", 0),
            success=True
        )
        
        return state
    
    def _handle_fallback(self, state: WorkflowState) -> WorkflowState:
        """Fallback node"""
        print(f"\n[FALLBACK] ---- Fallback called ----")
        error = state.get("error", "Unknown error")
        print(f"[FALLBACK] Error: {error}")
        
        if "Invalid entities" in error or state["query_result"].get("error"):
            # Format error with Query result
            result = self.formatter.format_response(
                state["user_query"],
                state["intent"],
                state["query_result"]
            )
            state["final_response"] = result["response"]
        else:
            state["final_response"] = (
                "❌ I couldn't process your request.\n\n"
                "I can help you with:\n"
                "🏢 Property Comparisons\n"
                "💰 P&L Calculations\n"
                "📋 Property Details\n"
                "👥 Tenant Information\n\n"
                "Please try rephrasing your question."
            )
        
        print(f"[FALLBACK] Response: {state['final_response'][:100]}...\n")
        
        # Track fallback
        self.current_tracker.add_step(
            agent="Fallback",
            action="handle_error",
            input_data={"error": error},
            output_data={"has_response": bool(state["final_response"])},
            reasoning="Provided fallback response due to unsupported intent or error",
            duration_ms=0,
            success=True
        )
        
        return state
    
    def _should_proceed(self, state: WorkflowState) -> str:
        """Decide if we should continue or fallback after routing"""
        if state["intent"] == "unsupported":
            return "fallback"
        return "continue"
    
    def _should_format_or_fallback(self, state: WorkflowState) -> str:
        """Decide if we should format or fallback after query"""
        if state.get("error") and "Invalid entities" not in state["error"]:
            return "fallback"
        return "format"


