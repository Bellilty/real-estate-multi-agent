#!/usr/bin/env python3
"""
Backend Testing Script
Test the orchestrator directly without Streamlit
"""

import sys
sys.path.insert(0, 'backend')

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader

# Initialize
print("=" * 80)
print("🧪 BACKEND TESTING")
print("=" * 80)

llm = LLMClient()
data_loader = RealEstateDataLoader('data/cortex.parquet')
orch = RealEstateOrchestrator(llm, data_loader)

# Test 1: Follow-up questions (CHAT CONTEXT)
print("\n" + "=" * 80)
print("TEST 1: FOLLOW-UP QUESTIONS (CHAT CONTEXT)")
print("=" * 80)

queries = [
    "What is the P&L for Building 180 in 2024?",
    "And in 2025?",
    "What about Building 140?",
]

chat_history = []

"""for i, query in enumerate(queries, 1):
    print(f"\n{'='*80}")
    print(f"Query {i}: {query}")
    print(f"{'='*80}")
    
    response, tracker = orch.run(query, chat_history=chat_history)
    
    # Add to chat history
    chat_history.append({"role": "user", "content": query})
    chat_history.append({"role": "assistant", "content": response})
    
    print(f"\n📊 RESULT:")
    print(f"Response: {response}")
    print(f"Steps: {len(tracker.steps)}")
    print(f"Intent: {tracker.steps[0].output_data.get('intent') if tracker.steps else 'N/A'}")
    print(f"Entities: {tracker.steps[1].output_data if len(tracker.steps) > 1 else 'N/A'}")
"""
# Test 2: Tenant query
print("\n" + "=" * 80)
print("TEST 2: TENANT QUERY")
print("=" * 80)

query = "What properties does Tenant 8 occupy?"
print(f"Query: {query}")

response, tracker = orch.run(query)

print(f"\n📊 RESULT:")
print(f"Response: {response}")
print(f"Steps: {len(tracker.steps)}")
print(f"Intent: {tracker.steps[0].output_data.get('intent') if tracker.steps else 'N/A'}")
print(f"Entities: {tracker.steps[1].output_data if len(tracker.steps) > 1 else 'N/A'}")
print(f"Query result: {tracker.steps[2].output_data if len(tracker.steps) > 2 else 'N/A'}")

# Test 3: Invalid building
print("\n" + "=" * 80)
print("TEST 3: INVALID BUILDING")
print("=" * 80)

query = "What is the P&L for Building 18?"
print(f"Query: {query}")

response, tracker = orch.run(query)

print(f"\n📊 RESULT:")
print(f"Response: {response}")
print(f"Steps: {len(tracker.steps)}")
print(f"Intent: {tracker.steps[0].output_data.get('intent') if tracker.steps else 'N/A'}")
print(f"Entities: {tracker.steps[1].output_data if len(tracker.steps) > 1 else 'N/A'}")

print("\n" + "=" * 80)
print("✅ TESTS COMPLETE")
print("=" * 80)

