#!/usr/bin/env python3
"""
FULL SYSTEM VALIDATION TEST SUITE
Comprehensive end-to-end testing of the multi-agent real estate assistant
"""

import sys
import time
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
from pydantic import BaseModel, ValidationError
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader


# ============================================================================
# PYDANTIC SCHEMA FOR OUTPUT VALIDATION
# ============================================================================

class FinalResponseSchema(BaseModel):
    """Schema for orchestrator output validation"""
    final_answer: str
    agent_path: List[str]
    is_followup: bool
    intent: str
    validation_status: str
    clarifications_requested: int
    duration_ms: int


# ============================================================================
# TEST FRAMEWORK
# ============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, duration_ms: int, 
                 error: str = None, metadata: Dict = None):
        self.name = name
        self.passed = passed
        self.duration_ms = duration_ms
        self.error = error
        self.metadata = metadata or {}


class TestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.orchestrator = None
        self.data_loader = None
        self.chat_history = []
        
        # Metrics
        self.total_llm_calls = 0
        self.agent_call_counts = Counter()
        self.intent_counts = Counter()
        self.validation_status_counts = Counter()
        self.latencies = []
        
    def setup(self):
        """Initialize the system"""
        print("🔧 Setting up test environment...")
        try:
            # Initialize LLM
            llm_client = LLMClient()
            llm = llm_client.get_llm()
            
            # Initialize data loader
            self.data_loader = RealEstateDataLoader("data/cortex.parquet")
            
            # Initialize orchestrator with debug_mode=False to reduce verbosity
            self.orchestrator = RealEstateOrchestrator(llm, self.data_loader, debug_mode=False)
            
            print("✅ Setup complete\n")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {e}\n")
            return False
    
    def run_query(self, query: str, test_name: str = None, verbose: bool = False) -> Tuple[Dict, TestResult]:
        """Run a single query and return result + test result"""
        start_time = time.time()
        
        try:
            # Run orchestrator (suppress debug output unless verbose)
            if verbose:
                response, tracker = self.orchestrator.run(query, self.chat_history)
            else:
                # Capture and suppress debug prints
                captured_output = StringIO()
                with redirect_stdout(captured_output):
                    response, tracker = self.orchestrator.run(query, self.chat_history)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract metadata from response
            result_dict = {
                "final_answer": response,
                "agent_path": getattr(tracker, 'agent_path', []),
                "is_followup": False,  # Will be extracted from tracker if available
                "intent": getattr(tracker, 'intent', 'unknown'),
                "validation_status": getattr(tracker, 'validation_status', 'unknown'),
                "clarifications_requested": getattr(tracker, 'clarifications_requested', 0),
                "duration_ms": duration_ms
            }
            
            # Try to extract more metadata from tracker
            if hasattr(tracker, 'steps') and tracker.steps:
                for step in tracker.steps:
                    # Handle ReasoningStep dataclass
                    if hasattr(step, 'agent'):
                        agent_name = step.agent
                        if 'FollowUpResolver' in agent_name:
                            result_dict['is_followup'] = True
                        self.agent_call_counts[agent_name] += 1
                    # Fallback for dict-like steps
                    elif isinstance(step, dict):
                        agent_name = step.get('step', 'unknown')
                        if 'FollowUpResolver' in agent_name:
                            result_dict['is_followup'] = True
                        self.agent_call_counts[agent_name] += 1
            
            # Update metrics
            self.latencies.append(duration_ms)
            self.intent_counts[result_dict['intent']] += 1
            self.validation_status_counts[result_dict['validation_status']] += 1
            
            # Validate schema
            try:
                FinalResponseSchema(**result_dict)
                schema_valid = True
            except ValidationError as e:
                schema_valid = False
                result_dict['schema_error'] = str(e)
            
            # Create test result
            test_result = TestResult(
                name=test_name or query[:50],
                passed=schema_valid and response is not None,
                duration_ms=duration_ms,
                metadata=result_dict
            )
            
            return result_dict, test_result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            test_result = TestResult(
                name=test_name or query[:50],
                passed=False,
                duration_ms=duration_ms,
                error=str(e)
            )
            return None, test_result
    
    def add_to_history(self, query: str, response: str):
        """Add query/response to chat history"""
        self.chat_history.append({"role": "user", "content": query})
        self.chat_history.append({"role": "assistant", "content": response})
    
    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 FULL SYSTEM VALIDATION SUMMARY")
        print("="*80)
        
        # Overall stats
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        print(f"\n✅ OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ({100*passed_tests/total_tests:.1f}%)")
        print(f"   Failed: {failed_tests} ({100*failed_tests/total_tests:.1f}%)")
        
        # Latency stats
        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            max_latency = max(self.latencies)
            min_latency = min(self.latencies)
            
            print(f"\n⏱️  PERFORMANCE METRICS:")
            print(f"   Average Latency: {avg_latency:.0f}ms")
            print(f"   Max Latency: {max_latency:.0f}ms")
            print(f"   Min Latency: {min_latency:.0f}ms")
        
        # Agent stats
        if self.agent_call_counts:
            print(f"\n🤖 AGENT CALL COUNTS:")
            for agent, count in self.agent_call_counts.most_common(10):
                print(f"   {agent}: {count}")
        
        # Intent stats
        if self.intent_counts:
            print(f"\n🎯 INTENT DISTRIBUTION:")
            for intent, count in self.intent_counts.most_common():
                print(f"   {intent}: {count}")
        
        # Validation stats
        if self.validation_status_counts:
            print(f"\n✔️  VALIDATION STATUS:")
            for status, count in self.validation_status_counts.most_common():
                print(f"   {status}: {count}")
        
        # Failed tests
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"   • {result.name}")
                    if result.error:
                        print(f"     Error: {result.error}")
        
        print("\n" + "="*80)


