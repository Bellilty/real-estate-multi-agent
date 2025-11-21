# 🏢 Multi-Agent Real Estate Assistant

A multi-agent system for real estate asset management built with **LangGraph** and **GPT-4o-mini**. The system handles natural language queries about property P&L, comparisons, and temporal analysis.

**Time Spent**: 6-8 hours  
**Framework**: LangGraph + Streamlit

---

## 📊 Overview

A multi-agent assistant that processes natural language queries about property financials using LangGraph orchestration.

**What it does**:

- P&L calculation for properties
- Property and temporal comparisons
- Follow-up questions with context
- Natural date parsing (Q1, December, etc.)
- Entity validation and helpful error messages

**Tech Stack**: LangGraph + GPT-4o-mini + Polars + Streamlit

---

## 🏗️ Architecture

### Multi-Agent System

The system uses **8 specialized agents** orchestrated by LangGraph:

#### **1. Router Agent** (`backend/agents/router.py`)

- Classifies user intent (pl_calculation, property_comparison, temporal_comparison, etc.)
- Uses LLM to analyze query and return intent + confidence

#### **2. Extractor Agent** (`backend/agents/extractor.py`)

- Extracts structured entities: properties, dates, tenants
- Returns JSON with extracted entities

#### **3. FollowUp Resolver** (`backend/agents/followup_resolver.py`)

- Detects follow-up questions (e.g., "And what about 2025?")
- Enriches query with conversation context

#### **4. Natural Date Agent** (`backend/agents/naturaldate_agent.py`)

- Normalizes date formats: "Q1" → "2024-Q1", "December" → "2024-M12"
- Handles ambiguous dates

#### **5. Validation Agent** (`backend/agents/validation_agent.py`)

- Validates entities against the dataset
- Returns status: `ok`, `missing`, or `ambiguous`
- Enables early exit if entities don't exist

#### **6. Disambiguation Agent** (`backend/agents/disambiguation_agent.py`)

- Handles fuzzy matches (e.g., "Building 18" → "Building 180")
- Requests clarification when multiple matches exist

#### **7. Query Agent** (`backend/agents/query.py`)

- Executes data queries using Polars
- Calculates P&L, handles comparisons and aggregations

#### **8. Formatter Agent** (`backend/agents/formatter.py`)

- Converts query results to natural language
- Formats numbers, percentages, and comparisons

### LangGraph Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                       USER QUERY                             │
│            "Show Building 180 in Q1 2024"                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NODE 1: FollowUpResolver                                    │
│  • Detects if query is a follow-up                          │
│  • Enriches with conversation context                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NODE 2: Router                                              │
│  • Classifies intent (8 types)                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NODE 3: Extractor                                           │
│  • Extracts properties, dates, tenants                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NODE 4: NaturalDateAgent                                    │
│  • Normalizes date formats                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NODE 5: ValidationAgent (ROUTING DECISION)                 │
│  • Validates entities against dataset                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    │  CONDITIONAL  │
                    │   BRANCHING   │
                    └───────┬───────┘
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
    [VALID]            [MISSING]          [AMBIGUOUS]
        ↓                   ↓                   ↓
┌───────────────┐   ┌──────────────┐   ┌──────────────────┐
│  QueryAgent   │   │ Clarification│   │ Disambiguation   │
│               │   │   Handler    │   │     Agent        │
│ • Execute SQL │   │ • Generate   │   │ • Fuzzy match    │
│ • Calculate   │   │   helpful    │   │ • Auto-resolve   │
│   P&L         │   │   error msg  │   │   or ask user    │
└───────────────┘   └──────────────┘   └──────────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NODE 6: Formatter                                           │
│  • Converts results to natural language                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    USER RESPONSE                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:

- Conditional routing based on validation status
- Early exit for invalid entities (no wasted queries)
- Self-healing with disambiguation
- Context-aware follow-up resolution

---

## 📁 Project Structure

