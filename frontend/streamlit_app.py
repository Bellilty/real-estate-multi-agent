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
    .reasoning-step {
        margin: 0.5rem 0;
        padding: 0.5rem;
        border-left: 3px solid #4CAF50;
        background-color: white;
    }
    .metrics-box {
        background: #e8f4f8;
        padding: 0.6rem;
        border-radius: 0.4rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_system():
    """Initialize the multi-agent system (cached for performance)."""
    try:
        llm = LLMClient().get_llm()
        data_loader = RealEstateDataLoader("data/cortex.parquet")
        orchestrator = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
        stats = data_loader.get_dataset_stats()
        return orchestrator, data_loader, stats, None
    except Exception as e:
        return None, None, None, str(e)


def main():
    # Headers
    st.markdown('<p class="main-header">🏢 Real Estate AI Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Multi-Agent System with Chain-of-Thought Reasoning</p>', unsafe_allow_html=True)

    # Session state
    if "history" not in st.session_state:
        st.session_state.history = []
    if "saved_chats" not in st.session_state:
        st.session_state.saved_chats = []
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = 0

    # Load system
    orchestrator, data_loader, stats, error = initialize_system()

    if error:
        st.error(f"❌ Failed to initialize system: {error}")
        return

    # Sidebar
    with st.sidebar:
        st.title("🏢 Real Estate AI")
        st.markdown("Multi-Agent System")
        st.markdown("---")

        # Dataset info
        st.markdown("### 📊 Portfolio")
        if stats:
            st.markdown(f"**{len(stats['properties'])} Properties** | **{stats['total_records']:,} Records**")
            with st.expander("Details"):
                st.write("Properties:")
                for p in sorted(stats["properties"]):
                    st.markdown(f"- {p}")
                st.markdown(f"Tenants: {len(stats['tenants'])}")
                if stats.get('period_range') and len(stats['period_range']) >= 2:
                    # Format months nicely: "2024-M01" → "Jan 2024"
                    def format_month(month_str):
                        if not month_str or '-' not in month_str:
                            return month_str
                        parts = month_str.split('-')
                        if len(parts) == 2 and parts[1].startswith('M'):
                            year = parts[0]
                            month_num = int(parts[1][1:])
                            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                            return f"{month_names[month_num-1]} {year}"
                        return month_str
                    start = format_month(stats['period_range'][0])
                    end = format_month(stats['period_range'][-1])
                    st.markdown(f"Period: {start} → {end}")
                else:
                    # Fallback to years if no month range
                    if stats.get('years') and len(stats['years']) >= 2:
                        st.markdown(f"Period: {stats['years'][0]} → {stats['years'][-1]}")
                    elif stats.get('years'):
                        st.markdown(f"Year: {stats['years'][0]}")
                st.markdown(f"Years: {', '.join(map(str, stats['years'])) if stats.get('years') else 'N/A'}")

        st.markdown("---")

        # Chat history
        st.markdown("### 💬 Chat History")

        if st.button("➕ New Chat", use_container_width=True):
            if st.session_state.history:
                first = st.session_state.history[0]["query"]
                title = first[:45] + "..." if len(first) > 45 else first
                st.session_state.saved_chats.append({
                    "id": st.session_state.current_chat_id,
                    "title": title,
                    "messages": st.session_state.history.copy()
                })
                st.session_state.current_chat_id += 1

            st.session_state.history = []
            st.rerun()

        if st.session_state.saved_chats:
            st.markdown("**Saved Chats:**")
            for chat in reversed(st.session_state.saved_chats[-10:]):
                if st.button(f"💬 {chat['title']}", use_container_width=True):
                    st.session_state.history = chat["messages"].copy()
                    st.rerun()

        if st.session_state.saved_chats:
            if st.button("🗑️ Clear All History", use_container_width=True):
                st.session_state.saved_chats = []
                st.rerun()

        st.markdown("---")
        st.markdown("### 🤖 Tech")
        st.markdown("- GPT-4o-mini")
        st.markdown("- LangGraph")
        st.markdown("- Streamlit")
        st.markdown("- Polars")

    # Main Chat Display
    st.subheader("💬 Chat")

    # Show past messages
    if not st.session_state.history:
        st.info("👋 Welcome! Ask anything about your real estate data.\nExample: *What is the P&L for Building 180 in 2024?*")
    else:
        for msg in st.session_state.history:
            with st.chat_message("user"):
                st.markdown(msg["query"])
            with st.chat_message("assistant"):
                # Chain-of-thought viewer
                with st.expander("🧠 Chain of Thought"):
                    tracker = msg["tracker"]
                    for i, step in enumerate(tracker["steps"], 1):
                        st.markdown(f"**Step {i}: {step['agent']}** ({step['duration_ms']:.0f}ms)")
                        st.text(step["reasoning"])

                    metrics = tracker["metrics"]
                    st.markdown(f"⏱️ {metrics['total_duration_ms']:.0f}ms | 🤖 {metrics['llm_calls']} LLM Calls")

                st.text(msg["response"])

    # User input
    user_query = st.chat_input("Ask me about your properties...")

    if user_query:
        with st.spinner("🤔 Thinking..."):
            try:
                # Build chat_history from session state for follow-up detection
                chat_history = []
                if st.session_state.history:
                    # Take last 6 messages (3 exchanges) for context
                    for msg in st.session_state.history[-6:]:
                        chat_history.append({
                            "user": msg["query"],
                            "assistant": msg["response"]
                        })
                
                response, tracker = orchestrator.run(user_query, chat_history=chat_history if chat_history else None)

                st.session_state.history.append({
                    "query": user_query,
                    "response": response,
                    "tracker": tracker.to_dict()
                })

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
