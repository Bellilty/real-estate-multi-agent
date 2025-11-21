## 🏗️ System Architecture

### Overview

The Real Estate Multi-Agent System uses **LangGraph** to orchestrate multiple specialized AI agents that work together to process user queries about real estate data. The system features a clean separation between frontend, backend, and AI components, with built-in Chain-of-Thought reasoning and performance tracking.

### 📊 Data Source

**Primary Dataset:** `data/cortex.parquet`

The system retrieves all financial information from a **Parquet dataset** containing real estate transactions:

- **Format:** Apache Parquet (columnar, compressed)
- **Records:** 3,924 financial transactions
- **Properties:** 5 buildings (Building 17, 120, 140, 160, 180)
- **Entity:** PropCo (Property Company)
- **Time Period:** 2024-01 to 2025-03
- **Data Fields:**
  - `entity_name`: Organization (PropCo)
  - `property_name`: Building identifier
  - `tenant_name`: Tenant occupying the space
  - `ledger_type`: revenue or expenses
  - `ledger_category`: Rent, parking, mortgage, etc.
  - `profit`: Transaction amount
  - `year`, `quarter`, `month`: Time dimensions

**Data Loading:** Polars library (Python) for high-performance data operations

**Why This Approach?**
- ✅ No external API dependencies (works offline)
- ✅ Fast queries (<10ms for most operations)
- ✅ Easy to version control and replicate
- ✅ Industry-standard format for analytics

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│              (Streamlit - frontend/)                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (backend/core/)                │
│         Coordinates agents with LangGraph                │
│         + Chain-of-Thought Tracking                      │
└─┬───────────────────────────────────────────────────────┘
  │
  │    ┌──────────────┐    ┌──────────────┐
  ├────► Router Agent │───►│ Extractor    │
  │    │ (Intent)     │    │ (Entities)   │
  │    └──────────────┘    └──────────────┘
  │
  │    ┌──────────────┐    ┌──────────────┐
  ├────► Query Agent  │───►│ Formatter    │
  │    │ (Data)       │    │ (Response)   │
  │    └──────────────┘    └──────────────┘
  │
  │    ┌──────────────┐
  └────► Fallback     │
       │ (Errors)     │
       └──────────────┘
            │
            ▼
  ┌─────────────────────┐
  │   DATA LAYER        │
  │  (Polars DataFrame) │
  │  cortex.parquet     │
  └─────────────────────┘
