# 🧠 INTELLIGENT ORCHESTRATOR - PLAN D'IMPLÉMENTATION

## ✅ PHASE 1: NOUVEAUX AGENTS CRÉÉS (COMPLETED)

### 1️⃣ FollowUpResolverAgent
**Fichier**: `backend/agents/followup_resolver.py`

**Responsabilités**:
- Détecte les questions de suivi (follow-up)
- Enrichit la query avec le contexte de l'historique
- Premier node du graph

**Format de sortie**:
```python
{
    "status": "ok" | "error",
    "is_followup": bool,
    "updated_query": str,
    "original_query": str,
    "context_used": dict,
    "notes": str,
    "needs_clarification": bool,
    "duration_ms": int
}
```

**Exemples**:
- Input: "And what about Building 999?" (après "Compare Building 140 to Building 180")
- Output: `updated_query: "What is the P&L for Building 999?"`

---

### 2️⃣ NaturalDateAgent
**Fichier**: `backend/agents/naturaldate_agent.py`

**Responsabilités**:
- Parse les dates en langage naturel
- Normalise vers YYYY-MM-DD, YYYY-QX, YYYY-MXX
- Détecte les dates ambiguës

**Format de sortie**:
```python
{
    "status": "ok" | "ambiguous" | "error",
    "entities": dict,  # normalized
    "date_metadata": dict,
    "ambiguous_dates": list,
    "needs_clarification": bool,
    "notes": str,
    "duration_ms": int
}
```

**Exemples**:
- Input: `quarter: "Q1"` → Output: `quarter: "2024-Q1"`
- Input: `month: "December"` → Output: `month: "2024-M12"`

---

### 3️⃣ ValidationAgent (3-way routing)
**Fichier**: `backend/agents/validation_agent.py`

**Responsabilités**:
- Valide les entités contre le dataset
- Route vers 3 branches: `ok` / `missing` / `ambiguous`
- Identifie les champs manquants

**Format de sortie**:
```python
{
    "status": "ok" | "missing" | "ambiguous",
    "validation_status": "VALID" | "MISSING" | "AMBIGUOUS",  # for routing
    "entities": dict,
    "invalid_entities": dict,
    "missing_fields": list,
    "ambiguous_entities": dict,
    "suggestions": dict,
    "needs_clarification": bool,
    "notes": str,
    "duration_ms": int
}
```

**Routing**:
- `status: "ok"` → Query node
- `status: "missing"` → Clarification node
- `status: "ambiguous"` → Disambiguation node

---

### 4️⃣ DisambiguationAgent
**Fichier**: `backend/agents/disambiguation_agent.py`

**Responsabilités**:
- Résout les matchs ambigus (fuzzy matching)
- Exemple: "Building 18" vs "Building 180"
- Suggère des alternatives

**Format de sortie**:
```python
{
    "status": "ok" | "ambiguous" | "error",
    "entities": dict,  # clarified
    "suggestions": dict,
    "needs_clarification": bool,
    "clarification_message": str,
    "notes": str,
    "duration_ms": int
}
```

**Exemples**:
- Input: `properties: ["Building 18"]`
- Candidates: ["Building 18", "Building 180"]
- Output: `needs_clarification: True`, `suggestions: ["Building 18", "Building 180"]`

---

## 🎯 PHASE 2: ORCHESTRATOR PREVIEW (COMPLETED)

**Fichier**: `backend/core/orchestrator_preview.py`

### Architecture du Graph

```
Entry
  ↓
FollowUpResolver (enriches query if needed)
  ↓
Router (classifies intent)
  ↓
Extractor (extracts entities)
  ↓
NaturalDateAgent (normalizes dates)
  ↓
ValidationAgent (validates entities)
  ↓
┌─────────┼─────────┐
↓         ↓         ↓
MISSING  AMBIGUOUS  VALID
↓         ↓         ↓
Clarify  Disambig  Query
↓         ↓         ↓
END      Query    Formatter
           ↓         ↓
       Formatter    END
           ↓
          END
```

### Conditional Routing

1. **After Validation**:
   - `status: "ok"` → Query
   - `status: "missing"` → Clarification
   - `status: "ambiguous"` → Disambiguation

2. **After Disambiguation**:
   - `needs_clarification: False` → Query
   - `needs_clarification: True` → Clarification

---

## ⏳ PHASE 3: TESTS INDIVIDUELS (TODO)

### Test FollowUpResolver
```python
# Test 1: No follow-up
query = "What is the P&L for Building 180?"
result = followup_resolver.process(query, chat_history=[])
assert result["is_followup"] == False
assert result["updated_query"] == query

# Test 2: Follow-up detected
query = "And what about Building 140?"
history = [{"user": "What is the P&L for Building 180?", "assistant": "..."}]
result = followup_resolver.process(query, chat_history=history)
assert result["is_followup"] == True
assert "Building 140" in result["updated_query"]
```

