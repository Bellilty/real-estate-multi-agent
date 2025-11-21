# 🚀 Setup Guide: Switching to GPT-4o-mini

## ✅ What's Changed

We've switched from **Llama 3.2-3B (HuggingFace)** to **GPT-4o-mini (OpenAI)** for:

- ✅ Better entity extraction accuracy
- ✅ More reliable formatting
- ✅ Improved handling of complex queries
- ✅ Native support for multi-turn conversations

## 📝 Setup Steps

### 1. Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-...`)

### 2. Update `.env.local`

Open `/Users/simonbellilty/VSproject/Cortex-multi-agent-task/.env.local` and add:

```bash
# OpenAI API Key for GPT-4o-mini
OPENAI_API_KEY=sk-proj-your-key-here

# You can keep your HuggingFace token as backup
# HUGGINGFACE_API_TOKEN=hf_...
```

### 3. Restart Streamlit

```bash
cd /Users/simonbellilty/VSproject/Cortex-multi-agent-task
source venv/bin/activate
streamlit run frontend/streamlit_app.py --server.port 8502
```

## 💰 Cost

GPT-4o-mini is very affordable:

- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens

**Example**: A typical query session (~10 queries) costs approximately **$0.02-0.05**.

For testing purposes, OpenAI gives you **$5 free credits** on new accounts.

## 🧪 Test the Setup

Run this to verify:

```bash
cd /Users/simonbellilty/VSproject/Cortex-multi-agent-task
source venv/bin/activate
python backend/llm/llm_client.py
```

You should see:

```
✅ Initialized LLM: gpt-4o-mini
🤖 Testing LLM...
Response: A P&L (Profit and Loss) statement is a financial report...
```

## 🔄 Reverting to HuggingFace (if needed)

If you need to switch back, just remove `OPENAI_API_KEY` from `.env.local`.
The system will automatically fall back to using `HUGGINGFACE_API_TOKEN`.

## 📊 Expected Improvements

With GPT-4o-mini, you should see:

- ✅ Correct extraction of all 3 entities in multi-queries ("PropCo in Q1, Building 180 in Q2, Building 140 in Q3")
- ✅ Proper year clarification ("Which year did you mean for Q1? (2024 or 2025)")
- ✅ Clean, formatted responses without special characters
- ✅ Better handling of follow-up questions

## 🐛 Troubleshooting

**Error: "Incorrect API key"**

- Check that your key starts with `sk-proj-` or `sk-`
- Make sure there are no spaces or quotes around the key in `.env.local`

**Error: "Rate limit exceeded"**

- You've used your free credits
- Add billing info at https://platform.openai.com/account/billing

**Still using HuggingFace?**

- Make sure `OPENAI_API_KEY` is set in `.env.local`
- Restart Streamlit completely (kill the process and restart)
