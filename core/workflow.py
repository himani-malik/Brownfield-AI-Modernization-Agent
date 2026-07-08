import os
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

# Import core agent classes
from core.ingestion import ProjectIngestionAgent
from core.arch_detector import ArchitectureDetectionAgent
from core.parser import CodeParsingAgent
from core.retrieval import RetrievalAgent
from core.dependency_analysis import DependencyAnalysisAgent
from core.planner import PlannerAgent
from core.modifier import CodeModificationAgent
from core.validator import ValidationAgent
from core.reporter import ReportingAgent

class AgentState(TypedDict):
    source: str
    workspace_path: str
    architecture: Dict[str, Any]
    parsed_data: Dict[str, Any]
    enhancement_request: str
    tasks: List[Dict[str, Any]]
    modification_plan: str
    impacted_files: List[str]
    modifications: Dict[str, str]
    original_contents: Dict[str, str]
    validation_results: Dict[str, Any]
    report: str
    approval_status: str  # "pending", "approved", "rejected"
    error: str

# Instantiate the agents
INGESTION_AGENT = ProjectIngestionAgent(workspace_base_dir="workspaces")
ARCH_DETECTOR = ArchitectureDetectionAgent()
PARSING_AGENT = CodeParsingAgent()
RETRIEVAL_AGENT = RetrievalAgent()
DEPENDENCY_AGENT = DependencyAnalysisAgent()
PLANNER_AGENT = PlannerAgent()
MODIFIER_AGENT = CodeModificationAgent()
VALIDATION_AGENT = ValidationAgent()
REPORTER_AGENT = ReportingAgent()

# Seed default rules in Milvus Lite
RETRIEVAL_AGENT.populate_default_rules()

# ----------------- LangGraph Node Functions -----------------

