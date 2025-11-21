# 🏢 Multi-Agent Real Estate Assistant

A multi-agent system for real estate asset management built with **LangGraph** and **GPT-4o-mini**. The system handles natural language queries about property P&L, comparisons, and temporal analysis.

**Time Spent**: 6-8 hours  
**Framework**: LangGraph + Streamlit

---

## 📊 Overview

This project demonstrates a multi-agent architecture where specialized agents work together to:

- Classify user intent
- Extract entities (properties, dates, tenants)
- Validate and disambiguate inputs
- Execute queries on real estate data
- Format natural language responses

The system handles follow-up questions, natural date parsing (Q1, "December"), and provides helpful error messages when entities are not found.

---

## 🏗️ Architecture

### Multi-Agent System

The system uses **8 specialized agents** orchestrated by LangGraph:

#### **1. Router Agent** (`backend/agents/router.py`)

- Classifies user intent into categories:
  - `pl_calculation`: P&L for a single property
  - `property_comparison`: Compare two properties
  - `temporal_comparison`: Compare time periods
  - `multi_entity_query`: Multiple properties/periods
  - `property_details`, `tenant_info`, `general_query`, `unsupported`
- Uses LLM to analyze query and return intent + confidence

#### **2. Extractor Agent** (`backend/agents/extractor.py`)

- Extracts structured entities from natural language:
  - Properties (e.g., "Building 180")
  - Dates (year, quarter, month)
  - Tenants
- Returns JSON with extracted entities

#### **3. FollowUp Resolver** (`backend/agents/followup_resolver.py`)

- Detects follow-up questions (e.g., "And what about 2025?")
- Enriches query with context from conversation history
- Enables multi-turn conversations

#### **4. Natural Date Agent** (`backend/agents/naturaldate_agent.py`)

- Normalizes date formats:
  - "Q1" → "2024-Q1"
  - "December" → "2024-M12"
  - Handles ambiguous dates (e.g., "Q5" is invalid)
- Uses custom date parser for consistency

#### **5. Validation Agent** (`backend/agents/validation_agent.py`)

- Validates extracted entities against the dataset
- Returns status: `ok`, `missing`, or `ambiguous`
- Provides suggestions for invalid entities
- Enables early exit if entities don't exist

#### **6. Disambiguation Agent** (`backend/agents/disambiguation_agent.py`)

- Handles fuzzy matches (e.g., "Building 18" → "Building 180")
- Resolves partial property names
- Requests clarification when multiple matches exist

#### **7. Query Agent** (`backend/agents/query.py`)

- Executes data queries using Polars
- Calculates P&L (revenue - expenses)
- Handles comparisons and aggregations
- Returns structured results

#### **8. Formatter Agent** (`backend/agents/formatter.py`)

- Converts query results to natural language
- Formats numbers, percentages, and comparisons
- Generates user-friendly responses

### LangGraph Workflow

```
User Query
    ↓
FollowUpResolver (enriches with context)
    ↓
Router (classifies intent)
    ↓
Extractor (extracts entities)
    ↓
NaturalDateAgent (normalizes dates)
    ↓
ValidationAgent (validates entities)
    ↓
    ├─ VALID → QueryAgent
    ├─ MISSING → ClarificationHandler
    └─ AMBIGUOUS → DisambiguationAgent → QueryAgent
    ↓
Formatter (generates response)
    ↓
User Response
```

The orchestrator (`backend/core/orchestrator.py`) uses **conditional branching** based on validation results, making the system self-healing.

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
│   ├── tools/
│   │   └── search_tool.py   # Entity search
│   └── utils/
│       ├── prompts.py       # Agent prompts
│       ├── tracking.py      # Chain-of-thought tracking
│       ├── conversation.py  # Context management
│       ├── date_parser.py   # Date normalization
│       └── clarification.py # Error handling
├── data/
│   └── cortex.parquet       # Real estate dataset
├── frontend/
│   └── streamlit_app.py     # Interactive UI
├── tests/
│   ├── test_new_agents.py
│   ├── test_quick_validation.py
│   └── explore_data.ipynb
├── README.md
├── requirements.txt
└── run.sh
```

---

## 📊 Dataset

**File**: `data/cortex.parquet`  
**Format**: Parquet (optimized for Polars)  
**Size**: 28KB

### Schema

- `entity_name`: Entity identifier
- `property_name`: Building name (e.g., "Building 180", "Building 140")
- `tenant_name`: Tenant identifier
- `ledger_type`: `revenue` or `expenses`
- `ledger_category`: Specific category (e.g., "revenue_rent_taxed")
- `month`: Month identifier (e.g., "2024-M01")
- `quarter`: Quarter identifier (e.g., "2024-Q1")
- `year`: Year string ("2024", "2025")
- `profit`: Financial value

---

## 🚀 Setup

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

```bash
# Clone repository
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
- **Empty queries**: Returns helpful error message

