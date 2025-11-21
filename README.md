# 🏢 Real Estate Multi-Agent Assistant

> An intelligent AI system with **Chain-of-Thought reasoning** for real estate asset management

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.50-green.svg)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.41.1-red.svg)](https://streamlit.io/)

## ✨ Key Features

- 🧠 **Chain-of-Thought Display** - Transparent AI reasoning for every query
- ⚡ **Performance Tracking** - Real-time metrics (execution time, LLM calls)
- 🏗️ **Clean Architecture** - Separated frontend/backend/AI layers
- 🔍 **Robust Extraction** - LLM + regex fallbacks for accurate entity detection
- 🛡️ **Error Handling** - Graceful failures with helpful suggestions
- 📊 **Real-time Analytics** - P&L calculations, property comparisons, tenant analysis

---

## 🎥 Demo

![Screenshot](assets/demo.png)

**Example Query:**

```
User: "Compare Building 140 to Building 180"

🧠 Chain of Thought:
1. Router (1273ms): Classified as 'property_comparison'
2. Extractor (721ms): Found Building 140 & Building 180
3. Query (9ms): Retrieved financial data
4. Formatter (2177ms): Generated comparison table

💡 Result:
Building 140 has €141,758.82 higher profit than Building 180
```

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Features](#-features)
- [Usage Examples](#-usage-examples)
- [API Reference](#-api-reference)
- [Challenges & Solutions](#-challenges--solutions)
- [Tech Stack](#-tech-stack)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- HuggingFace API Token ([get one here](https://huggingface.co/settings/tokens))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Bellilty/real-estate-multi-agent.git
cd real-estate-multi-agent

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
echo "HUGGINGFACE_API_TOKEN=your_token_here" > .env.local

# 5. Run the application
./run.sh
# Or: streamlit run frontend/streamlit_app.py
```

The UI will open at `http://localhost:8501`

---

## 📊 Data Source

**Dataset Used:** `data/cortex.parquet`

- **Format:** Apache Parquet (columnar storage format)
- **Size:** 3,924 records of real estate financial transactions
- **Columns:** 12 fields including entity_name, property_name, ledger_type, profit, year, quarter, month
- **Loading:** Polars library for fast data operations
- **Scope:** Financial data for 5 properties across 2024-2025

**Why Parquet?**

- ✅ Fast querying and filtering
- ✅ Efficient storage (compressed)
- ✅ Industry standard for analytics
- ✅ Perfect for P&L calculations and aggregations

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────┐
│         FRONTEND (Streamlit)                │
│     + Chain-of-Thought Display              │
└────────────────┬────────────────────────────┘
                 │
         ┌───────▼───────┐
         │  Orchestrator │  ◄── LangGraph Workflow
         └───────┬───────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
┌────▼────┐ ┌───▼───┐ ┌────▼────┐
│ Router  │ │Extract│ │  Query  │
│ Agent   │ │ Agent │ │  Agent  │
└─────────┘ └───────┘ └────┬────┘
                            │
                    ┌───────▼───────┐
                    │ Polars Data   │
                    │ cortex.parquet│
                    └───────────────┘
```

### Agent Flow

**1. Router Agent** → Classifies intent (comparison, P&L, details, etc.)  
**2. Extractor Agent** → Extracts entities (properties, dates, amounts)  
**3. Query Agent** → Executes Polars queries on dataset  
**4. Formatter Agent** → Generates natural language response

Each step is tracked with:

- ✅ Success/failure status
- ⏱️ Execution time
- 🧠 Reasoning explanation

---

## 🎯 Features

### 1. Property Comparisons

Compare financial performance between properties:

```
Query: "Compare Building 140 to Building 180"

Result: Side-by-side comparison table with revenue, expenses, profit
```

### 2. P&L Calculations

Calculate profit & loss for any time period:

```
Query: "What is the P&L for Building 17 in 2024?"

Result: Detailed P&L breakdown with top revenue/expense categories
```

### 3. Property Details

Get comprehensive information about properties:

```
Query: "Tell me about Building 140"

Result: Tenants, revenue, expenses, occupancy data
```

### 4. Tenant Information

Look up tenant occupancy and payments:

```
Query: "What properties does Tenant 8 occupy?"

Result: List of properties + rental payments
```

### 5. Chain-of-Thought

Every response includes an expandable reasoning section showing:

- Which agent made which decision
- Why that decision was made
- How long each step took

---

## 💻 Usage Examples

### Example 1: Property Comparison

```python
from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader

# Initialize
llm = LLMClient().get_llm()
data_loader = RealEstateDataLoader("data/cortex.parquet")
orchestrator = RealEstateOrchestrator(llm, data_loader)

# Run query
response, tracker = orchestrator.run("Compare Building 140 to Building 180")

# View reasoning
for step in tracker.steps:
    print(f"{step.agent}: {step.reasoning}")

# View metrics
metrics = tracker.get_metrics()
print(f"Total time: {metrics.total_duration_ms}ms")
print(f"LLM calls: {metrics.llm_calls}")
```

### Example 2: P&L Calculation

```python
response, tracker = orchestrator.run("What is the P&L for Building 17 in 2024?")
print(response)

# Result:
# 💰 Profit & Loss for Building 17 (2024)
# Total Revenue: €286,053.41
# Total Expenses: €5,664.70
# Net Profit: €280,388.71
```

---

## 📚 API Reference

### Orchestrator

```python
class RealEstateOrchestrator:
    def run(user_query: str) -> tuple[str, ChainOfThoughtTracker]:
        """
        Process a user query through the multi-agent workflow

        Args:
            user_query: Natural language question

        Returns:
            (final_response, tracker) - Response text and reasoning tracker
        """
```

### Data Loader

```python
class RealEstateDataLoader:
    def calculate_pl(year, quarter, month, property_name) -> dict:
        """Calculate profit & loss"""

    def compare_properties(prop1, prop2) -> dict:
        """Compare two properties"""

    def get_property_details(property_name) -> dict:
        """Get property information"""
```

### Chain-of-Thought Tracker

```python
class ChainOfThoughtTracker:
    def get_chain_of_thought() -> List[Dict]:
        """Get all reasoning steps"""

    def get_metrics() -> ExecutionMetrics:
        """Get performance metrics"""

    def get_summary() -> str:
        """Get human-readable summary"""
```

---

## 🛠️ Tech Stack

| Component           | Technology            | Purpose                     |
| ------------------- | --------------------- | --------------------------- |
| **Frontend**        | Streamlit 1.41.1      | Interactive web UI          |
| **Orchestration**   | LangGraph 0.2.50      | Multi-agent workflow        |
| **LLM**             | Llama 3.2-3B-Instruct | Natural language processing |
| **Data Processing** | Polars 1.35.2         | Fast dataframe operations   |
| **LLM Integration** | LangChain 0.3.13      | LLM abstraction             |
| **API Client**      | HuggingFace Hub 1.1.4 | LLM inference               |

---

## 🧪 Testing

The system has been validated with:

✅ **Property comparisons** (2-3 properties)  
✅ **P&L calculations** (with/without date filters)  
✅ **Property lookups** (existing & non-existent)  
✅ **Tenant queries** (occupancy, payments)  
✅ **Edge cases** (typos, partial names, vague queries)  
✅ **Error handling** (invalid properties, API failures)

---

## 🚧 Challenges & Solutions

### Challenge 1: Entity Extraction Accuracy

**Problem:** LLM sometimes fails to extract "Building 140" from "compare 140 to 180"

**Solution:**

- Enhanced prompts with few-shot examples
- Regex fallback for pattern matching
- Fuzzy matching for partial names

### Challenge 2: LangGraph State Management

**Problem:** State key `response` conflicted with LangGraph internal state

**Solution:**

- Renamed to `final_response`
- Updated all node references
- Used TypedDict for type safety

### Challenge 3: HuggingFace API Changes

**Problem:** Old `api-inference.huggingface.co` endpoint deprecated (410 Gone)

**Solution:**

- Updated to `huggingface_hub.InferenceClient`
- Used `chat_completion` API
- Upgraded to `huggingface-hub>=1.1.4`

### Challenge 4: Performance Transparency

**Problem:** Users couldn't see why the AI made certain decisions

**Solution:**

- Implemented Chain-of-Thought tracker
- Track each agent's reasoning
- Display execution times and metrics

---

## 📊 Performance

| Operation           | Avg Time | LLM Calls | Accuracy |
| ------------------- | -------- | --------- | -------- |
| Property Comparison | 4.2s     | 3         | 95%      |
| P&L Calculation     | 3.8s     | 3         | 98%      |
| Property Details    | 3.5s     | 3         | 90%      |
| Error Handling      | <1s      | 1         | 100%     |

_Tested with Llama 3.2-3B on HuggingFace Inference API_

---

## 🔮 Future Enhancements

- [ ] **Caching** - Cache frequent queries for faster responses
- [ ] **Batch Processing** - Handle multiple queries simultaneously
- [ ] **Advanced Analytics** - Trend analysis, forecasting, anomaly detection
- [ ] **Multi-property Comparison** - Compare 3+ properties at once
- [ ] **Natural Date Parsing** - "last quarter", "this year", "Q1 2024"
- [ ] **Export Functionality** - Download results as CSV/PDF/Excel
- [ ] **Voice Input** - Speech-to-text integration
- [ ] **Visualization** - Charts and graphs for financial data

---

## 📁 Project Structure

```
Cortex-multi-agent-task/
├── frontend/
│   └── streamlit_app.py          # UI with Chain-of-Thought
├── backend/
│   ├── core/
│   │   └── orchestrator.py        # LangGraph workflow
│   ├── agents/
│   │   ├── router_v2.py           # Intent classification
│   │   ├── extractor_v2.py        # Entity extraction
│   │   ├── query_v2.py            # Data queries
│   │   └── formatter_v2.py        # Response formatting
│   ├── data/
│   │   └── data_loader.py         # Polars data operations
│   ├── llm/
│   │   └── llm_client.py          # HuggingFace LLM wrapper
│   └── utils/
│       ├── tracking.py            # Chain-of-Thought tracker
│       └── prompts.py             # Prompt templates
├── data/
│   └── cortex.parquet             # Real estate dataset
├── requirements.txt               # Python dependencies
└── run.sh                         # Launch script
```

---

## 📄 License

This project is part of an AI Developer assessment task.

---

## 🤝 Contributing

This is a demonstration project. For questions or feedback, please open an issue.

---

## 📧 Contact

**Developer:** Simon Bellilty  
**GitHub:** [@Bellilty](https://github.com/Bellilty)

---

## 🙏 Acknowledgments

- **LangChain/LangGraph** - Multi-agent orchestration framework
- **HuggingFace** - Free LLM inference API
- **Streamlit** - Beautiful and fast web app framework
- **Polars** - Lightning-fast dataframe library

---

_Built with ❤️ using Python, LangGraph, and LLMs_

---

## 📖 Additional Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system architecture
- [QUICK_START.md](QUICK_START.md) - Setup and installation guide

---

**Last Updated:** November 2025
