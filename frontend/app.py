import streamlit as st
import requests
import os
from typing import Dict, Any, List

# Setup premium styling and typography
st.set_page_config(
    page_title="Brownfield AI Architect & Modification Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for glassmorphic cards, custom fonts, and glowing elements
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stCodeBlock, code {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1rem;
    }
    
    .tech-tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .frontend-tag { background-color: #00d2fc; color: #0c2340; }
    .backend-tag { background-color: #4caf50; color: white; }
    .database-tag { background-color: #ff9800; color: white; }
    .config-tag { background-color: #9c27b0; color: white; }
</style>
""", unsafe_allow_html=True)

# API Endpoint definition
API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000")

# Title Header
st.markdown("""
<div class="main-header">
    <h1>🛡️ Brownfield App AI Modernization Agent</h1>
    <p>Analyze, plan, modify, and validate changes across legacy three-tier applications with Human-in-the-Loop oversight</p>
</div>
""", unsafe_allow_html=True)

# Sidebar settings
st.sidebar.image("https://img.icons8.com/isometric/512/processor.png", width=100)
st.sidebar.title("Configuration & Keys")
api_key = st.sidebar.text_input("OpenAI API Key (Optional for fallbacks)", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

st.sidebar.markdown("---")
st.sidebar.subheader("API Status")
try:
    health_resp = requests.get(f"{API_URL}/api/health", timeout=3)
    if health_resp.status_code == 200:
        st.sidebar.success("✅ Backend Connected")
    else:
        st.sidebar.error("❌ Connected but unhealthy status")
except Exception:
    st.sidebar.error(f"❌ Cannot connect to backend at {API_URL}")
    st.sidebar.warning("Please ensure the FastAPI server is running.")

# State initialization
if "session_id" not in st.session_state:
    st.session_state["session_id"] = ""
if "current_state" not in st.session_state:
    st.session_state["current_state"] = None
if "dep_graph" not in st.session_state:
    st.session_state["dep_graph"] = None

# Main Panel layout split in tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📂 Project Ingestion & Stack Discovery", 
    "🕸️ Dependency & Impact Graph",
    "📚 Enterprise Standards (RAG)", 
    "🛠️ Plan, Edit & Human Approval"
])

# Tab 1: Project Ingestion
with tab1:
    st.header("1. Application Source Ingestion")
    
    source_type = st.radio("Select Repository Source:", ["Local Folder path / ZIP File", "GitHub URL"])
    
    default_source = ""
    if source_type == "Local Folder path / ZIP File":
        default_source = os.path.join(os.getcwd(), "scratch", "test_repo")
        source_input = st.text_input("Local directory path or absolute ZIP path:", value=default_source)
    else:
        source_input = st.text_input("GitHub URL (e.g., https://github.com/spring-projects/spring-petclinic.git):")
        
    enhancement_req = st.text_area(
        "Describe your requested enhancement / modification:",
        placeholder="e.g. Add a status field to the User profile class and expose it through the API controllers.",
        value="Add email verification to the database schema and backend endpoints."
    )
    
    if st.button("🚀 Ingest & Start Workflow Graph", use_container_width=True):
        if not source_input or not enhancement_req:
            st.error("Please fill in both the source path/URL and the enhancement request.")
        else:
            with st.spinner("Executing LangGraph State Machine (Ingestion -> Architecture -> AST Parse -> Dependencies -> Planning -> Modification -> Validation)..."):
                try:
                    payload = {"source": source_input, "requirement": enhancement_req}
                    resp = requests.post(f"{API_URL}/api/start", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state["session_id"] = data["session_id"]
                        
                        # Fetch full session state to populate graphs
                        session_resp = requests.get(f"{API_URL}/api/session/{data['session_id']}")
                        if session_resp.status_code == 200:
                            session_data = session_resp.json()
                            st.session_state["current_state"] = session_data["state"]
                            st.session_state["dep_graph"] = session_data["dependency_graph"]
                            st.success(f"Graph executed successfully! Session ID: {data['session_id']}")
                        else:
                            st.error("Failed to fetch graph session data.")
                    else:
                        st.error(f"Error starting workflow: {resp.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error making API request: {str(e)}")

    # Display Architecture summary if loaded
    if st.session_state["current_state"]:
        state = st.session_state["current_state"]
        arch = state.get("architecture", {})
        
        st.markdown("### 🔍 Detected Architecture Profile")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.subheader("Frontend Stack")
            for ft in arch.get("frontend", []):
                st.markdown(f'<span class="tech-tag frontend-tag">{ft}</span>', unsafe_allow_html=True)
        with col2:
            st.subheader("Backend Stack")
            for bt in arch.get("backend", []):
                st.markdown(f'<span class="tech-tag backend-tag">{bt}</span>', unsafe_allow_html=True)
        with col3:
            st.subheader("Database Tier")
            for dt in arch.get("database", []):
                st.markdown(f'<span class="tech-tag database-tag">{dt}</span>', unsafe_allow_html=True)
        with col4:
            st.subheader("Configs Detected")
            for cf in arch.get("config_files", []):
                st.markdown(f'<span class="tech-tag config-tag">{cf}</span>', unsafe_allow_html=True)

# Tab 2: Dependency Graph
with tab2:
    st.header("2. Dependency & Impact Graph")
    st.markdown("This graph is built dynamically using AST imports, REST API calls, and Database configurations.")
    
    if st.session_state["dep_graph"]:
        graph_data = st.session_state["dep_graph"]
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        # Build DOT representation for Graphviz rendering
        dot = "digraph {\n"
        dot += "  graph [rankdir=LR, bgcolor=transparent];\n"
        dot += "  node [shape=box, style=filled, fontname=\"Outfit\"];\n"
        
        for node in nodes:
            n_id = node["id"]
            n_type = node["type"]
            label = os.path.basename(n_id) if n_type == "file" else n_id
            if n_type == "database":
                color = "#ff9800"
                fontcolor = "white"
            elif "frontend" in n_id.lower() or "public" in n_id.lower():
                color = "#00d2fc"
                fontcolor = "black"
            else:
                color = "#4caf50"
                fontcolor = "white"
            dot += f'  "{n_id}" [label="{label}", fillcolor="{color}", fontcolor="{fontcolor}"];\n'
            
        for edge in edges:
            dot += f'  "{edge["source"]}" -> "{edge["target"]}" [color="#888888"];\n'
            
        dot += "}"
        st.graphviz_chart(dot)
        
        # Print list of nodes and relationships
        st.markdown("### Graph Component Details")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Components (Nodes):**")
            st.dataframe(nodes, use_container_width=True)
        with c2:
            st.write("**Relations (Edges):**")
            st.dataframe(edges, use_container_width=True)
    else:
        st.info("Run Ingestion and Workflow to visualize the application graph.")

# Tab 3: RAG Enterprise Standards
with tab3:
    st.header("3. Enterprise Reference Guidelines (RAG)")
    st.markdown("Retrieves only governance and standards documentation to ensure LLM compliance. Enhancement rules are managed directly within the agent prompts.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Add Policy Document")
        doc_title = st.text_input("Document/Policy Title:")
        doc_cat = st.selectbox("Category:", ["coding_standards", "security", "architecture"])
        doc_content = st.text_area("Document Content (Markdown or Plain Text):")
        
        if st.button("📥 Index Document in Milvus"):
            if not doc_title or not doc_content:
                st.error("Title and Content are required.")
            else:
                try:
                    payload = {"title": doc_title, "content": doc_content, "category": doc_cat}
                    resp = requests.post(f"{API_URL}/api/retrieval/add", json=payload)
                    if resp.status_code == 200:
                        st.success("Document added and embedded in Milvus Lite!")
                    else:
                        st.error("Failed to index document.")
                except Exception as e:
                    st.error(f"Error querying backend: {e}")
                    
    with col2:
        st.subheader("Query Standards Cache")
        q = st.text_input("Enter search phrase:", value="database standards")
        if st.button("🔍 Search RAG Vector DB"):
            try:
                resp = requests.get(f"{API_URL}/api/retrieval/query", params={"query": q})
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        for r in results:
                            st.markdown(f"**[{r['category'].upper()}] {r['title']}** (Score: {r['score']:.4f})")
                            st.write(r["content"])
                            st.markdown("---")
                    else:
                        st.write("No matching documents found.")
                else:
                    st.error("Failed to query vector database.")
            except Exception as e:
                st.error(f"Error: {e}")

# Tab 4: Plan, Modifications & Approval
with tab4:
    st.header("4. Plan & Code modifications")
    
    if st.session_state["current_state"]:
        state = st.session_state["current_state"]
        session_id = st.session_state["session_id"]
        
        col_p1, col_p2 = st.columns([1, 1])
        
        with col_p1:
            st.subheader("Proposed Plan & Task Breakdown")
            st.markdown(state.get("modification_plan", "No plan created."))
            
        with col_p2:
            st.subheader("Impact Summary & Validation")
            st.markdown(f"**Impacted Files Count**: {len(state.get('impacted_files', []))}")
            st.markdown(", ".join([f"`{f}`" for f in state.get('impacted_files', [])]))
            
            # Validation results
            val = state.get("validation_results", {})
            st.markdown(f"**Validation Status**: `{val.get('status', 'unknown').upper()}`")
            st.markdown(f"**Syntax Verification**: `{'Passed' if val.get('syntax_valid') else 'Failed'}`")
            st.markdown(f"**Simulated Build**: `{'Passed' if val.get('build_simulated') else 'Failed'}`")
            
            if val.get("security_issues"):
                st.warning("⚠️ Security scanning flagged potential concerns!")
                for sec in val["security_issues"]:
                    st.markdown(f"- `[{sec['severity']}]` in `{sec['file']}`: {sec['issue']}")
        
        st.markdown("---")
        st.subheader("Code Diffs & File Changes")
        
        # Display file changes
        modifications = state.get("modifications", {})
        original_contents = state.get("original_contents", {})
        
        if modifications:
            for file_path, new_code in modifications.items():
                with st.expander(f"📄 View Diff: {file_path}", expanded=True):
                    col_code1, col_code2 = st.columns(2)
                    with col_code1:
                        st.write("**Original Code**")
                        st.code(original_contents.get(file_path, ""), language=os.path.splitext(file_path)[1].replace(".", ""))
                    with col_code2:
                        st.write("**Modified Code**")
                        st.code(new_code, language=os.path.splitext(file_path)[1].replace(".", ""))
        else:
            st.info("No modifications were required for this run.")
            
        st.markdown("---")
        st.subheader("⚖️ Human-in-the-Loop Decision")
        
        if state.get("approval_status") == "pending":
            c_app1, c_app2 = st.columns(2)
            with c_app1:
                if st.button("✅ Approve & Write Changes to Files", use_container_width=True):
                    try:
                        resp = requests.post(f"{API_URL}/api/approve", json={"session_id": session_id, "approved": True})
                        if resp.status_code == 200:
                            st.success("Changes successfully approved and saved in workspace!")
                            # Refresh state
                            session_resp = requests.get(f"{API_URL}/api/session/{session_id}")
                            if session_resp.status_code == 200:
                                st.session_state["current_state"] = session_resp.json()["state"]
                                st.rerun()
                        else:
                            st.error(f"Approval failed: {resp.json().get('detail')}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")
            with c_app2:
                if st.button("❌ Reject Modifications", use_container_width=True):
                    try:
                        resp = requests.post(f"{API_URL}/api/approve", json={"session_id": session_id, "approved": False})
                        if resp.status_code == 200:
                            st.warning("Changes successfully discarded.")
                            session_resp = requests.get(f"{API_URL}/api/session/{session_id}")
                            if session_resp.status_code == 200:
                                st.session_state["current_state"] = session_resp.json()["state"]
                                st.rerun()
                        else:
                            st.error(f"Rejection failed: {resp.json().get('detail')}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")
        else:
            st.markdown(f"#### Workflow is finalized: Status is **{state.get('approval_status').upper()}**")
            if state.get('approval_status') == "approved":
                st.success("🎉 Changes are safely applied and verified.")
            else:
                st.error("🚫 Modifications were rejected and discarded.")
                
    else:
        st.info("Ingest and analyze a project to view details and execute Human-in-the-Loop review.")
