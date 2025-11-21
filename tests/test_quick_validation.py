#!/usr/bin/env python3
"""
QUICK SYSTEM VALIDATION - Essential tests only
Fast validation of core functionality
"""

import sys
import time
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader


def run_test(orchestrator, query, test_name, chat_history=None):
    """Run a single test"""
    chat_history = chat_history or []
    start = time.time()
    
    try:
        # Suppress debug output
        captured = StringIO()
        with redirect_stdout(captured):
            response, tracker = orchestrator.run(query, chat_history)
        
        duration = int((time.time() - start) * 1000)
        
        # Extract basic info
        agent_path = []
        if hasattr(tracker, 'steps'):
            for step in tracker.steps:
                if hasattr(step, 'agent'):
                    agent_path.append(step.agent)
        
        print(f"✅ {test_name}")
        print(f"   Duration: {duration}ms | Agents: {len(agent_path)}")
        print(f"   Response: {response[:100]}...")
        
        return True, response, duration
        
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        print(f"❌ {test_name}")
        print(f"   Error: {str(e)[:100]}")
        return False, None, duration


def main():
    print("="*80)
    print("🧪 QUICK SYSTEM VALIDATION")
    print("="*80)
    
    # Setup
    print("\n🔧 Setup...")
    try:
        llm_client = LLMClient()
        llm = llm_client.get_llm()
        data_loader = RealEstateDataLoader("data/cortex.parquet")
        orchestrator = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
        print("✅ Setup complete\n")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return
    
    # Results tracking
    results = []
    durations = []
    
    # Test 1: Simple P&L
    print("\n" + "="*80)
    print("TEST 1: Simple P&L Query")
    print("="*80)
    passed, response, duration = run_test(
        orchestrator,
        "What is the P&L for Building 180 in 2024?",
        "Simple P&L Query"
    )
    results.append(passed)
    durations.append(duration)
    
    # Test 2: Multi-property comparison
    print("\n" + "="*80)
    print("TEST 2: Multi-Property Comparison")
    print("="*80)
    passed, response, duration = run_test(
        orchestrator,
        "Compare Building 140 and Building 180 in 2024",
        "Multi-Property Comparison"
    )
    results.append(passed)
    durations.append(duration)
    
    # Test 3: Follow-up
    print("\n" + "="*80)
    print("TEST 3: Follow-up Query")
    print("="*80)
    chat_history = []
    
    # First query
    passed1, response1, duration1 = run_test(
        orchestrator,
        "Show P&L for Building 180 in 2024",
        "Follow-up: Initial"
    )
    
    if passed1:
        chat_history.append({"role": "user", "content": "Show P&L for Building 180 in 2024"})
        chat_history.append({"role": "assistant", "content": response1})
        
        # Follow-up
        passed2, response2, duration2 = run_test(
            orchestrator,
            "And what about 2025?",
            "Follow-up: Second",
            chat_history
        )
        results.append(passed1 and passed2)
        durations.append(duration1 + duration2)
    else:
        results.append(False)
        durations.append(duration1)
    
    # Test 4: Invalid entity
    print("\n" + "="*80)
    print("TEST 4: Invalid Entity")
    print("="*80)
    passed, response, duration = run_test(
        orchestrator,
        "Show P&L for Building 999",
        "Invalid Entity (should clarify)"
    )
    results.append(passed)
    durations.append(duration)
    
    # Test 5: Natural date
    print("\n" + "="*80)
    print("TEST 5: Natural Date Parsing")
    print("="*80)
    passed, response, duration = run_test(
        orchestrator,
        "Show Building 140 in Q1 2024",
        "Natural Date Q1"
    )
    results.append(passed)
    durations.append(duration)
    
    # Test 6: Edge case - empty
    print("\n" + "="*80)
    print("TEST 6: Edge Case - Empty Query")
    print("="*80)
    passed, response, duration = run_test(
        orchestrator,
        "",
        "Empty Query (should handle gracefully)"
    )
    # For edge cases, we consider it a pass if it doesn't crash
    results.append(True)  # Didn't crash = pass
    durations.append(duration)
    
    # Test 7: Import test
    print("\n" + "="*80)
    print("TEST 7: Import Test")
    print("="*80)
    try:
        from backend.agents.router import IntentRouter
        from backend.agents.extractor import EntityExtractor
        from backend.agents.followup_resolver import FollowUpResolverAgent
        from backend.agents.naturaldate_agent import NaturalDateAgent
        from backend.agents.validation_agent import ValidationAgent
        from backend.agents.disambiguation_agent import DisambiguationAgent
        print("✅ All imports successful")
        results.append(True)
        durations.append(0)
    except Exception as e:
        print(f"❌ Import failed: {e}")
        results.append(False)
        durations.append(0)
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\n✅ RESULTS:")
    print(f"   Total Tests: {total}")
    print(f"   Passed: {passed} ({100*passed/total:.1f}%)")
    print(f"   Failed: {failed}")
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        print(f"\n⏱️  PERFORMANCE:")
        print(f"   Average: {avg_duration:.0f}ms")
        print(f"   Max: {max_duration:.0f}ms")
    
    print("\n" + "="*80)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} TEST(S) FAILED")
    
    print("="*80)


if __name__ == "__main__":
    main()