```

---

## 📁 Project Structure

```
Cortex-multi-agent-task/
│
├── frontend/                 # 🎨 Frontend Layer
│   └── streamlit_app.py     # Streamlit UI with Chain-of-Thought display
│
├── backend/                  # ⚙️ Backend Layer (Complete)
│   ├── core/                # Core orchestration logic
│   │   └── orchestrator.py  # LangGraph workflow coordinator
│   │
│   ├── agents/              # 🤖 AI Agents
│   │   ├── router_v2.py     # Intent classification
│   │   ├── extractor_v2.py  # Entity extraction with fallbacks
│   │   ├── query_v2.py      # Data query execution
│   │   └── formatter_v2.py  # Response formatting
│   │
│   ├── data/                # 📊 Data Layer
│   │   └── data_loader.py   # Polars data operations
│   │
│   ├── llm/                 # 🤖 LLM Layer
│   │   └── llm_client.py    # HuggingFace LLM wrapper
│   │
│   └── utils/               # 🛠️ Utilities
│       ├── tracking.py      # Performance & Chain-of-Thought tracking
│       └── prompts.py       # Enhanced prompt templates
│
├── data/                     # 📊 Dataset
│   └── cortex.parquet       # Real estate financial data
│
├── .env.local               # 🔐 API keys (not in git)
├── requirements.txt         # 📦 Python dependencies
└── run.sh                   # 🚀 Launch script
```

---

## 🔄 Data Flow: From Question to Answer

### Step-by-Step Process

#### **1. User Input** 
```
User: "Compare Building 140 to Building 180"
```

#### **2. Router Agent** (Intent Classification)
- **Input:** Raw user query
- **Process:** Sends query to LLM with classification prompt
- **Output:** Intent type + confidence level
- **Example:**
  ```
  Intent: property_comparison
  Confidence: high
  Reason: Two buildings to compare
  ```

#### **3. Extractor Agent** (Entity Extraction)
- **Input:** User query + Intent
- **Process:** 
  - Uses intent-specific prompt to extract entities
  - Applies regex fallbacks if LLM fails
  - Validates against available properties
- **Output:** Extracted entities
- **Example:**
  ```json
  {
    "properties": ["Building 140", "Building 180"],
    "count": 2
  }
  ```

#### **4. Query Agent** (Data Retrieval)
- **Input:** Intent + Entities
- **Process:**
  - Validates entities against dataset
  - Executes Polars queries on `cortex.parquet`
  - Performs calculations (P&L, comparisons, etc.)
- **Output:** Raw data results
- **Example:**
  ```json
  {
    "Building 140": {
      "total_revenue": 537340.10,
      "total_expenses": 10681.25,
      "net_profit": 526658.85
    },
    "Building 180": {
      "total_revenue": 391490.26,
      "total_expenses": 6590.23,
      "net_profit": 384900.03
    }
  }
  ```

#### **5. Formatter Agent** (Response Generation)
- **Input:** User query + Data results + Chain of thought summary
- **Process:** Sends data to LLM with formatting prompt
- **Output:** Natural language response in Markdown
- **Example:**
  ```markdown
  🏢 **Property Comparison: Building 140 vs Building 180**
  
  | Metric | Building 140 | Building 180 |
  |--------|-------------|--------------|
  | Total Revenue | €537,340.10 | €391,490.26 |
  | Net Profit | €526,658.85 | €384,900.03 |
  
  Building 140 has €141,758.82 higher profit.
  ```

#### **6. Chain-of-Thought Display**
The system tracks each step with:
- Agent name
- Action performed
- Reasoning
- Execution time (ms)
- Success/failure status

---

## 🧠 Chain-of-Thought Tracking

The system implements a transparent reasoning process:

```python
class ChainOfThoughtTracker:
    - Tracks each agent's reasoning
    - Measures execution time per step
    - Counts LLM API calls
    - Provides performance metrics
```

**Example Output:**
```
1. Router (1273ms): Classified as 'property_comparison' with high confidence
2. Extractor (721ms): Extracted 2 properties: Building 140, Building 180
3. Query (9ms): Retrieved comparison data
4. Formatter (2177ms): Generated 709 character response

