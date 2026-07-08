import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from core.workflow import GraphWorkflowManager
from core.retrieval import RetrievalAgent

app = FastAPI(
    title="Brownfield AI Agent API",
    description="REST interface managing ingestion, architecture detection, RAG retrieval, planning, modification, and verification of brownfield applications.",
    version="1.0.0"
)

# Initialize Manager and RAG DB
workflow_manager = GraphWorkflowManager()
retrieval_agent = RetrievalAgent()

# Pydantic schemas
class AnalyzeRequest(BaseModel):
    source: str
    requirement: str

class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool

class DocumentRequest(BaseModel):
    title: str
    content: str
    category: str  # security, coding_standards, architecture

# Endpoints
@app.post("/api/start", summary="Start code analysis and planning")
def start_analysis(payload: AnalyzeRequest):
    """
    Kicks off the LangGraph agent state machine for the specified project source
    and natural language enhancement request.
    """
    try:
        result = workflow_manager.run_analysis_and_plan(
            source=payload.source,
            requirement=payload.requirement
        )
        return {
            "session_id": result["session_id"],
            "status": "success",
            "message": "Analysis completed successfully. Awaiting Human-in-the-Loop review.",
            "state": {
                "architecture": result["state"]["architecture"],
                "tasks": result["state"]["tasks"],
                "modification_plan": result["state"]["modification_plan"],
                "impacted_files": result["state"]["impacted_files"],
                "modifications": result["state"]["modifications"],
                "validation_results": result["state"]["validation_results"],
                "report": result["state"]["report"],
                "approval_status": result["state"]["approval_status"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

@app.get("/api/session/{session_id}", summary="Fetch session details")
def get_session(session_id: str):
    """
    Returns the current graph state and serialized NetworkX dependency graph for UI visualization.
    """
    if session_id not in workflow_manager.run_store:
        raise HTTPException(status_code=404, detail="Session ID not found")
    
    state = workflow_manager.run_store[session_id]
    serialized_graph = workflow_manager.get_serialized_graph(session_id)
    
    return {
        "session_id": session_id,
        "state": {
            "source": state["source"],
            "workspace_path": state["workspace_path"],
            "architecture": state["architecture"],
            "enhancement_request": state["enhancement_request"],
            "tasks": state["tasks"],
            "modification_plan": state["modification_plan"],
            "impacted_files": state["impacted_files"],
            "modifications": state["modifications"],
            "validation_results": state["validation_results"],
            "report": state["report"],
            "approval_status": state["approval_status"]
        },
        "dependency_graph": serialized_graph
    }

@app.post("/api/approve", summary="Approve or reject modifications")
def approve_changes(payload: ApprovalRequest):
    """
    Human-in-the-Loop decision. If approved, commits changes to the physical workspace.
    """
    result = workflow_manager.apply_approval(payload.session_id, payload.approved)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/retrieval/add", summary="Add enterprise reference document to Milvus Lite RAG")
def add_enterprise_document(payload: DocumentRequest):
    """
    Ingests and embeds standard coding or architectural policies into local Milvus.
    """
    try:
        doc_id = retrieval_agent.add_document(
            title=payload.title,
            content=payload.content,
            category=payload.category
        )
        return {"status": "success", "document_id": doc_id, "message": "Enterprise document indexed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Milvus indexing failed: {str(e)}")

@app.get("/api/retrieval/query", summary="Search local vector database")
def query_vector_db(query: str, category: Optional[str] = None):
    try:
        results = retrieval_agent.query(query, category=category)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
        
@app.get("/api/health", summary="Health Check")
def health():
    return {"status": "healthy"}
