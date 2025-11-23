"""
Test des 11 cas spécifiques avec analyse détaillée
Vérifie chaque cas individuellement et analyse si c'est une vraie erreur ou juste une réponse incomplète
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.orchestrator import RealEstateOrchestrator
from backend.llm.llm_client import LLMClient
from backend.data.data_loader import RealEstateDataLoader
import polars as pl


# Les 11 cas spécifiques
TEST_CASES = [
    {
        "id": 1,
        "query": "Show me the tenants for Building 140",
        "expected": "Should return list of tenants for Building 140",
        "type": "tenant_info"
    },
    {
        "id": 2,
        "query": "List all properties",
        "expected": "Should return list of all properties",
        "type": "analytics_query"
    },
    {
        "id": 3,
        "query": "Give me the highest expense category in 2024",
        "expected": "Should return highest expense category (or error if not supported)",
        "type": "analytics_query"
    },
    {
        "id": 4,
        "query": "What is the revenue for all properties in Q1 2025?",
        "expected": "Should return revenue for all properties in Q1 2025",
        "type": "pl_calculation"
    },
    {
        "id": 5,
        "query": "Compare Q1 and Q2 2024 for Building 180",
        "expected": "Should compare Q1 vs Q2 2024 for Building 180",
        "type": "temporal_comparison"
    },
    {
        "id": 6,
        "query": "Show all tenants",
        "expected": "Should return list of all tenants",
        "type": "analytics_query"
    },
    {
        "id": 7,
        "query": "Which property made the most profit in 2024?",
        "expected": "Should return property with highest profit in 2024 (or error if not supported)",
        "type": "analytics_query"
    },
    {
        "id": 8,
        "query": "Compare Q1 and Q2 2024 for Building 180",
        "expected": "Same as case 5 - verify it works",
        "type": "temporal_comparison"
    },
    {
        "id": 9,
        "query": "Compare Q1 and Q2 2024 for Building 180",
        "expected": "Initial query for follow-up test",
        "type": "temporal_comparison",
        "is_followup_base": True
    },
    {
        "id": 10,
        "query": "What about Q3?",
        "expected": "Follow-up: Should compare Q1, Q2, Q3 or handle gracefully",
        "type": "temporal_comparison",
        "followup_of": 9,
        "chat_history": [
            {"user": "Compare Q1 and Q2 2024 for Building 180"},
            {"assistant": "Previous response"}
        ]
    },
    {
        "id": 11,
        "query": "Show me the tenants for Building 140",
        "expected": "Should return list of tenants for Building 140",
        "type": "tenant_info"
    }
]


def check_data_availability(data_loader, property_name=None, year=None, quarter=None):
    """Vérifie si les données existent dans le dataset"""
    df = data_loader.df
    
    if property_name:
        df = df.filter(pl.col("property_name").str.to_lowercase() == property_name.lower())
    
    if year:
        df = df.filter(pl.col("year") == str(year))
    
    if quarter:
        # Quarter format: "2024-Q1" or "Q1"
        if "-" in quarter:
            q = quarter.split("-")[-1]
        else:
            q = quarter
        df = df.filter(pl.col("quarter") == q)
    
    return {
        "exists": not df.is_empty(),
        "count": len(df),
        "years": df["year"].unique().to_list() if not df.is_empty() else [],
        "quarters": df["quarter"].unique().to_list() if not df.is_empty() else []
    }


def analyze_response(case, response, tracker, data_loader):
    """Analyse la réponse pour déterminer si c'est une vraie erreur ou juste incomplet"""
    analysis = {
        "case_id": case["id"],
        "query": case["query"],
        "response": response,
        "is_error": response.startswith("❌") or "error" in response.lower(),
        "issues": [],
        "data_check": {},
        "recommendation": ""
    }
    
    # Extraire les entités et intent du tracker
    intent = None
    entities = {}
    for step in tracker.steps:
        if step.agent == "Router":
            intent = step.output_data.get("intent")
        elif step.agent == "Extractor":
            entities = step.output_data.get("entities", {})
    
    analysis["intent"] = intent
    analysis["entities"] = entities
    
    # Vérifications spécifiques par cas
    if case["id"] == 1 or case["id"] == 11:  # Show me the tenants for Building 140
        prop = "Building 140"
        data_check = check_data_availability(data_loader, property_name=prop)
        analysis["data_check"] = data_check
        
        if analysis["is_error"]:
            analysis["issues"].append(f"Query failed but data exists: {data_check['count']} records for {prop}")
            analysis["recommendation"] = "Should work - data exists. Check extraction/validation."
        elif "tenant" in response.lower() and "building 140" in response.lower():
            analysis["recommendation"] = "✅ Response looks correct"
        else:
            analysis["issues"].append("Response doesn't mention Building 140 tenants")
            analysis["recommendation"] = "Response may be incomplete"
    
    elif case["id"] == 2:  # List all properties
        props = data_loader.get_properties()
        analysis["data_check"] = {"properties_count": len(props), "properties": props}
        
        if analysis["is_error"]:
            analysis["issues"].append(f"Query failed but {len(props)} properties exist")
            analysis["recommendation"] = "Should work - analytics_query should list properties"
        elif "building" in response.lower() or "property" in response.lower():
            analysis["recommendation"] = "✅ Response likely correct"
        else:
            analysis["issues"].append("Response doesn't contain property list")
            analysis["recommendation"] = "Response may be incomplete"
    
    elif case["id"] == 3:  # Highest expense category
        # Vérifier si on a des données d'expenses en 2024
        df_2024 = data_loader.df.filter(pl.col("year") == "2024")
        expenses = df_2024.filter(pl.col("ledger_type") == "expenses")
        analysis["data_check"] = {
            "has_expenses_2024": not expenses.is_empty(),
            "expense_categories": expenses["ledger_category"].unique().to_list() if not expenses.is_empty() else []
        }
        
        if analysis["is_error"]:
            if "not yet fully supported" in response.lower():
                analysis["recommendation"] = "✅ Expected - complex analytics not implemented"
            else:
                analysis["issues"].append("Unexpected error for analytics query")
                analysis["recommendation"] = "Should return 'not supported' message, not crash"
        else:
            analysis["recommendation"] = "Response provided (may be placeholder)"
    
    elif case["id"] == 4:  # Revenue for all properties in Q1 2025
        data_check = check_data_availability(data_loader, year="2025", quarter="Q1")
        analysis["data_check"] = data_check
        
        if analysis["is_error"]:
            if "PropCo" not in str(entities.get("properties", [])):
                analysis["issues"].append("'all properties' not extracted as PropCo")
                analysis["recommendation"] = "Fix extraction to detect 'all properties'"
            elif not data_check["exists"]:
                analysis["recommendation"] = "✅ Expected - no data for Q1 2025"
            else:
                analysis["issues"].append("Data exists but query failed")
                analysis["recommendation"] = "Should work - check PropCo handling"
        else:
            analysis["recommendation"] = "✅ Response provided"
    
    elif case["id"] == 5 or case["id"] == 8:  # Compare Q1 and Q2 2024
        prop = "Building 180"
        q1_check = check_data_availability(data_loader, property_name=prop, year="2024", quarter="Q1")
        q2_check = check_data_availability(data_loader, property_name=prop, year="2024", quarter="Q2")
        analysis["data_check"] = {"Q1": q1_check, "Q2": q2_check}
        
        if analysis["is_error"]:
            if not q1_check["exists"] or not q2_check["exists"]:
                analysis["recommendation"] = "✅ Expected - missing period data"
            else:
                analysis["issues"].append("Data exists but comparison failed")
                analysis["recommendation"] = "Should work - check quarter formatting"
        elif "compare" in response.lower() or "period" in response.lower():
            # Vérifier le format des quarters dans entities
            quarters = entities.get("quarter", [])
            if any("['2024']" in str(q) for q in quarters):
                analysis["issues"].append("Quarter format incorrect: contains ['2024']")
                analysis["recommendation"] = "Fix quarter normalization"
            else:
                analysis["recommendation"] = "✅ Response looks correct"
        else:
            analysis["recommendation"] = "Response may be incomplete"
    
    elif case["id"] == 6:  # Show all tenants
        tenants = data_loader.get_tenants()
        analysis["data_check"] = {"tenants_count": len(tenants), "tenants": tenants[:10]}
        
        if analysis["is_error"]:
            analysis["issues"].append(f"Query failed but {len(tenants)} tenants exist")
            analysis["recommendation"] = "Should work - analytics_query should list tenants"
        elif "tenant" in response.lower():
            analysis["recommendation"] = "✅ Response likely correct"
        else:
            analysis["issues"].append("Response doesn't contain tenant list")
            analysis["recommendation"] = "Response may be incomplete"
    
    elif case["id"] == 7:  # Which property made the most profit in 2024
        df_2024 = data_loader.df.filter(pl.col("year") == "2024")
        props = df_2024["property_name"].unique().to_list()
        analysis["data_check"] = {
            "has_data_2024": not df_2024.is_empty(),
            "properties_in_2024": props
        }
        
        if analysis["is_error"]:
            if "not yet fully supported" in response.lower():
                analysis["recommendation"] = "✅ Expected - max analytics not implemented"
            else:
                analysis["issues"].append("Unexpected error for analytics query")
                analysis["recommendation"] = "Should return 'not supported' message, not crash"
        else:
            analysis["recommendation"] = "Response provided (may be placeholder)"
    
    elif case["id"] == 9:  # Base for follow-up
        prop = "Building 180"
        q1_check = check_data_availability(data_loader, property_name=prop, year="2024", quarter="Q1")
        q2_check = check_data_availability(data_loader, property_name=prop, year="2024", quarter="Q2")
        analysis["data_check"] = {"Q1": q1_check, "Q2": q2_check}
        analysis["recommendation"] = "Base query for follow-up test"
    
    elif case["id"] == 10:  # Follow-up: What about Q3?
        prop = "Building 180"
        q3_check = check_data_availability(data_loader, property_name=prop, year="2024", quarter="Q3")
        analysis["data_check"] = {"Q3": q3_check}
        
        # Vérifier si c'est détecté comme follow-up
        is_followup = False
        for step in tracker.steps:
            if step.agent == "FollowUpResolver":
                is_followup = step.output_data.get("is_followup", False)
        
        analysis["is_followup_detected"] = is_followup
        
        if not is_followup:
            analysis["issues"].append("Follow-up not detected")
            analysis["recommendation"] = "Should detect as follow-up and enrich with Building 180 + 2024"
        elif analysis["is_error"]:
            if "periods (need ≥ 2)" in response:
                analysis["recommendation"] = "✅ Expected - temporal comparison needs 2+ periods"
            else:
                analysis["issues"].append("Unexpected error in follow-up")
                analysis["recommendation"] = "Should enrich query with context"
        else:
            analysis["recommendation"] = "✅ Follow-up handled correctly"
    
    return analysis


