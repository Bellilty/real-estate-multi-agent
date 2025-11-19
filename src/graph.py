"""
LangGraph Multi-Agent Workflow
Orchestrates the multi-agent system for real estate asset management
"""

from typing import TypedDict, Annotated, Any
from langgraph.graph import StateGraph, END
from langchain_core.language_models.llms import BaseLLM

from src.data_loader import RealEstateDataLoader
from src.agents.router_agent import RouterAgent
from src.agents.extractor_agent import ExtractorAgent
from src.agents.query_agent import QueryAgent
from src.agents.response_agent import ResponseAgent


class AgentState(TypedDict):
    """State object passed between agents"""
    user_query: str
    intent: str
    confidence: str
    entities: dict
    query_result: dict
    final_response: str
    error: str
    iteration: int


class RealEstateAgentGraph:
    """Multi-agent workflow using LangGraph"""
    
    def __init__(self, llm: BaseLLM, data_loader: RealEstateDataLoader):
        """Initialize the agent graph
        
        Args:
            llm: Language model instance
            data_loader: Data loader instance
        """
        self.llm = llm
        self.data_loader = data_loader
        
        # Initialize agents
        self.router_agent = RouterAgent(llm)
        self.extractor_agent = ExtractorAgent(
            llm, 
            data_loader.get_properties()
        )
        self.query_agent = QueryAgent(data_loader)
        self.response_agent = ResponseAgent(llm)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("router", self._route_intent)
        workflow.add_node("extractor", self._extract_entities)
        workflow.add_node("query", self._execute_query)
        workflow.add_node("formatter", self._format_response)
        workflow.add_node("fallback", self._handle_fallback)
        
        # Define edges
        workflow.set_entry_point("router")
        
        # From router, check if intent is supported
        workflow.add_conditional_edges(
            "router",
            self._should_proceed_to_extraction,
            {
                "extract": "extractor",
                "fallback": "fallback"
            }
        )
        
        # From extractor to query
        workflow.add_edge("extractor", "query")
        
        # From query, check if query succeeded
        workflow.add_conditional_edges(
            "query",
            self._should_retry_or_respond,
            {
                "format": "formatter",
                "fallback": "fallback"
            }
        )
        
        # From formatter and fallback to END
        workflow.add_edge("formatter", END)
        workflow.add_edge("fallback", END)
        
        return workflow.compile()
    
    def _route_intent(self, state: AgentState) -> AgentState:
        """Router node: Classify user intent"""
        print("🔀 Router: Classifying intent...")
        
        result = self.router_agent.classify_intent(state["user_query"])
        
        state["intent"] = result["intent"]
        state["confidence"] = result["confidence"]
        
        print(f"   Intent: {result['intent']} (confidence: {result['confidence']})")
        print(f"   Reason: {result['reason']}")
        
        return state
    
    def _extract_entities(self, state: AgentState) -> AgentState:
        """Extractor node: Extract entities from query"""
        print("🔍 Extractor: Extracting entities...")
        
        entities = self.extractor_agent.extract_entities(
            state["user_query"],
            state["intent"]
        )
        
        state["entities"] = entities
        print(f"   Entities: {entities}")
        
        return state
    
    def _execute_query(self, state: AgentState) -> AgentState:
        """Query node: Execute data query"""
        print("🗄️  Query: Executing query...")
        
        result = self.query_agent.execute_query(
            state["intent"],
            state["entities"]
        )
        
        state["query_result"] = result
        
        if "error" in result:
            print(f"   ⚠️  Query error: {result['error']}")
        else:
            print("   ✅ Query successful")
        
        return state
    
    def _format_response(self, state: AgentState) -> AgentState:
        """Response node: Format final response"""
        print("💬 Response: Formatting answer...")
        
        response = self.response_agent.format_response(
            state["intent"],
            state["query_result"],
            state["user_query"]
        )
        
        state["final_response"] = response
        print("   ✅ Response generated")
        
        return state
    
    def _handle_fallback(self, state: AgentState) -> AgentState:
        """Fallback node: Handle unsupported or failed requests"""
        print("⚠️  Fallback: Handling error/unsupported request...")
        
        # Check why we're in fallback
        if state["intent"] == "unsupported":
            response = """I'm sorry, I couldn't understand your request or it's not something I can help with.

I can help you with:
- **Property Comparisons**: Compare two properties
- **P&L Calculations**: Calculate profit and loss for properties or time periods
- **Property Details**: Get information about specific properties
- **Tenant Information**: Look up tenant data
- **General Questions**: Answer questions about the dataset

Could you please rephrase your question or try one of the above request types?"""
        
        elif "error" in state.get("query_result", {}):
            # Query failed, provide helpful error message
            response = self.response_agent.format_response(
                state["intent"],
                state["query_result"],
                state["user_query"]
            )
        
        else:
            response = """I encountered an issue processing your request. Please try:
- Being more specific about properties or time periods
- Using property names from the available list
- Rephrasing your question

Would you like to see the list of available properties?"""
        
        state["final_response"] = response
        return state
    
    def _should_proceed_to_extraction(self, state: AgentState) -> str:
        """Decision: Should we proceed to entity extraction?"""
        if state["intent"] == "unsupported" or state["confidence"] == "low":
            return "fallback"
        return "extract"
    
    def _should_retry_or_respond(self, state: AgentState) -> str:
        """Decision: Should we format response or go to fallback?"""
        # Check if query has critical error
        result = state.get("query_result", {})
        
        if "error" in result:
            # Some errors can still be formatted nicely (e.g., "property not found")
            # Only go to fallback for critical errors
            error_msg = result["error"].lower()
            if "execution failed" in error_msg or "unsupported" in error_msg:
                return "fallback"
        
        return "format"
    
    def run(self, user_query: str) -> str:
        """Run the agent graph with a user query
        
        Args:
            user_query: The user's natural language query
            
        Returns:
            The final response string
        """
        print("\n" + "="*80)
        print("🚀 Starting Multi-Agent Workflow")
        print("="*80)
        print(f"Query: {user_query}\n")
        
        # Initialize state
        initial_state: AgentState = {
            "user_query": user_query,
            "intent": "",
            "confidence": "",
            "entities": {},
            "query_result": {},
            "final_response": "",
            "error": "",
            "iteration": 0
        }
        
        try:
            # Run the graph
            final_state = self.graph.invoke(initial_state)
            
            print("\n" + "="*80)
            print("✅ Workflow Complete")
            print("="*80 + "\n")
            
            return final_state["final_response"]
            
        except Exception as e:
            print(f"\n❌ Workflow Error: {str(e)}\n")
            return f"An error occurred while processing your request: {str(e)}"


def create_agent_graph(llm: BaseLLM, data_loader: RealEstateDataLoader) -> RealEstateAgentGraph:
    """Factory function to create the agent graph
    
    Args:
        llm: Language model instance
        data_loader: Data loader instance
        
    Returns:
        Initialized agent graph
    """
    return RealEstateAgentGraph(llm, data_loader)

