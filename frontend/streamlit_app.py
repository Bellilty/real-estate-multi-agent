"""
Enhanced Streamlit UI with Chain-of-Thought Display
Frontend for the Real Estate Multi-Agent System
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader
from backend.utils.conversation import ConversationContext


# Page configuration
st.set_page_config(
    page_title="Real Estate AI Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .chain-of-thought {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .reasoning-step {
        margin: 0.5rem 0;
        padding: 0.5rem;
        border-left: 3px solid #4CAF50;
        background-color: white;
        color: #333;
    }
    .reasoning-step strong {
        color: #1a1a1a;
    }
    .reasoning-step em {
        color: #555;
    }
    .metrics-box {
        background-color: #e8f4f8;
        padding: 0.5rem;
        border-radius: 0.5rem;
        text-align: center;
        color: #1a1a1a;
    }
    .metrics-box strong {
        color: #0066cc;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_system():
    """Initialize the multi-agent system (cached for performance)"""
    try:
        # Load LLM (cached)
        llm_client = LLMClient()
        llm = llm_client.get_llm()
        
        # Load data (cached)
        data_loader = RealEstateDataLoader("data/cortex.parquet")
        
        # Initialize orchestrator
        orchestrator = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
        
        # Get dataset stats (cached)
        stats = data_loader.get_dataset_stats()
        
        return orchestrator, data_loader, stats, None
        
    except Exception as e:
        return None, None, None, str(e)


def display_chain_of_thought(tracker, expanded=False):
    """Display the chain of thought in an expandable section"""
    metrics = tracker.get_metrics()
    title = f"🧠 **Chain of Thought** ({metrics.total_duration_ms:.0f}ms | {metrics.llm_calls} LLM calls)"
    
    with st.expander(title, expanded=expanded):
        st.markdown("**How the AI reasoned through your question:**")
        
        for i, step in enumerate(tracker.steps, 1):
            status_icon = "✅" if step.success else "❌"
            
            st.markdown(f"""
<div class="reasoning-step">
    <strong>{status_icon} Step {i}: {step.agent}</strong> ({step.duration_ms:.0f}ms)<br>
    <em>{step.reasoning}</em>
</div>
""", unsafe_allow_html=True)
            
            if step.error:
                st.error(f"Error: {step.error}")
        
        # Display metrics
        metrics = tracker.get_metrics()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
<div class="metrics-box">
    <strong>⏱️ Total Time</strong><br>
    {metrics.total_duration_ms:.0f}ms
</div>
""", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
<div class="metrics-box">
    <strong>🤖 LLM Calls</strong><br>
    {metrics.llm_calls}
</div>
""", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
<div class="metrics-box">
    <strong>📊 Steps</strong><br>
    {metrics.steps_count}
</div>
""", unsafe_allow_html=True)


