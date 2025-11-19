"""
Streamlit UI for Real Estate Multi-Agent Assistant
"""

import streamlit as st
from src.llm_client import LLMClient
from src.data_loader import RealEstateDataLoader
from src.graph import create_agent_graph


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
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTextInput > div > div > input {
        font-size: 1.1rem;
    }
    .example-query {
        background-color: #f0f2f6;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        cursor: pointer;
    }
    .example-query:hover {
        background-color: #e0e2e6;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_system():
    """Initialize the LLM and data loader (cached)"""
    try:
        llm_client = LLMClient()
        data_loader = RealEstateDataLoader()
        agent_graph = create_agent_graph(llm_client.get_llm(), data_loader)
        
        return agent_graph, data_loader, None
    except Exception as e:
        return None, None, str(e)


def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown('<div class="main-header">🏢 Real Estate AI Assistant</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Initialize system
    with st.spinner("🔄 Initializing AI system..."):
        agent_graph, data_loader, error = initialize_system()
    
    if error:
        st.error(f"❌ Failed to initialize system: {error}")
        st.info("Please make sure you have set your HUGGINGFACE_API_TOKEN in `.env.local` file")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dataset Info")
        
        if data_loader:
            summary = data_loader.get_data_summary()
            
            st.metric("Total Records", f"{summary['total_records']:,}")
            st.metric("Properties", summary['properties_count'])
            st.metric("Tenants", summary['tenants_count'])
            
            st.markdown("---")
            
            st.subheader("📅 Date Range")
            st.write(f"**Years:** {', '.join(summary['date_range']['years'])}")
            st.write(f"**Period:** {summary['date_range']['earliest_month']} to {summary['date_range']['latest_month']}")
            
            st.markdown("---")
            
            st.subheader("🏢 Available Properties")
            properties = data_loader.get_properties()
            for prop in properties:
                st.write(f"- {prop}")
        
        st.markdown("---")
        st.markdown("### 🤖 Powered by")
        st.markdown("- **LLM:** Llama 3.2-3B")
        st.markdown("- **Framework:** LangGraph")
        st.markdown("- **UI:** Streamlit")
    
    # Initialize session state
    if "query_input" not in st.session_state:
        st.session_state.query_input = ""
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Ask a Question")
        
        # Query input
        user_query = st.text_input(
            "Enter your question:",
            value=st.session_state.query_input,
            placeholder="e.g., What is the P&L for Building 17 in 2024?",
            label_visibility="collapsed",
            key="text_input"
        )
        
        # Submit button
        submit_button = st.button("🚀 Ask", type="primary", use_container_width=True)
        
        # Process query
        if submit_button and user_query:
            with st.spinner("🤔 Thinking..."):
                response = agent_graph.run(user_query)
            
            st.markdown("---")
            st.subheader("💡 Response")
            st.markdown(response)
            
            # Store in session state for history
            if "history" not in st.session_state:
                st.session_state.history = []
            
            st.session_state.history.append({
                "query": user_query,
                "response": response
            })
            
            # Clear input after successful query
            st.session_state.query_input = ""
    
    with col2:
        st.subheader("💡 Example Queries")
        
        examples = [
            "What is the P&L for Building 17?",
            "Compare Building 140 to Building 180",
            "What is the total P&L for 2024?",
            "Tell me about Building 17",
            "What is the P&L for Q1 2024?",
            "Show me information about Tenant 12",
            "What properties does Tenant 8 occupy?",
            "Calculate P&L for Building 140 in 2024",
        ]
        
        for example in examples:
            if st.button(f"📝 {example}", key=example, use_container_width=True):
                st.session_state.query_input = example
                st.rerun()
    
    # Query history
    if "history" in st.session_state and st.session_state.history:
        st.markdown("---")
        st.subheader("📜 Query History")
        
        for i, item in enumerate(reversed(st.session_state.history[-5:])):
            with st.expander(f"Query {len(st.session_state.history) - i}: {item['query'][:50]}..."):
                st.markdown(f"**Question:** {item['query']}")
                st.markdown(f"**Answer:**\n\n{item['response']}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Built with ❤️ using LangGraph & Streamlit | "
        "AI Developer Multi-Agent Task"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