```
Cortex-multi-agent-task/
├── backend/
│   ├── agents/              # 8 specialized agents
│   │   ├── router.py
│   │   ├── extractor.py
│   │   ├── followup_resolver.py
│   │   ├── naturaldate_agent.py
│   │   ├── validation_agent.py
│   │   ├── disambiguation_agent.py
│   │   ├── query.py
│   │   └── formatter.py
│   ├── core/
│   │   └── orchestrator.py  # LangGraph workflow
│   ├── data/
│   │   └── data_loader.py   # Polars-based data access
│   ├── llm/
│   │   └── llm_client.py    # GPT-4o-mini wrapper
│   └── utils/
│       ├── prompts.py       # Agent prompts
│       ├── tracking.py      # Chain-of-thought tracking
│       ├── conversation.py  # Context management
│       └── date_parser.py   # Date normalization
├── data/
│   └── cortex.parquet       # Real estate dataset
├── frontend/
│   └── streamlit_app.py     # Interactive UI
├── tests/
│   └── test_quick_validation.py
├── README.md
├── requirements.txt
└── run.sh
```

---

## 📊 Dataset

**File**: `data/cortex.parquet` (28KB)

### Schema

- `property_name`: Building name (e.g., "Building 180")
- `tenant_name`: Tenant identifier
- `ledger_type`: `revenue` or `expenses`
- `ledger_category`: Specific category
- `month`: Month identifier (e.g., "2024-M01")
- `quarter`: Quarter identifier (e.g., "2024-Q1")
- `year`: Year string ("2024", "2025")
- `profit`: Financial value

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

```bash
# Navigate to project
cd Cortex-multi-agent-task

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env.local` with your OpenAI API key:

```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env.local
```

Get a free API key at: https://platform.openai.com/api-keys

### Run

```bash
# Launch Streamlit UI
streamlit run frontend/streamlit_app.py

# Or use the script
./run.sh
```

Access at: **http://localhost:8501**

---

## 💬 Example Queries

### Simple P&L

```
"What is the P&L for Building 180 in 2024?"
```

→ Shows revenue, expenses, and net profit

### Property Comparison

```
"Compare Building 140 and Building 180 in 2024"
```

→ Shows profit comparison with breakdown

### Follow-up Question

```
User: "Show P&L for Building 180 in 2024"
Bot: [Shows 2024 results]

User: "And what about 2025?"
Bot: [Shows 2025 results with context maintained]
```

### Natural Date Parsing

```
"Show Building 140 in Q1 2024"
```

→ Automatically normalizes Q1 to 2024-Q1

### Invalid Entity

```
"Show P&L for Building 999"
```

→ "Building 999 not found. Available properties: Building 100, Building 140, Building 180..."

---

## ⚠️ Error Handling

The system handles:

- **Invalid properties**: Suggests valid alternatives
- **Missing dates**: Requests clarification
- **Ambiguous entities**: Uses fuzzy matching or asks for clarification
- **Invalid quarters**: Detects Q5, Q6, etc. as invalid

---

## 🧪 Testing

```bash
# Quick validation (7 tests)
python tests/test_quick_validation.py

# Unit tests for agents
python tests/test_new_agents.py
```

---

## 🎯 Challenges & Solutions

### Challenge 1: Follow-up Context Management

**Problem**: Follow-up questions like "And what about 2025?" lost context from previous queries.

**Solution**: Created a FollowUpResolverAgent that runs first in the pipeline, detects follow-up indicators ("and", "what about"), and enriches the query with conversation history before routing to other agents.

### Challenge 2: Entity Validation

**Problem**: Queries with invalid entities (e.g., "Building 999") proceeded to execution, causing confusing errors.

**Solution**: Implemented a validation-first approach with 3-way routing (ok/missing/ambiguous) that validates entities against the dataset before query execution, providing early exit and helpful suggestions.

### Challenge 3: Date Format Variations

**Problem**: Users input dates in many formats: "Q1", "2024-Q1", "December", etc.

**Solution**: Built a NaturalDateAgent with a custom parser that normalizes all formats to a consistent schema (Q1 → 2024-Q1, December → 2024-M12) and detects invalid dates.

---


## 🚀 Future Improvements

Given more time, I would add:

1. **Structured LLM Outputs** - Use Pydantic models with `with_structured_output()` to eliminate JSON parsing errors
2. **Extended Date Ranges** - Handle "last quarter", "YTD" with proper date arithmetic
3. **N-Property Comparisons** - Support "compare all buildings in 2024"
4. **Query Caching** - Cache repeated queries to reduce LLM calls
5. **Simple Charts** - Add bar charts for revenue/expense breakdowns
6. **Confidence Scores** - Display router confidence in UI

---

## 🛠️ Tech Stack

- **LLM**: GPT-4o-mini (OpenAI)
- **Framework**: LangGraph
- **UI**: Streamlit
- **Data**: Polars
- **Language**: Python 3.11