Total: 4234ms | LLM Calls: 3
```

---

## 🎯 Enhanced Features

### 1. **Robust Entity Extraction**
- LLM-based extraction with **regex fallbacks**
- Handles partial matches ("140" → "Building 140")
- Validates against available data

### 2. **Error Handling**
- Validates all entities before querying
- Provides helpful error messages with available options
- Fallback agent for unsupported requests

### 3. **Performance Optimization**
- Tracks execution time per agent
- Monitors LLM API usage
- Provides performance metrics to user

### 4. **Flexible Prompts**
- Intent-specific prompt templates
- Few-shot examples for better accuracy
- Structured output format for reliable parsing

---

## 🔧 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Interactive web UI |
| **Orchestration** | LangGraph | Multi-agent workflow |
| **LLM** | Llama 3.2-3B (HuggingFace) | Natural language processing |
| **Data** | Polars | Fast dataframe operations |
| **State Management** | TypedDict | Type-safe state passing |
| **Tracking** | Custom Tracker | Chain-of-Thought & metrics |

---

## 🚀 Performance Characteristics

| Operation | Typical Time | LLM Calls |
|-----------|-------------|-----------|
| Property Comparison | ~4-5s | 3 |
| P&L Calculation | ~3-4s | 3 |
| Property Details | ~3-4s | 3 |
| Error Fallback | <1s | 1 |

*Note: Times vary based on LLM API response time*

---

## 🛡️ Error Handling Strategy

### 1. **Validation Errors**
```
Property not found → Show available properties
No data for time period → Suggest valid periods
```

### 2. **Extraction Failures**
```
LLM fails to extract → Regex fallback
No entities found → Request clarification
```

### 3. **LLM API Errors**
```
Rate limit → Graceful error message
Network error → Retry logic
```

### 4. **Unsupported Queries**
```
Intent: unsupported → Fallback agent
Shows: Capabilities + Examples
```

---

## 📊 Data Model

### Input Dataset (cortex.parquet)
```
Columns:
- period: Date (YYYY-MM)
- property_name: Building identifier
- tenant_name: Tenant identifier  
- ledger_type: revenue/expense
- ledger: Specific type (rent, mortgage, etc.)
- profit: Amount (€)
```

### Agent State (WorkflowState)
```python
{
    "user_query": str,      # Original question
    "intent": str,          # Classified intent
    "confidence": str,      # Classification confidence
    "entities": dict,       # Extracted parameters
    "query_result": dict,   # Data from database
    "final_response": str,  # Generated answer
    "tracker": Tracker      # Reasoning & metrics
}
```

---

## 🎨 UI Features

1. **Query Input** - Natural language input field
2. **Example Queries** - One-click pre-populated questions
3. **Response Display** - Formatted markdown output
4. **Chain-of-Thought** - Expandable reasoning view
5. **Performance Metrics** - Time, LLM calls, steps
6. **Query History** - Last 5 queries with replay
7. **Dataset Info** - Properties, tenants, date range

---

## 🧪 Testing & Validation

The system has been tested with:

✅ Property comparisons (2 properties)
✅ P&L calculations (with/without filters)
✅ Property details queries
✅ Tenant information queries
✅ Non-existent properties (error handling)
✅ Vague queries (fallback)
✅ Edge cases (partial names, typos)

---

## 🔮 Future Enhancements

1. **Caching** - Cache frequent queries
2. **Batch Processing** - Handle multiple queries at once
3. **Advanced Analytics** - Trend analysis, forecasting
4. **Multi-property Comparison** - Compare 3+ properties
5. **Natural Language Filters** - "Last quarter", "This year"
6. **Export** - Download results as CSV/PDF

---

## 📚 Code Quality

- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ Clean separation of concerns
- ✅ Error handling at every layer
- ✅ Performance monitoring
- ✅ Logging and debugging support

---

## 🎓 Key Design Decisions

### Why LangGraph?
- **Declarative workflow** - Easy to visualize and modify
- **State management** - Clean data passing between agents
- **Conditional edges** - Dynamic routing based on results

### Why Polars?
- **Fast** - 5-10x faster than Pandas
- **Memory efficient** - Lazy evaluation
- **SQL-like** - Familiar query syntax

### Why Llama 3.2-3B?
- **Free** - HuggingFace Inference API
- **Fast** - Small model = quick responses  
- **Good enough** - Sufficient for classification/extraction

### Why Chain-of-Thought?
- **Transparency** - Users see reasoning process
- **Debugging** - Easy to identify failure points
- **Trust** - Build confidence in AI decisions

---

## 💡 Best Practices Implemented

1. **Separation of Concerns**: Frontend / Backend / AI layers
2. **Fail Fast**: Validate early, provide clear errors
3. **Fallback Logic**: Always have a backup plan
4. **User Feedback**: Show progress, reasoning, and metrics
5. **Clean Code**: Type hints, docstrings, consistent naming
6. **Performance Tracking**: Measure everything
7. **Structured Prompts**: Few-shot examples, clear formats
8. **Robust Extraction**: LLM + regex fallbacks

---

*For setup instructions, see [QUICK_START.md](QUICK_START.md)*
*For full documentation, see [README.md](README.md)*

