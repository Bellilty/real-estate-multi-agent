# 🏢 Multi-Agent Real Estate Assistant

A multi-agent system for real estate asset management built with **LangGraph** and **GPT-4o-mini**. The system handles natural language queries about property P&L, comparisons, and temporal analysis.

**Time Spent**: 6-8 hours  
**Framework**: LangGraph + Streamlit

---

## 📊 Overview

A multi-agent assistant that processes natural language queries about property financials using LangGraph orchestration.

**What it does**:

- P&L calculation for properties (single or multiple years)
- Property and temporal comparisons (Q1 vs Q2, 2024 vs 2025)
- Follow-up questions with context ("And for 2025?", "And overall?")
- Natural date parsing (Q1, December, last quarter, etc.)
- Entity validation with helpful error messages
- Invalid data detection (e.g., "Building 180 in 2032")

**Tech Stack**: LangGraph + GPT-4o-mini + Polars + Streamlit

**Scope**: This prototype focuses on **P&L calculations and comparisons**. Advanced queries (temporal analysis, rankings, trends) are documented as future improvements.

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

→ Shows revenue, expenses, and net profit for 2024

### Temporal Comparison

```
"Compare Q1 2024 and Q2 2024 for Building 140"
```

→ Shows profit comparison between quarters with breakdown

### Property Comparison

```
"Compare Building 140 and Building 180 in 2024"
```

→ Shows profit comparison between properties

### Follow-up Questions

```
User: "Show P&L for Building 180 in 2024"
Bot: "The total P&L for Building 180 is $303,598.25..."

User: "And for 2025?"
Bot: "The total P&L for Building 180 is $81,301.78..."

User: "And overall?"
Bot: "The total P&L for Building 180 is $384,900.03..."
```

→ Context maintained across conversation, "overall" aggregates all years

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

### Invalid Year

```
"Show P&L for Building 180 in 2032"
```

→ "No financial data available for Building 180 in 2032. Please try a different time period."

---

## ⚠️ Error Handling

The system handles:

- **Invalid properties**: Suggests valid alternatives
- **Invalid years**: Detects when no data exists (e.g., 2032) and provides clear error messages
- **Missing dates**: Requests clarification
- **Ambiguous entities**: Uses fuzzy matching or asks for clarification
- **Invalid quarters**: Detects Q5, Q6, etc. as invalid
- **"Overall" queries**: Aggregates data across all available years when user says "overall" or "in total"

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

### Challenge 4: Temporal Comparisons

**Problem**: Comparing multiple time periods (e.g., "Q1 vs Q2") required extracting multiple dates and ensuring correct pairing with years.

**Solution**: Enhanced the Extractor to handle lists of quarters/months, and updated the orchestrator to sync normalized quarters with the periods list after NaturalDateAgent processing.

### Challenge 5: "Overall" Follow-up Queries

**Problem**: When users asked "And overall?" after specific year queries, the system would return the last year's data instead of aggregating all years.

**Solution**: Implemented a `clear_timeframes` flag in FollowUpResolver that detects "overall" indicators and removes all temporal entities, allowing QueryAgent to aggregate across all available data.

---

## ⚠️ Current Limitations

This is a **6-8 hour prototype** focused on core P&L and comparison queries. The following query types are **not yet supported**:

### Temporal Analysis Queries

**Not Supported**:

```
"In which month of 2025 did Building 17 record its highest profit?"
"Show Building 17 P&L for each month in 2025"
```

**Why**: Requires a new intent (`temporal_analysis`) and aggregation logic to group by month, calculate totals, and rank results.

**Workaround**: Ask for specific months individually:

```
"What is the P&L for Building 17 in January 2025?"
"What is the P&L for Building 17 in February 2025?"
```

### Ranking Queries

**Not Supported**:

```
"What are the top 3 most profitable properties?"
"Which building has the best profit margin?"
```

**Why**: Requires ranking logic and multi-property aggregation with sorting.

### Trend Analysis

**Not Supported**:

```
"Is Building 180's profit increasing or decreasing?"
"Show the trend for Building 140 over time"
```

**Why**: Requires time-series analysis and trend detection algorithms.

---

## 🚀 Future Improvements

Given more time (estimated +10-12 hours), I would add:

### High Priority (Production Readiness)

1. **Temporal Analysis Intent** (3-4h)

   - New intent: `temporal_analysis`
   - Support for "highest/lowest/average by month/quarter"
   - QueryAgent methods: `_query_temporal_analysis()` with GROUP BY + ORDER BY
   - Example: "Which month had the highest profit for Building 17?"

2. **Ranking & Top-N Queries** (2-3h)

   - New intent: `ranking_query`
   - Support for "top 3", "best", "worst"
   - Multi-property aggregation with LIMIT
   - Example: "What are the top 3 most profitable properties in 2024?"

3. **Multi-Month Breakdown** (2h)
   - Handle "show P&L for each month in 2025"
   - Return structured list of monthly results
   - Formatter: Display as table or list

### Medium Priority (Enhanced UX)

4. **Structured LLM Outputs** (2h)

   - Use Pydantic models with `with_structured_output()` to eliminate JSON parsing errors

5. **Query Caching** (1-2h)

   - Cache repeated queries to reduce LLM calls and improve response time

6. **Simple Charts** (2h)
   - Add bar charts for revenue/expense breakdowns in Streamlit
   - Monthly trend visualization

### Low Priority (Nice to Have)

7. **Confidence Scores** (1h)

   - Display router confidence and validation status in UI

8. **Better Disambiguation** (1h)

   - Rank fuzzy match candidates by relevance score

9. **Extended Date Ranges** (1h)
   - Handle "YTD", "last 6 months" with proper date arithmetic

---

## 🛠️ Tech Stack

- **LLM**: GPT-4o-mini (OpenAI)
- **Framework**: LangGraph
- **UI**: Streamlit
- **Data**: Polars
- **Language**: Python 3.11