def main():
    # Header
    st.markdown('<p class="main-header">🏢 Real Estate AI Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Multi-Agent System with Chain-of-Thought Reasoning</p>', unsafe_allow_html=True)
    
    # Initialize session state FIRST
    if "history" not in st.session_state:
        st.session_state.history = []
    
    # Initialize conversation context
    if "conversation" not in st.session_state:
        st.session_state.conversation = ConversationContext()
    
    # Initialize saved chats (list of previous chat sessions)
    if "saved_chats" not in st.session_state:
        st.session_state.saved_chats = []
    
    # Current chat ID
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = 0
    
    # Initialize system
    orchestrator, data_loader, stats, error = initialize_system()
    
    if error:
        st.error(f"❌ Failed to initialize system: {error}")
        st.info("Please make sure you have set your HUGGINGFACE_API_TOKEN in .env.local file")
        return
    
    # Sidebar
    with st.sidebar:
        st.title("🏢 Real Estate AI")
        st.markdown("Multi-Agent System")
        st.markdown("---")
        
        # Dataset summary (always visible)
        if stats:
            st.markdown("### 📊 Portfolio")
            st.markdown(f"**{len(stats['properties'])} Properties** | **{stats['total_records']:,} Records**")
            
            # Detailed info in expander
            with st.expander("📋 View Details"):
                st.markdown("**Properties:**")
                for prop in sorted(stats['properties']):
                    st.markdown(f"- {prop}")
                
                st.markdown("")
                st.markdown(f"**Tenants:** {len(stats['tenants'])}")
                st.markdown(f"**Period:** {stats['period_range'][0]} to {stats['period_range'][1]}")
                st.markdown(f"**Years:** {', '.join(map(str, stats['years']))}")
        
        st.markdown("---")
        
        # Chat history in sidebar
        st.markdown("### 💬 Chat History")
        
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            # Save current chat before clearing (if it has messages)
            if st.session_state.history:
                # Get first user message as chat title
                first_msg = st.session_state.history[0]["query"]
                chat_title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
                
                # Save chat
                st.session_state.saved_chats.append({
                    "id": st.session_state.current_chat_id,
                    "title": chat_title,
                    "messages": st.session_state.history.copy(),
                    "timestamp": st.session_state.conversation.messages[-1].timestamp if st.session_state.conversation.messages else None
                })
                
                # Increment chat ID for next chat
                st.session_state.current_chat_id += 1
            
            # Clear for new chat
            st.session_state.conversation.clear()
            st.session_state.history = []
            st.rerun()
        
        # Show current chat if active
        if st.session_state.history:
            st.markdown("**📍 Current Chat**")
            first_msg = st.session_state.history[0]["query"]
            current_preview = first_msg[:35] + "..." if len(first_msg) > 35 else first_msg
            st.markdown(f"💬 {current_preview}")
            st.markdown("")
        
        # Show saved chats
        if st.session_state.saved_chats:
            st.markdown("**💾 Previous Chats**")
            # Show last 10 saved chats (most recent first)
            for chat in reversed(st.session_state.saved_chats[-10:]):
                if st.button(f"💬 {chat['title']}", key=f"saved_{chat['id']}", use_container_width=True):
                    # Load saved chat
                    st.session_state.history = chat['messages'].copy()
                    st.rerun()
        
        if not st.session_state.history and not st.session_state.saved_chats:
            st.markdown("*No chat history yet*")
        
        # Clear all history option
        if st.session_state.saved_chats:
            st.markdown("")
            if st.button("🗑️ Clear All History", use_container_width=True, type="secondary"):
                st.session_state.saved_chats = []
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 🤖 Tech Stack")
        st.markdown("- **LLM:** GPT-4o-mini")
        st.markdown("- **Framework:** LangGraph")
        st.markdown("- **UI:** Streamlit")
        st.markdown("- **Data:** Polars")
    
    # Main content - FULL WIDTH (no more columns)
    with st.container():
        st.subheader("💬 Chat")
        
        # Chat container with scrollable history
        chat_container = st.container()
        
        with chat_container:
            if not st.session_state.history:
                # Welcome message
                st.info("👋 **Welcome!** Ask me about your real estate portfolio.\n\n*Example: \"What is the P&L for Building 180 in 2024?\"*")
            else:
                # Display chat history in chronological order
                for idx, item in enumerate(st.session_state.history):
                    # User message
                    with st.chat_message("user"):
                        st.markdown(item['query'])
                    
                    # Assistant message
                    with st.chat_message("assistant"):
                        # Chain of Thought FIRST (at the top, collapsed)
                        if 'tracker_dict' in item:
                            tracker_data = item['tracker_dict']
                            with st.expander("🧠 Chain of Thought", expanded=False):
                                if 'steps' in tracker_data:
                                    steps = tracker_data['steps']
                                    
                                    # Display steps
                                    for step_idx, step in enumerate(steps, 1):
                                        st.markdown(f"**Step {step_idx}: {step['agent']}** ({step['duration_ms']:.0f}ms)")
                                        st.text(step['reasoning'])
                                        st.markdown("")
                                    
                                    # Agent path summary
                                    st.markdown("---")
                                    agent_path = [step['agent'] for step in steps]
                                    agent_path_str = " → ".join([a.split('Agent')[0] for a in agent_path])
                                    st.markdown(f"📌 **Agent Path:** {agent_path_str}")
                                
                                if 'metrics' in tracker_data:
                                    metrics = tracker_data['metrics']
                                    st.markdown(f"⏱️ Total: {metrics['total_duration_ms']:.0f}ms | 🤖 LLM Calls: {metrics['llm_calls']}")
                        
                        # Response AFTER Chain of Thought
                        st.text(item['response'])
        
        st.markdown("---")
        
        # Query input (ChatGPT style - always at bottom)
        user_query = st.chat_input("Ask me about your properties...")
        
        # Process query
        if user_query:
            # Add user message to conversation
            st.session_state.conversation.add_user_message(user_query)
            
            # Check if it's a follow-up
            is_followup = st.session_state.conversation.is_follow_up_question(user_query)
            
            with st.spinner("🤔 Thinking..."):
                try:
                    # ALWAYS try to resolve references (not just for follow-ups)
                    resolved_query = st.session_state.conversation.resolve_references(user_query)
                    
                    # Show debug info if query was rewritten
                    if resolved_query != user_query:
                        st.info(f"💡 Context applied: \"{user_query}\" → \"{resolved_query}\"")
                    
                    # Quick fix: if user says "for all" after an error, re-run with last context
                    if user_query.lower().strip() in ["for all properties", "for all", "all properties", "all of them"]:
                        if st.session_state.conversation.last_intent and st.session_state.history:
                            last_query = st.session_state.history[-1]["query"]
                            resolved_query = f"{last_query} for all properties"
                    
                    # Build chat history for LLM context (last 10 exchanges)
                    chat_history = []
                    for msg in st.session_state.conversation.messages[-20:]:  # Last 10 pairs (20 messages)
                        chat_history.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                    
                    # Run orchestrator with chat history for follow-up context
                    response, tracker = orchestrator.run(resolved_query, chat_history=chat_history)
                    
                    # Update conversation context
                    intent = tracker.steps[0].output_data.get('intent') if tracker.steps else 'unknown'
                    
                    # Extract entities correctly - the extractor returns {"success": ..., "entities": {...}}
                    extractor_output = tracker.steps[1].output_data if len(tracker.steps) > 1 else {}
                    if isinstance(extractor_output, dict) and "entities" in extractor_output:
                        entities = extractor_output["entities"]
                    else:
                        entities = extractor_output
                    
                    query_result = tracker.steps[2].output_data if len(tracker.steps) > 2 else {}
                    
                    st.session_state.conversation.update_context(intent, entities, query_result)
                    st.session_state.conversation.add_assistant_message(response, {
                        "tracker": tracker.to_dict()
                    })
                    
                    # Store in history with tracker (chat will display it automatically)
                    st.session_state.history.append({
                        "query": user_query,
                        "response": response,
                        "metrics": tracker.get_metrics(),
                        "is_followup": is_followup,
                        "tracker_dict": tracker.to_dict()
                    })
                    
                    # Rerun to display new message (input auto-clears with st.chat_input)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    error_msg = f"I encountered an error: {str(e)}"
                    st.session_state.conversation.add_assistant_message(error_msg)


if __name__ == "__main__":
    main()