### Test NaturalDateAgent
```python
# Test 1: Quarter normalization
entities = {"quarter": "Q1", "year": "2024"}
result = naturaldate_agent.process(entities)
assert result["entities"]["quarter"] == "2024-Q1"

# Test 2: Ambiguous date
entities = {"quarter": "Q5"}  # Invalid
result = naturaldate_agent.process(entities)
assert result["status"] == "ambiguous"
assert "Q5" in result["ambiguous_dates"]
```

### Test ValidationAgent
```python
# Test 1: Valid entities
entities = {"properties": ["Building 180"], "year": "2024"}
result = validation_agent.validate("pl_calculation", entities)
assert result["status"] == "ok"

# Test 2: Invalid property
entities = {"properties": ["Building 999"]}
result = validation_agent.validate("pl_calculation", entities)
assert result["status"] == "missing"
assert "Building 999" in result["invalid_entities"]["property"]
```

### Test DisambiguationAgent
```python
# Test 1: Exact match
entities = {"properties": ["Building 180"]}
ambiguous = {}
result = disambiguation_agent.process(entities, ambiguous)
assert result["status"] == "ok"
assert result["entities"]["properties"] == ["Building 180"]

# Test 2: Fuzzy match
entities = {"properties": ["Building 18"]}
ambiguous = {"properties": [{"input": "Building 18", "candidates": ["Building 18", "Building 180"]}]}
result = disambiguation_agent.process(entities, ambiguous)
assert result["needs_clarification"] == True
```

---

## ⏳ PHASE 4: INTÉGRATION (TODO)

### Étapes

1. **Tester le preview orchestrator avec des mocks**
   - Vérifier que le routing fonctionne
   - Vérifier les branches conditionnelles

2. **Intégrer les vrais agents un par un**
   - Commencer par FollowUpResolver
   - Puis NaturalDateAgent
   - Puis ValidationAgent
   - Enfin DisambiguationAgent

3. **Tests end-to-end**
   - Test suite complète avec 10 queries
   - Vérifier les agent paths
   - Vérifier les clarifications

4. **Remplacer l'ancien orchestrator**
   - Backup de l'ancien: `orchestrator_old.py`
   - Renommer `orchestrator_preview.py` → `orchestrator_v2.py`
   - Mettre à jour `app.py` pour utiliser v2

---

## ⏳ PHASE 5: UI ENHANCEMENTS (TODO)

### Ajouts à Streamlit

1. **Agent Path Display**
```python
st.info(f"🔀 Agent Path: {' → '.join(agent_path)}")
```

2. **Clarification Counter**
```python
st.metric("Clarifications Requested", clarifications_count)
```

3. **Follow-up Detection Badge**
```python
if is_followup:
    st.badge("🔄 Follow-up detected", type="info")
```

4. **Validation Status**
```python
if validation_status == "ambiguous":
    st.warning("⚠️ Ambiguous entities detected")
```

---

## 📊 AVANTAGES DE LA NOUVELLE ARCHITECTURE

### 1. **Follow-up Resolution**
- ✅ Détection automatique
- ✅ Enrichissement du contexte
- ✅ Pas besoin de répéter les infos

### 2. **3-Way Validation Routing**
- ✅ Séparation claire: ok/missing/ambiguous
- ✅ Gestion intelligente des erreurs
- ✅ Clarifications ciblées

### 3. **Disambiguation**
- ✅ Fuzzy matching automatique
- ✅ Suggestions intelligentes
- ✅ Résolution des ambiguïtés

### 4. **Natural Date Parsing**
- ✅ Parse "Q1" → "2024-Q1"
- ✅ Détecte les dates invalides
- ✅ Normalisation automatique

### 5. **Structured Outputs**
- ✅ Format uniforme pour tous les agents
- ✅ Facilite le debugging
- ✅ Meilleure traçabilité

---

## 🚀 NEXT STEPS

1. ✅ **Tous les agents créés avec structured outputs**
2. ⏳ **Tester chaque agent individuellement**
3. ⏳ **Intégrer dans orchestrator_preview**
4. ⏳ **Tests end-to-end**
5. ⏳ **Remplacer l'ancien orchestrator**
6. ⏳ **Mettre à jour l'UI**

---

## 📝 NOTES

- ⚠️ **L'ancien orchestrator reste intact** (`backend/core/orchestrator.py`)
- ⚠️ **Le preview est dans un fichier séparé** (`backend/core/orchestrator_preview.py`)
- ⚠️ **Pas de modification de l'app principale** jusqu'à validation complète
- ✅ **Tous les agents ont des structured outputs uniformes**
- ✅ **Tous les agents sont dans des fichiers séparés**

