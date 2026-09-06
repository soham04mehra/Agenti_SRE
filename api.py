import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import BASE_DIR
from agent.graph import incident_agent_app
from database.repository import save_incident_state, get_incident_state
from eval.evaluate import evaluate_agent_benchmark

# Initialize FastAPI App
app = FastAPI(
    title="AI Incident Investigation & Recommendation Agent API",
    description="Agentic SRE Decision-Support System powered by LangGraph, MCP Tools & Deterministic Confidence Evaluation",
    version="1.0.0"
)

# Enable CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Request Models
class IncidentRequest(BaseModel):
    raw_description: str
    affected_service: Optional[str] = None
    severity: Optional[str] = "HIGH"

# API Endpoints

@app.get("/health")
def health_check():
    """API Health Status Endpoint."""
    return {
        "status": "healthy",
        "service": "AI Incident Agent API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/investigate")
def investigate_incident(req: IncidentRequest):
    """
    Main Endpoint: Receives an incident alert, runs the 6-node LangGraph investigation loop,
    persists state to Supabase, and returns the final evidence-backed RCA report.
    """
    if not req.raw_description.strip():
        raise HTTPException(status_code=400, detail="Incident description cannot be empty.")

    auto_id = f"inc_{int(time.time())}"

    initial_state = {
        "incident_id": auto_id,
        "raw_description": req.raw_description,
        "affected_service": req.affected_service,
        "symptom": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": req.severity or "HIGH",
        "hypotheses": [],
        "ruled_out_hypotheses": [],
        "current_plan": None,
        "next_tool_calls": [],
        "evidence": [],
        "tools_called": [],
        "raw_data_refs": [],
        "similar_past_incidents": [],
        "confidence_score": 0.0,
        "iteration_count": 0,
        "max_iterations": 3,
        "status": "investigating",
        "final_report": None
    }

    # Execute LangGraph workflow loop
    try:
        final_state = incident_agent_app.invoke(initial_state)
        save_incident_state(final_state)
        return final_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation workflow failed: {str(e)}")

@app.get("/api/v1/incidents/{incident_id}")
def get_incident_details(incident_id: str):
    """Fetches full state trace for a specific incident from Supabase or local memory."""
    state = get_incident_state(incident_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    return state

@app.get("/api/v1/benchmark")
def run_evaluation_benchmark():
    """Runs the 30 ground-truth evaluation harness benchmark and returns quantitative metrics."""
    try:
        metrics = evaluate_agent_benchmark()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(e)}")

# Serve Static Web Frontend Files
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def serve_frontend():
    """Serves the main SRE Incident Console Web Dashboard."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "AI Incident Agent API Running. Frontend index.html loading..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
