# 🏢 Real Estate Multi-Agent Assistant

An AI-powered multi-agent system for real estate asset management using LangGraph, built with Python and Llama 3.2-3B.

## 📋 Overview

This system uses a multi-agent architecture to handle natural language queries about real estate properties, including:

- Property comparisons
- Profit & Loss (P&L) calculations
- Property details lookup
- Tenant information
- General dataset queries

## 🏗️ Architecture

### Multi-Agent Workflow (LangGraph)

```
User Query
    ↓
┌─────────────────┐
│  Router Agent   │  ← Classifies intent
└─────────────────┘
    ↓
┌─────────────────┐
│ Extractor Agent │  ← Extracts entities (properties, dates, etc.)
└─────────────────┘
    ↓
┌─────────────────┐
│  Query Agent    │  ← Executes data queries
└─────────────────┘
    ↓
┌─────────────────┐
│ Response Agent  │  ← Formats natural language response
└─────────────────┘
    ↓
Final Response
```

### Agents

1. **Router Agent**: Classifies user intent into predefined categories

   - property_comparison
   - pl_calculation
   - property_details
   - tenant_info
   - general_query

2. **Extractor Agent**: Extracts relevant entities from queries

   - Property names
   - Time periods (year, quarter, month)
   - Tenant names

3. **Query Agent**: Executes queries against the dataset

   - Uses Polars for efficient data processing
   - Calculates aggregations and comparisons

4. **Response Agent**: Formats results into natural language
   - Structured markdown responses
   - Error handling with helpful suggestions

### Technology Stack

- **LLM**: Llama 3.2-3B-Instruct (via HuggingFace)
- **Orchestration**: LangGraph
- **Framework**: LangChain
- **Data Processing**: Polars & PyArrow
- **UI**: Streamlit
- **Language**: Python 3.11+

## 🚀 Setup Instructions

### Prerequisites

- Python 3.11 or higher
- HuggingFace API token ([Get one here](https://huggingface.co/settings/tokens))

### Installation

1. **Clone the repository**

   ```bash
   cd Cortex-multi-agent-task
   ```

2. **Create and activate virtual environment**

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env.local` file in the project root:

   ```bash
   HUGGINGFACE_API_TOKEN=your_token_here
   ```

5. **Verify data file**

   Ensure `data/cortex.parquet` exists in the project directory.

### Running the Application

**Launch the Streamlit UI:**

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

**Test individual components:**

```bash
# Test data loader
python src/data_loader.py

# Test LLM client
python src/llm_client.py
```

## 💡 Usage Examples

### Query Examples

1. **P&L Calculation**

   ```
   "What is the P&L for Building 17?"
   "Calculate total profit and loss for 2024"
   "Show me P&L for Q1 2024"
   ```

2. **Property Comparison**

   ```
   "Compare Building 140 to Building 180"
   "Which performs better: Building 17 or Building 140?"
   ```

3. **Property Details**

   ```
   "Tell me about Building 17"
   "What are the details for Building 140?"
   ```

4. **Tenant Information**

   ```
   "Show me information about Tenant 12"
   "What properties does Tenant 8 occupy?"
   ```

5. **General Queries**
   ```
   "How many properties do we have?"
   "What is the date range of the data?"
   ```

## 🔧 Project Structure

```
Cortex-multi-agent-task/
├── app.py                      # Streamlit UI
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .env.local                  # Environment variables (not in git)
├── .gitignore                  # Git ignore rules
│
├── data/
│   └── cortex.parquet         # Real estate dataset
│
└── src/
    ├── llm_client.py          # HuggingFace LLM integration
    ├── data_loader.py         # Data loading and queries
    ├── graph.py               # LangGraph workflow
    │
    └── agents/
        ├── __init__.py
        ├── router_agent.py     # Intent classification
        ├── extractor_agent.py  # Entity extraction
        ├── query_agent.py      # Data queries
        └── response_agent.py   # Response formatting
```

## 🎯 Design Decisions

### 1. Why LangGraph?

LangGraph provides a clear, stateful workflow for orchestrating multiple agents. It allows:

- Explicit control flow between agents
- State management across agent transitions
- Conditional routing based on agent outputs
- Easy debugging and visualization

### 2. Why Llama 3.2-3B?

- **Free & Open Source**: No API costs
- **Good Performance**: Despite smaller size, performs well for structured tasks
- **Fast Inference**: Quick responses via HuggingFace Inference API
- **Instruction-tuned**: Optimized for following instructions

### 3. Why Polars over Pandas?

- **Performance**: Faster data processing, especially for aggregations
- **Memory Efficiency**: Better memory management for larger datasets
- **Modern API**: Clean, expressive syntax

### 4. Why Streamlit?

- **Rapid Development**: Quick to build interactive UIs
- **Python Native**: No need for JavaScript
- **Easy Deployment**: Can deploy to Streamlit Cloud or Vercel

## ⚠️ Error Handling

The system handles various edge cases:

1. **Property Not Found**

   - Returns list of available properties
   - Suggests correct property names

2. **Ambiguous Queries**

   - Router classifies as "unsupported"
   - Fallback agent provides guidance

3. **Missing Data**

   - Query agent returns appropriate error
   - Response agent formats helpful message

4. **LLM Failures**
   - Try-catch blocks around LLM calls
   - Fallback to structured responses

## 🧪 Testing

**Manual Testing Checklist:**

- [ ] Property comparison queries
- [ ] P&L calculation with different time periods
- [ ] Property details lookup
- [ ] Tenant information queries
- [ ] Handling of non-existent properties
- [ ] Ambiguous query handling
- [ ] Edge cases (empty results, etc.)

## 🚧 Challenges & Solutions

### Challenge 1: LLM Consistency

**Problem**: Free-tier LLMs can be inconsistent with structured output

**Solution**:

- Used explicit format instructions in prompts
- Added parsing logic to handle variations
- Implemented fallback responses

### Challenge 2: Entity Extraction

**Problem**: Property names might not match exactly in queries

**Solution**:

- Provided available properties list to LLM
- Implemented fuzzy matching in future enhancement
- Clear error messages with suggestions

### Challenge 3: Rate Limiting

**Problem**: HuggingFace free tier has rate limits

**Solution**:

- Used lower temperature for deterministic outputs
- Cached LLM initialization
- Minimal LLM calls per query (3-4 max)

### Challenge 4: Response Formatting

**Problem**: Balancing LLM-generated vs structured responses

**Solution**:

- Used structured templates for data-heavy responses
- LLM only for general queries
- Markdown formatting for readability

## 📈 Future Enhancements

- [ ] Add conversation history/memory
- [ ] Implement fuzzy property name matching
- [ ] Add data visualization (charts, graphs)
- [ ] Support batch queries
- [ ] Add authentication and user management
- [ ] Deploy to Vercel/cloud platform
- [ ] Add unit and integration tests
- [ ] Implement caching for common queries
- [ ] Add support for uploading custom datasets
- [ ] Multi-language support

## 📝 Notes

- **HuggingFace Rate Limits**: Free tier has limits. For production, consider Pro account or self-hosted model
- **Data Privacy**: Currently runs locally. No data sent to external services except HuggingFace LLM API
- **Performance**: First query may be slow (LLM cold start). Subsequent queries are faster

## 🤝 Contributing

This is a demonstration project. For improvements, please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

This project is created for the AI Developer Multi-Agent Task assessment.

## 👤 Author

Created as part of the Real Estate Asset Management Multi-Agent Task

---

**Built with ❤️ using LangGraph, LangChain, and Streamlit**
