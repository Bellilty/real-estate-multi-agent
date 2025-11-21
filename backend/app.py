"""
FastAPI Backend for Real Estate AI Assistant
Multi-Agent System with LangGraph Orchestration
"""

import os
import sys
import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# Add backend and project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # Project root
sys.path.insert(0, os.path.dirname(__file__))  # Backend directory

from backend.core.orchestrator import RealEstateOrchestrator
from backend.data.data_loader import RealEstateDataLoader
from backend.llm.llm_client import LLMClient
from backend.utils.conversation import ConversationContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Real Estate AI Assistant API",
    description="Multi-Agent System for Real Estate Asset Management",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    thought_process: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}

# Global state
orchestrator = None
conversation_context = ConversationContext()

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    global orchestrator
    
    try:
        logger.info("🚀 Starting Real Estate AI Assistant...")
        
        # Initialize LLM
        llm_client = LLMClient()
        llm = llm_client.get_llm()
        logger.info(f"✅ LLM initialized: {llm_client.MODEL_NAME}")
        
        # Initialize data loader
        data_loader = RealEstateDataLoader()
        logger.info(f"✅ Loaded {len(data_loader.df)} records from {data_loader.data_path}")
        
        # Initialize orchestrator
        orchestrator = RealEstateOrchestrator(llm=llm, data_loader=data_loader)
        logger.info("✅ Orchestrator initialized")
        
        logger.info("🎉 System ready!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize system: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Real Estate AI Assistant API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        # Test data loader
        stats = orchestrator.data_loader.get_dataset_stats()
        
        return {
            "status": "healthy",
            "llm": LLMClient.MODEL_NAME,
            "database": "connected",
            "records": len(orchestrator.data_loader.df),
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process user query through multi-agent system"""
    start_time = time.time()
    
    try:
        logger.info(f"📥 Received query: {request.question}")
        
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Check for context enhancement (follow-up questions)
        resolved_query = conversation_context.resolve_references(request.question)
        
        query_to_process = resolved_query if resolved_query != request.question else request.question
        
        # Process query through orchestrator
        final_response, tracker = orchestrator.run(query_to_process)
        
        # Extract intent and entities from tracker steps
        intent = "unknown"
        entities = {}
        if tracker and len(tracker.steps) > 0:
            # Router is step 0
            if len(tracker.steps) >= 1 and tracker.steps[0].output_data:
                intent = tracker.steps[0].output_data.get("intent", "unknown")
            # Extractor is step 1
            if len(tracker.steps) >= 2 and tracker.steps[1].output_data:
                extractor_output = tracker.steps[1].output_data
                if isinstance(extractor_output, dict) and "entities" in extractor_output:
                    entities = extractor_output["entities"]
                else:
                    entities = extractor_output or {}
        
        # Update conversation context
        conversation_context.add_turn(
            user_query=request.question,
            intent=intent,
            entities=entities,
            response=final_response
        )
        
        # Extract thought process from Chain-of-Thought tracker
        thought_process = []
        if tracker and hasattr(tracker, "steps"):
            for step in tracker.steps:
                thought_process.append({
                    "step": step.step_name,
                    "action": step.action,
                    "duration_ms": step.duration_ms,
                    "output": str(step.output_data)[:200] if step.output_data else None
                })
        
        # Prepare metadata
        metadata = {
            "intent": intent,
            "confidence": tracker.steps[0].output_data.get("confidence", "unknown") if tracker and len(tracker.steps) > 0 else "unknown",
            "total_duration_ms": (time.time() - start_time) * 1000,
            "llm_calls": tracker.total_llm_calls if tracker and hasattr(tracker, "total_llm_calls") else 0,
            "resolved_query": query_to_process if query_to_process != request.question else None
        }
        
        logger.info(f"✅ Query processed in {metadata['total_duration_ms']:.0f}ms")
        
        return QueryResponse(
            answer=final_response,
            thought_process=thought_process,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/schema")
async def get_schema():
    """Get dataset schema information"""
    try:
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        stats = orchestrator.data_loader.get_dataset_stats()
        
        return {
            "columns": list(orchestrator.data_loader.df.columns),
            "stats": stats,
            "sample_data": orchestrator.data_loader.df.head(3).to_dicts()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schema: {str(e)}")

@app.get("/available-entities")
async def get_available_entities():
    """Get all available entities (properties, tenants, years, etc.)"""
    try:
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        df = orchestrator.data_loader.df
        
        return {
            "properties": sorted(df.filter(df["property_name"].is_not_null())["property_name"].unique().to_list()),
            "tenants": sorted(df.filter(df["tenant_name"].is_not_null())["tenant_name"].unique().to_list()),
            "years": sorted(df["year"].unique().to_list()),
            "quarters": sorted(df["quarter"].unique().to_list()),
            "ledger_types": sorted(df["ledger_type"].unique().to_list()),
            "ledger_groups": sorted(df["ledger_group"].unique().to_list())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting entities: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )

