# 🚀 Quick Start Guide

## Setup (5 minutes)

### 1. Verify Your Environment

You already have the venv set up! Make sure you're in it:
```bash
cd /Users/simonbellilty/VSproject/Cortex-multi-agent-task
source venv/bin/activate
```

### 2. Set Your HuggingFace Token

Your token should already be in `.env.local`. Verify it:
```bash
cat .env.local
```

If not set, create it:
```bash
echo "HUGGINGFACE_API_TOKEN=hf_YOUR_TOKEN_HERE" > .env.local
```

### 3. Launch the Application

**Option A: Using the launch script**
```bash
./run.sh
```

**Option B: Direct command**
```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`

## 🎯 Try These Example Queries

Once the app is running, try:

1. **"What is the P&L for Building 17?"**
   - Tests: P&L calculation, property identification

2. **"Compare Building 140 to Building 180"**
   - Tests: Property comparison, multi-entity extraction

3. **"What is the total P&L for 2024?"**
   - Tests: Time period extraction, aggregation

4. **"Tell me about Tenant 12"**
   - Tests: Tenant info retrieval

5. **"Show me all properties"**
   - Tests: General data query, fallback handling

## 📊 What to Expect

### First Query (may take 30-60 seconds)
- LLM cold start on HuggingFace
- Model initialization
- Data loading

### Subsequent Queries (faster, ~5-10 seconds)
- Cached model
- Only LLM inference time

### Workflow You'll See

In the terminal, you'll see the multi-agent workflow:
```
🚀 Starting Multi-Agent Workflow
================================
Query: What is the P&L for Building 17?

🔀 Router: Classifying intent...
   Intent: pl_calculation (confidence: high)
   Reason: User explicitly asks for P&L

🔍 Extractor: Extracting entities...
   Entities: {'property': 'Building 17', 'year': None, 'quarter': None, 'month': None}

🗄️  Query: Executing query...
   ✅ Query successful

💬 Response: Formatting answer...
   ✅ Response generated

✅ Workflow Complete
```

## 🐛 Troubleshooting

### "HuggingFace API token not found"
```bash
echo "HUGGINGFACE_API_TOKEN=your_token" > .env.local
```

### "Data file not found"
```bash
# Check if the file exists
ls -la data/cortex.parquet
```

### "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Rate Limit Errors
- HuggingFace free tier has limits
- Wait a few minutes and try again
- Or upgrade to Pro account

## 📹 Next Steps for Demo Video

1. Show the UI
2. Run 3-4 different query types
3. Show the terminal output (multi-agent workflow)
4. Show error handling (try a non-existent property)
5. Show the data summary in sidebar

## 🎥 Recommended Demo Flow

1. **Introduction** (30 sec)
   - Show the landing page
   - Explain the sidebar with dataset info

2. **Simple Query** (1 min)
   - "What is the P&L for Building 17?"
   - Show terminal workflow
   - Show formatted response

3. **Complex Query** (1 min)
   - "Compare Building 140 to Building 180"
   - Highlight multi-step reasoning

4. **Error Handling** (30 sec)
   - Try "What is Building 999?"
   - Show helpful error message

5. **Wrap-up** (30 sec)
   - Show query history
   - Quick architecture overview

Total: ~3-4 minutes

## 📝 Architecture Summary for Video

```
User Query → Router Agent → Extractor Agent → Query Agent → Response Agent → User
              (Intent)      (Entities)        (Data)         (Format)
```

Powered by:
- **LangGraph** for orchestration
- **Llama 3.2-3B** for NLU
- **Polars** for fast data queries
- **Streamlit** for UI

## 🎨 UI Features to Highlight

✅ Natural language input
✅ Example queries for quick testing
✅ Sidebar with dataset stats
✅ Query history
✅ Formatted markdown responses
✅ Real-time agent workflow (in terminal)

---

**Questions?** Check the main README.md for full documentation!