def main():
    print("="*80)
    print("🧪 TEST DES 11 CAS SPÉCIFIQUES")
    print("="*80)
    
    # Initialize
    print("\n🔧 Initialisation...")
    llm_client = LLMClient()
    llm = llm_client.get_llm()
    data_loader = RealEstateDataLoader("data/cortex.parquet")
    orchestrator = RealEstateOrchestrator(llm, data_loader, debug_mode=False)
    print("✅ Système initialisé\n")
    
    results = []
    chat_history = []
    
    for case in TEST_CASES:
        print(f"\n{'='*80}")
        print(f"📋 CAS {case['id']}: {case['query']}")
        print(f"   Type: {case['type']} | Attendu: {case['expected']}")
        print("="*80)
        
        # Préparer chat_history si c'est un follow-up
        if case.get("followup_of"):
            # Utiliser le chat_history fourni ou construire depuis les résultats précédents
            if case.get("chat_history"):
                test_chat_history = case["chat_history"]
            else:
                # Construire depuis les résultats précédents
                base_case = next(c for c in TEST_CASES if c["id"] == case["followup_of"])
                test_chat_history = [
                    {"user": base_case["query"]},
                    {"assistant": results[case["followup_of"]-1]["response"]}
                ]
        else:
            test_chat_history = None
        
        try:
            response, tracker = orchestrator.run(case["query"], chat_history=test_chat_history)
            
            # Analyser la réponse
            analysis = analyze_response(case, response, tracker, data_loader)
            results.append(analysis)
            
            # Afficher les résultats
            print(f"\n📊 RÉSULTAT:")
            print(f"   Intent: {analysis['intent']}")
            print(f"   Entities: {analysis['entities']}")
            print(f"   Response: {response[:150]}...")
            print(f"   Is Error: {analysis['is_error']}")
            
            if analysis.get("data_check"):
                print(f"\n📈 VÉRIFICATION DONNÉES:")
                for key, value in analysis["data_check"].items():
                    if isinstance(value, list) and len(value) > 5:
                        print(f"   {key}: {len(value)} items (showing first 5: {value[:5]})")
                    else:
                        print(f"   {key}: {value}")
            
            if analysis["issues"]:
                print(f"\n⚠️  PROBLÈMES DÉTECTÉS:")
                for issue in analysis["issues"]:
                    print(f"   - {issue}")
            
            print(f"\n💡 RECOMMANDATION: {analysis['recommendation']}")
            
            # Mettre à jour chat_history pour les suivants
            if case.get("is_followup_base"):
                chat_history.append({"user": case["query"]})
                chat_history.append({"assistant": response})
        
        except Exception as e:
            print(f"\n❌ ERREUR EXCEPTION: {e}")
            results.append({
                "case_id": case["id"],
                "query": case["query"],
                "response": f"Exception: {str(e)}",
                "is_error": True,
                "issues": [f"Exception raised: {str(e)}"],
                "recommendation": "Fix exception handling"
            })
    
    # Résumé final
    print("\n" + "="*80)
    print("📊 RÉSUMÉ FINAL")
    print("="*80)
    
    total = len(results)
    errors = sum(1 for r in results if r["is_error"])
    issues_found = sum(len(r.get("issues", [])) for r in results)
    
    print(f"\n✅ Total: {total} cas")
    print(f"❌ Erreurs: {errors}")
    print(f"⚠️  Problèmes détectés: {issues_found}")
    
    print(f"\n📋 DÉTAIL PAR CAS:")
    for r in results:
        status = "❌" if r["is_error"] else "✅"
        issues = f" ({len(r.get('issues', []))} issues)" if r.get("issues") else ""
        print(f"   {status} Cas {r['case_id']}: {r['recommendation']}{issues}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()

