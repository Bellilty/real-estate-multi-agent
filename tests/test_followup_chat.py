"""
Test Follow-up Queries in Chat Context
Tests all queries from manual_test_queries.py and follow-up sequences
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader


# All queries from manual_test_queries.py
TEST_QUERIES = [
    "What is the P&L for Building 180 in 2024?",
    "Compare Building 100 and Building 120 in 2025",
    "Show me the tenants for Building 140",
    "List all properties",
    "Give me the highest expense category in 2024",
    "What is the revenue for all properties in Q1 2025?",
    "Compare Q1 and Q2 2024 for Building 180",
    "Show all tenants",
    "Which property made the most profit in 2024?",
    "Total expenses for Building 200 in March 2025",
]

# Follow-up test sequences
FOLLOWUP_SEQUENCES = [
    {
        "name": "P&L Follow-up Sequence",
        "queries": [
            "What is the P&L for Building 180 in 2024?",
            "And in 2025?",
            "What about Building 140?",
            "And overall?",
        ]
    },
    {
        "name": "Comparison Follow-up Sequence",
        "queries": [
            "Compare Building 100 and Building 120 in 2025",
            "What about Building 140?",
            "And for 2024?",
        ]
    },
    {
        "name": "Temporal Comparison Follow-up",
        "queries": [
            "Compare Q1 and Q2 2024 for Building 180",
            "What about Q3?",
            "And for Building 140?",
        ]
    },
    {
        "name": "Property Details Follow-up",
        "queries": [
            "Show me the tenants for Building 140",
            "What about Building 180?",
            "What is the P&L for Building 140?",
        ]
    },
    {
        "name": "All Buildings Follow-up",
        "queries": [
            "What is the P&L for Building 180 in 2024?",
            "And for all the buildings?",
        ]
    },
]


def test_individual_queries(orchestrator):
    """Test all queries individually (no chat context)"""
    print("\n" + "="*80)
    print("📋 TEST 1: Individual Queries (No Chat Context)")
    print("="*80)
    
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] {query}")
        try:
            response, tracker = orchestrator.run(query, chat_history=None)
            success = not response.startswith("❌")
            results.append({
                "query": query,
                "success": success,
                "response": response,
                "agents": len(tracker.steps)
            })
            status = "✅" if success else "❌"
            print(f"  {status} {response[:80]}...")
        except Exception as e:
            results.append({
                "query": query,
                "success": False,
                "error": str(e),
                "agents": 0
            })
            print(f"  ❌ Error: {e}")
    
    passed = sum(1 for r in results if r["success"])
    print(f"\n📊 Results: {passed}/{len(results)} passed")
    return results


def test_followup_sequence(orchestrator, sequence):
    """Test a follow-up sequence with chat context"""
    print(f"\n{'='*80}")
    print(f"💬 {sequence['name']}")
    print("="*80)
    
    chat_history = []
    results = []
    
    for i, query in enumerate(sequence["queries"], 1):
        print(f"\n[{i}/{len(sequence['queries'])}] Query: {query}")
        print(f"  Chat history length: {len(chat_history)}")
        
        try:
            response, tracker = orchestrator.run(query, chat_history=chat_history)
            success = not response.startswith("❌")
            
            # Check if follow-up was detected
            is_followup = False
            for step in tracker.steps:
                if step.agent == "FollowUpResolver":
                    is_followup = step.output_data.get("is_followup", False)
                    break
            
            results.append({
                "query": query,
                "success": success,
                "is_followup": is_followup,
                "response": response[:100] + "..." if len(response) > 100 else response,
                "agents": len(tracker.steps)
            })
            
            status = "✅" if success else "❌"
            followup_status = "🔄" if is_followup else "🆕"
            print(f"  {status} {followup_status} {response[:80]}...")
            
            # Add to chat history (format: {"user": "...", "assistant": "..."})
            chat_history.append({"user": query})
            chat_history.append({"assistant": response})
            
        except Exception as e:
            results.append({
                "query": query,
                "success": False,
                "error": str(e),
                "agents": 0
            })
            print(f"  ❌ Error: {e}")
            # Still add to history to continue test
            chat_history.append({"user": query})
            chat_history.append({"assistant": f"Error: {e}"})
    
    passed = sum(1 for r in results if r["success"])
    followups_detected = sum(1 for r in results[1:] if r.get("is_followup", False))
    print(f"\n📊 Results: {passed}/{len(results)} passed | {followups_detected} follow-ups detected")
    return results


def main():
    print("="*80)
    print("🧪 FOLLOW-UP CHAT TEST SUITE")
    print("="*80)
    
    # Initialize
    print("\n🔧 Initializing system...")
    try:
        llm_client = LLMClient()
        llm = llm_client.get_llm()
        data_loader = RealEstateDataLoader("data/cortex.parquet")
        orchestrator = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
        print("✅ System initialized\n")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return
    
    # Test 1: Individual queries
    individual_results = test_individual_queries(orchestrator)
    
    # Test 2: Follow-up sequences
    print("\n" + "="*80)
    print("📋 TEST 2: Follow-up Sequences (With Chat Context)")
    print("="*80)
    
    followup_results = []
    for sequence in FOLLOWUP_SEQUENCES:
        seq_results = test_followup_sequence(orchestrator, sequence)
        followup_results.extend(seq_results)
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    
    individual_passed = sum(1 for r in individual_results if r["success"])
    followup_passed = sum(1 for r in followup_results if r["success"])
    total_followups = sum(1 for r in followup_results[1:] if r.get("is_followup", False))
    expected_followups = sum(len(seq["queries"]) - 1 for seq in FOLLOWUP_SEQUENCES)
    
    print(f"\n✅ Individual Queries: {individual_passed}/{len(individual_results)} passed")
    print(f"✅ Follow-up Queries: {followup_passed}/{len(followup_results)} passed")
    print(f"🔄 Follow-ups Detected: {total_followups}/{expected_followups} (expected)")
    
    if individual_passed == len(individual_results) and followup_passed == len(followup_results):
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED")
    
    print("="*80)


if __name__ == "__main__":
    main()