def node_ingest(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Ingesting project...")
    result = INGESTION_AGENT.run(state["source"])
    if result["status"] == "error":
        return {"error": result["message"]}
    return {
        "workspace_path": result["local_path"],
        "error": ""
    }

def node_detect_architecture(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Detecting architecture...")
    if state.get("error"):
        return {}
    arch = ARCH_DETECTOR.run(state["workspace_path"])
    return {"architecture": arch}

def node_parse_code(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Parsing code structure...")
    if state.get("error"):
        return {}
    parsed = PARSING_AGENT.run(state["workspace_path"])
    return {"parsed_data": parsed}

def node_analyze_dependencies_and_impact(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Building dependency graph and running impact analysis...")
    if state.get("error"):
        return {}
    
    # 1. Build graph
    dep_result = DEPENDENCY_AGENT.run(state["parsed_data"])
    G = dep_result["graph"]
    
    # 2. Identify initial target files based on keyword match
    initial_files = []
    req_lower = state["enhancement_request"].lower()
    
    for filename, info in state["parsed_data"].items():
        base = os.path.basename(filename).lower()
        if any(keyword in base or keyword in req_lower for keyword in ["controller", "service", "route", "api", "db", "repository", "model"]):
            if "frontend" in req_lower and "frontend" in filename:
                initial_files.append(filename)
            elif "backend" in req_lower and "backend" in filename:
                initial_files.append(filename)
            elif "db" in req_lower or "database" in req_lower:
                if info["database_queries"] or "db" in filename or "repository" in filename:
                    initial_files.append(filename)
                    
    if not initial_files:
        for filename in state["parsed_data"].keys():
            if "controller" in filename.lower() or "app.py" in filename.lower() or "server.js" in filename.lower() or "main" in filename.lower():
                initial_files.append(filename)

    # 3. Traverse NetworkX graph reverse dependencies for impacted files
    impacted = DEPENDENCY_AGENT.analyze_impact(G, initial_files)
    
    if not impacted and state["parsed_data"]:
        impacted = [list(state["parsed_data"].keys())[0]]

    return {
        "impacted_files": impacted
    }

def node_retrieve_guidelines(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Fetching guidelines from Milvus Lite...")
    if state.get("error"):
        return {}
    hits = RETRIEVAL_AGENT.query(state["enhancement_request"], limit=3)
    return {"rag_context": hits}

def node_plan_modifications(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Developing execution plan...")
    if state.get("error"):
        return {}
    
    plan_result = PLANNER_AGENT.run(
        requirement=state["enhancement_request"],
        parsed_data=state["parsed_data"],
        impacted_files=state["impacted_files"],
        rag_context=state.get("rag_context", [])
    )
    return {
        "tasks": plan_result["tasks"],
        "modification_plan": plan_result["modification_plan"]
    }

def node_modify_code(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Modifying code files...")
    if state.get("error"):
        return {}
        
    modifications = {}
    original_contents = {}
    
    files_to_modify = list(set([task["target_file"] for task in state["tasks"] if task.get("target_file")] + state["impacted_files"]))
    
    for f in files_to_modify:
        full_path = os.path.join(state["workspace_path"], f)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                    original = file_obj.read()
                    
                task_desc = "\n".join([t["description"] for t in state["tasks"] if t.get("target_file") == f])
                if not task_desc:
                    task_desc = f"Modify this file to support: {state['enhancement_request']}"
                    
                modified = MODIFIER_AGENT.run(
                    file_path=f,
                    current_content=original,
                    task_description=task_desc,
                    rag_context=state.get("rag_context", [])
                )
                
                modifications[f] = modified
                original_contents[f] = original
            except Exception as e:
                print(f"[Workflow Node] Error reading/modifying {f}: {e}")
                
    return {
        "modifications": modifications,
        "original_contents": original_contents
    }

def node_validate(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Running validation agent...")
    if state.get("error"):
        return {}
    val_results = VALIDATION_AGENT.run(state["workspace_path"], state["modifications"])
    return {"validation_results": val_results}

def node_report(state: AgentState) -> Dict[str, Any]:
    print("[Workflow Node] Generating report...")
    if state.get("error"):
        return {}
        
    markdown_report = REPORTER_AGENT.run(
        requirement=state["enhancement_request"],
        architecture=state["architecture"],
        plan={
            "tasks": state["tasks"],
            "modification_plan": state["modification_plan"]
        },
        modifications=state["modifications"],
        original_contents=state["original_contents"],
        validation_results=state["validation_results"]
    )
    return {
        "report": markdown_report,
        "approval_status": "pending"
    }

# ----------------- Graph Construction -----------------

workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("ingest", node_ingest)
workflow.add_node("detect_architecture", node_detect_architecture)
workflow.add_node("parse_code", node_parse_code)
workflow.add_node("analyze_dependencies", node_analyze_dependencies_and_impact)
workflow.add_node("retrieve", node_retrieve_guidelines)
workflow.add_node("plan", node_plan_modifications)
workflow.add_node("modify", node_modify_code)
workflow.add_node("validate", node_validate)
workflow.add_node("report", node_report)

# Wire edges
workflow.set_entry_point("ingest")
workflow.add_edge("ingest", "detect_architecture")
workflow.add_edge("detect_architecture", "parse_code")
workflow.add_edge("parse_code", "analyze_dependencies")
workflow.add_edge("analyze_dependencies", "retrieve")
workflow.add_edge("retrieve", "plan")
workflow.add_edge("plan", "modify")
workflow.add_edge("modify", "validate")
workflow.add_edge("validate", "report")
workflow.add_edge("report", END)

# Compile graph
graph = workflow.compile()

class GraphWorkflowManager:
    """
    Manages running the LangGraph workflow and handling approvals.
    """
    def __init__(self):
        self.workflow = graph
        self.run_store = {}

    def run_analysis_and_plan(self, source: str, requirement: str) -> Dict[str, Any]:
        initial_state = {
            "source": source,
            "workspace_path": "",
            "architecture": {},
            "parsed_data": {},
            "enhancement_request": requirement,
            "tasks": [],
            "modification_plan": "",
            "impacted_files": [],
            "modifications": {},
            "original_contents": {},
            "validation_results": {},
            "report": "",
            "approval_status": "pending",
            "error": ""
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        import uuid
        session_id = str(uuid.uuid4())
        self.run_store[session_id] = final_state
        
        return {
            "session_id": session_id,
            "state": final_state
        }

    def apply_approval(self, session_id: str, approved: bool) -> Dict[str, Any]:
        if session_id not in self.run_store:
            return {"error": "Session ID not found."}
            
        state = self.run_store[session_id]
        
        if approved:
            state["approval_status"] = "approved"
            for rel_path, content in state["modifications"].items():
                full_path = os.path.join(state["workspace_path"], rel_path)
                try:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    return {"error": f"Failed writing to {rel_path}: {str(e)}"}
            return {
                "status": "success",
                "message": "Approved. Changes successfully committed.",
                "workspace_path": state["workspace_path"]
            }
        else:
            state["approval_status"] = "rejected"
            return {
                "status": "rejected",
                "message": "Rejected. Modifications discarded."
            }
            
    def get_serialized_graph(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.run_store:
            return {}
        state = self.run_store[session_id]
        result = DEPENDENCY_AGENT.run(state["parsed_data"])
        return result["serialized_graph"]