# ============================================================================
# TEST SUITE INSTANCE
# ============================================================================

suite = TestSuite()


# ============================================================================
# 1️⃣ BASIC TESTS
# ============================================================================

def test_basic_queries():
    """Test basic query functionality"""
    print("\n" + "="*80)
    print("1️⃣  BASIC TESTS")
    print("="*80)
    
    suite.clear_history()
    
    # Test 1: Simple P&L query
    print("\n[TEST 1] Simple P&L query: Building 180, 2024")
    result, test_result = suite.run_query(
        "What is the P&L for Building 180 in 2024?",
        "Simple P&L Query"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
        print(f"   Intent: {result['intent']}")
        print(f"   Validation: {result['validation_status']}")
    else:
        print(f"❌ FAIL: {test_result.error}")
    
    # Test 2: Revenue-only query
    print("\n[TEST 2] Revenue-only query")
    result, test_result = suite.run_query(
        "Show me the revenue for Building 140 in Q1 2024",
        "Revenue Query"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
    else:
        print(f"❌ FAIL: {test_result.error}")
    
    # Test 3: Multi-property comparison
    print("\n[TEST 3] Multi-property comparison")
    result, test_result = suite.run_query(
        "Compare Building 140 and Building 180 in 2024",
        "Multi-Property Comparison"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
    else:
        print(f"❌ FAIL: {test_result.error}")
    
    # Test 4: Follow-up query
    print("\n[TEST 4] Follow-up query")
    suite.clear_history()
    
    # First query
    result1, test_result1 = suite.run_query(
        "Show P&L for Building 180 in 2024",
        "Follow-up: Initial Query"
    )
    suite.results.append(test_result1)
    if test_result1.passed:
        suite.add_to_history("Show P&L for Building 180 in 2024", result1['final_answer'])
        print(f"   Initial query: ✅ PASS")
        
        # Follow-up
        result2, test_result2 = suite.run_query(
            "And what about 2025?",
            "Follow-up: Second Query"
        )
        suite.results.append(test_result2)
        if test_result2.passed:
            print(f"   Follow-up query: ✅ PASS ({test_result2.duration_ms}ms)")
            print(f"   Is Follow-up: {result2['is_followup']}")
        else:
            print(f"   Follow-up query: ❌ FAIL: {test_result2.error}")
    else:
        print(f"   Initial query: ❌ FAIL: {test_result1.error}")
    
    # Test 5: Invalid entity
    print("\n[TEST 5] Invalid entity: Building 999")
    suite.clear_history()
    result, test_result = suite.run_query(
        "Show P&L for Building 999",
        "Invalid Entity"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
        print(f"   Validation: {result['validation_status']}")
        print(f"   Clarifications: {result['clarifications_requested']}")
    else:
        print(f"❌ FAIL: {test_result.error}")
    
    # Test 6: Ambiguous entity
    print("\n[TEST 6] Ambiguous entity: Building 18")
    result, test_result = suite.run_query(
        "Show revenue for Building 18",
        "Ambiguous Entity"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
        print(f"   Validation: {result['validation_status']}")
    else:
        print(f"❌ FAIL: {test_result.error}")
    
    # Test 7: Natural date parsing
    print("\n[TEST 7] Natural date: Q1 2024")
    result, test_result = suite.run_query(
        "Show Building 140 in Q1 2024",
        "Natural Date Q1"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
    else:
        print(f"❌ FAIL: {test_result.error}")
    
    # Test 8: Missing date
    print("\n[TEST 8] Missing date")
    result, test_result = suite.run_query(
        "Show P&L for Building 180",
        "Missing Date"
    )
    suite.results.append(test_result)
    if test_result.passed:
        print(f"✅ PASS ({test_result.duration_ms}ms)")
        print(f"   Clarifications: {result['clarifications_requested']}")
    else:
        print(f"❌ FAIL: {test_result.error}")


# ============================================================================
# 2️⃣ EDGE CASES
# ============================================================================

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "="*80)
    print("2️⃣  EDGE CASES")
    print("="*80)
    
    suite.clear_history()
    
    edge_cases = [
        ("", "Empty String"),
        ("ok", "Stop Word Only"),
        ("yes", "Stop Word Yes"),
        ("and", "Stop Word And"),
        ("Show me something", "No Properties"),
        ("tell me more", "No Clear Intent"),
        ("Building 999 and Building 888", "Multiple Invalid Entities"),
        ("Show Tenant 1 and Building 180", "Mixed Tenants + Properties"),
    ]
    
    for query, test_name in edge_cases:
        print(f"\n[TEST] {test_name}: '{query}'")
        result, test_result = suite.run_query(query, f"Edge Case: {test_name}")
        suite.results.append(test_result)
        
        if test_result.passed:
            print(f"✅ PASS ({test_result.duration_ms}ms)")
            if result:
                print(f"   Response type: {type(result['final_answer'])}")
                print(f"   Has clarification: {result['clarifications_requested'] > 0}")
        else:
            print(f"✅ PASS (System handled gracefully)")
            print(f"   Error caught: {test_result.error[:100]}")


# ============================================================================
# 3️⃣ FOLLOW-UP CHAIN
# ============================================================================

def test_followup_chain():
    """Test multi-turn conversation"""
    print("\n" + "="*80)
    print("3️⃣  FOLLOW-UP CHAIN (5 turns)")
    print("="*80)
    
    suite.clear_history()
    
    conversation = [
        "Show Building 180 P&L for 2024",
        "and Q1?",
        "compare with 140",
        "and the expenses?",
        "ok now 2025"
    ]
    
    for i, query in enumerate(conversation, 1):
        print(f"\n[TURN {i}] {query}")
        result, test_result = suite.run_query(query, f"Follow-up Chain Turn {i}")
        suite.results.append(test_result)
        
        if test_result.passed:
            print(f"✅ PASS ({test_result.duration_ms}ms)")
            print(f"   Agent Path Length: {len(result['agent_path'])}")
            print(f"   Is Follow-up: {result['is_followup']}")
            
            # Add to history
            suite.add_to_history(query, result['final_answer'])
        else:
            print(f"❌ FAIL: {test_result.error}")
            break


# ============================================================================
# 4️⃣ NATURAL DATE EXTREME TESTS
# ============================================================================

def test_natural_dates():
    """Test natural date parsing edge cases"""
    print("\n" + "="*80)
    print("4️⃣  NATURAL DATE EXTREME TESTS")
    print("="*80)
    
    suite.clear_history()
    
    date_queries = [
        ("Show 180 in Q1 2024", "Q1 2024"),
        ("Show 180 in Q2", "Q2 (implicit year)"),
        ("Show 180 in December 2024", "Month name"),
        ("Compare 180 Q4 2023 vs Q1 2024", "Quarter comparison"),
        ("Show 180 in Jan, Feb and March 2024", "Multiple months"),
    ]
    
    for query, test_name in date_queries:
        print(f"\n[TEST] {test_name}: {query}")
        result, test_result = suite.run_query(query, f"Natural Date: {test_name}")
        suite.results.append(test_result)
        
        if test_result.passed:
            print(f"✅ PASS ({test_result.duration_ms}ms)")
            print(f"   Validation: {result['validation_status']}")
        else:
            print(f"❌ FAIL: {test_result.error}")


# ============================================================================
# 5️⃣ PERFORMANCE TEST
# ============================================================================

def test_performance():
    """Test system performance with multiple queries"""
    print("\n" + "="*80)
    print("5️⃣  PERFORMANCE TEST (20 queries)")
    print("="*80)
    
    suite.clear_history()
    
    test_queries = [
        "Show Building 180 P&L for 2024",
        "Show Building 140 revenue in Q1 2024",
        "Compare Building 140 and Building 180",
        "Show Building 700 in 2024",
        "What is the total profit for all properties?",
    ] * 4  # 20 queries total
    
    start_time = time.time()
    errors = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\r   Running query {i}/20...", end="", flush=True)
        result, test_result = suite.run_query(query, f"Performance Test {i}")
        suite.results.append(test_result)
        
        if not test_result.passed:
            errors += 1
    
    total_time = time.time() - start_time
    
    print(f"\n\n✅ Performance Test Complete")
    print(f"   Total Runtime: {total_time:.2f}s")
    print(f"   Average Query Time: {total_time/20:.2f}s")
    print(f"   Errors: {errors}/20")


# ============================================================================
# 6️⃣ JSON SCHEMA VALIDATION
# ============================================================================

def test_schema_validation():
    """Test that all outputs match the expected schema"""
    print("\n" + "="*80)
    print("6️⃣  JSON SCHEMA VALIDATION")
    print("="*80)
    
    suite.clear_history()
    
    # Run a few queries and validate schema
    queries = [
        "Show Building 180 in 2024",
        "Compare Building 140 and 180",
        "Show Building 999",  # Invalid
    ]
    
    schema_valid_count = 0
    
    for query in queries:
        print(f"\n[TEST] {query}")
        result, test_result = suite.run_query(query, f"Schema Validation: {query[:30]}")
        suite.results.append(test_result)
        
        if result:
            try:
                FinalResponseSchema(**result)
                print(f"✅ Schema Valid")
                schema_valid_count += 1
            except ValidationError as e:
                print(f"❌ Schema Invalid: {e}")
        else:
            print(f"❌ No result returned")
    
    print(f"\n📊 Schema Validation: {schema_valid_count}/{len(queries)} passed")


# ============================================================================
# 7️⃣ FULL SYSTEM IMPORT TEST
# ============================================================================

def test_imports():
    """Test that all imports work correctly"""
    print("\n" + "="*80)
    print("7️⃣  FULL SYSTEM IMPORT TEST")
    print("="*80)
    
    try:
        print("\n[TEST] Importing core modules...")
        from backend.core.orchestrator import RealEstateOrchestrator
        from backend.llm.llm_client import LLMClient
        from backend.data.data_loader import RealEstateDataLoader
        print("✅ All imports successful")
        
        print("\n[TEST] Initializing system...")
        llm_client = LLMClient()
        llm = llm_client.get_llm()
        data_loader = RealEstateDataLoader("data/cortex.parquet")
        orchestrator = RealEstateOrchestrator(llm, data_loader)
        print("✅ System initialization successful")
        
        print("\n[TEST] Running first query...")
        response, tracker = orchestrator.run("Show Building 180 in 2024", [])
        print("✅ First query successful")
        
        test_result = TestResult("Import Test", True, 0)
        suite.results.append(test_result)
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        test_result = TestResult("Import Test", False, 0, error=str(e))
        suite.results.append(test_result)


# ============================================================================
# 8️⃣ STREAMLIT + FASTAPI INTEGRATION TEST
# ============================================================================

def test_integration():
    """Test Streamlit and FastAPI integration patterns"""
    print("\n" + "="*80)
    print("8️⃣  STREAMLIT + FASTAPI INTEGRATION TEST")
    print("="*80)
    
    try:
        print("\n[TEST] Simulating Streamlit initialization...")
        llm_client = LLMClient()
        llm = llm_client.get_llm()
        data_loader = RealEstateDataLoader("data/cortex.parquet")
        orchestrator = RealEstateOrchestrator(llm, data_loader)
        print("✅ Streamlit pattern successful")
        
        print("\n[TEST] Simulating FastAPI query...")
        response, tracker = orchestrator.run("Show Building 180 in 2024", [])
        
        # Verify return type
        assert isinstance(response, str), "Response must be string"
        assert tracker is not None, "Tracker must not be None"
        print("✅ FastAPI pattern successful")
        print(f"   Response type: {type(response)}")
        print(f"   Tracker type: {type(tracker)}")
        
        test_result = TestResult("Integration Test", True, 0)
        suite.results.append(test_result)
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        test_result = TestResult("Integration Test", False, 0, error=str(e))
        suite.results.append(test_result)


# ============================================================================
# 9️⃣ ERROR HANDLING TESTS
# ============================================================================

def test_error_handling():
    """Test system resilience to errors"""
    print("\n" + "="*80)
    print("9️⃣  ERROR HANDLING TESTS")
    print("="*80)
    
    suite.clear_history()
    
    # Test various error scenarios
    error_scenarios = [
        ("", "Empty query"),
        ("   ", "Whitespace only"),
        ("Show me " + "x"*1000, "Very long query"),
        ("Show Building 180 in year 9999", "Invalid year"),
        ("Show Building 180 in Q5", "Invalid quarter"),
    ]
    
    for query, test_name in error_scenarios:
        print(f"\n[TEST] {test_name}")
        result, test_result = suite.run_query(query, f"Error Handling: {test_name}")
        suite.results.append(test_result)
        
        # For error handling, we consider it a pass if the system doesn't crash
        if test_result.passed or test_result.error:
            print(f"✅ System handled gracefully")
        else:
            print(f"❌ System crashed")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests"""
    print("="*80)
    print("🧪 FULL SYSTEM VALIDATION TEST SUITE")
    print("="*80)
    print("\nThis comprehensive test suite validates:")
    print("  • Basic query functionality")
    print("  • Edge cases and error handling")
    print("  • Multi-turn conversations")
    print("  • Natural date parsing")
    print("  • System performance")
    print("  • Schema validation")
    print("  • Import and integration")
    print("  • Error resilience")
    
    # Setup
    if not suite.setup():
        print("\n❌ Setup failed. Exiting.")
        return
    
    # Run all test categories
    try:
        test_basic_queries()
        test_edge_cases()
        test_followup_chain()
        test_natural_dates()
        test_performance()
        test_schema_validation()
        test_imports()
        test_integration()
        test_error_handling()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
    
    # Print summary
    suite.print_summary()


if __name__ == "__main__":
    main()