---

## 🧪 Testing

```bash
# Quick validation (7 tests)
python tests/test_quick_validation.py

# Unit tests for agents (15 tests)
python tests/test_new_agents.py

# Backend tests
python tests/test_backend.py
```

---

## 🎯 Challenges & Solutions

### Challenge 1: Multi-Entity Extraction

**Problem**: LLM struggled to extract multiple properties from complex queries like "Show PropCo in Q1, Building 180 in Q2"  
**Solution**: Simplified prompts to JSON-only output format and added explicit examples for multi-entity patterns

### Challenge 2: Follow-up Context

**Problem**: Follow-up questions like "And what about 2025?" lost context  
**Solution**: Created FollowUpResolverAgent that enriches queries with conversation history before routing

### Challenge 3: Date Format Variations

**Problem**: Users input dates as "Q1", "December", "2024-Q1", etc.  
**Solution**: Built NaturalDateAgent with a custom parser to normalize all formats to consistent schema

### Challenge 4: Invalid Entity Handling

**Problem**: Queries proceeded even with invalid entities, causing errors downstream  
**Solution**: Added ValidationAgent with 3-way routing (ok/missing/ambiguous) for early exit and helpful error messages

### Challenge 5: Case Sensitivity

**Problem**: "building 180" vs "Building 180" caused mismatches  
**Solution**: Added case-insensitive matching with `LOWER()` in all data queries

---

## ⏱️ Time Breakdown (6-8 hours)

- **Hour 1-2**: Dataset exploration, basic LangGraph setup, core agents (Router, Extractor)
- **Hour 3-4**: Query execution, data loader with Polars, basic Streamlit UI
- **Hour 5-6**: Advanced agents (FollowUpResolver, NaturalDate, Validation, Disambiguation)
- **Hour 7**: Testing, debugging, error handling
- **Hour 8**: UI polish, Chain-of-Thought display, documentation

---

## 🚀 Future Improvements

Given more time, I would add:

1. **Structured LLM Outputs** - Use Pydantic models with LangChain's `with_structured_output()` instead of JSON parsing to eliminate parsing errors

2. **Extended Date Ranges** - Handle "last quarter", "this year", "YTD" with proper date arithmetic

3. **Fuzzy Matching Thresholds** - Add configurable similarity scores for disambiguation (currently uses simple string matching)

4. **Better UI Formatting** - Add color coding for positive/negative values, format large numbers with commas

5. **N-Property Comparisons** - Extend comparison beyond 2 properties to support "compare all buildings in 2024"

6. **Query Caching** - Cache repeated queries to reduce LLM calls and improve response time

7. **Simple Charts** - Add Streamlit bar charts for revenue/expense breakdowns and trend visualization

8. **Additional Test Coverage** - Add unit tests for edge cases like empty datasets, malformed dates, special characters

9. **Confidence Scores** - Display router confidence in UI to help users understand when queries might be misclassified

10. **Export Functionality** - Add CSV/Excel export for query results

---

## 🛠️ Tech Stack

- **LLM**: GPT-4o-mini (OpenAI)
- **Framework**: LangGraph
- **UI**: Streamlit
- **Data**: Polars
- **Language**: Python 3.11

---

## 📝 Notes

- This project was completed as a home assignment in 6-8 hours
- The focus was on demonstrating multi-agent orchestration with LangGraph
- The system handles the core requirements: P&L calculation, comparisons, follow-ups, and error handling
- Some advanced features (caching, charts, extensive testing) were deprioritized due to time constraints

---

**Built in 6-8 hours for an AI Developer home assignment**
