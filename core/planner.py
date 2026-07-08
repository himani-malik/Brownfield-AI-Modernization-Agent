import os
import json
from typing import Dict, Any, List

class PlannerAgent:
    """
    Combines Requirement Understanding and Planning.
    Translates natural language into structured tasks and a multi-tier modification plan.
    Uses pure-Python OpenAI SDK to avoid heavy LangChain binary dependency installation issues.
    """
    def __init__(self):
        pass

    def run(self, requirement: str, parsed_data: Dict[str, Any], impacted_files: List[str], rag_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates the plan.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # Format the RAG guidelines
        rag_str = "\n".join([f"- [{h['category']}] {h['title']}: {h['content']}" for h in rag_context]) if rag_context else "No custom enterprise guidelines found."
        
        # Format parsed files details
        files_summary = []
        for f in impacted_files:
            if f in parsed_data:
                info = parsed_data[f]
                files_summary.append(
                    f"File: {f}\n"
                    f"  Classes: {info['classes']}\n"
                    f"  Functions: {info['functions']}\n"
                    f"  Endpoints: {info['endpoints']}\n"
                    f"  DB Queries: {info['database_queries']}\n"
                )
        files_summary_str = "\n".join(files_summary)

        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                
                system_prompt = (
                    "You are a Principal Software Architect. Your job is to design a code modification plan "
                    "for an existing three-tier codebase based on a user requirement, the list of impacted files, "
                    "and enterprise coding guidelines.\n\n"
                    "Provide your output as a JSON object with two fields:\n"
                    "1. 'tasks': A list of structured sub-tasks to execute (each with 'title', 'description', and 'target_file').\n"
                    "2. 'modification_plan': A detailed markdown description of the step-by-step plan, citing coding/security rules to respect."
                )
                
                user_prompt = (
                    f"USER REQUIREMENT:\n{requirement}\n\n"
                    f"ENTERPRISE GUIDELINES (RAG):\n{rag_str}\n\n"
                    f"IMPACTED FILES & AST STRUCTURE:\n{files_summary_str}\n\n"
                    "Generate the plan JSON object. Ensure the JSON is valid and fits the schema."
                )
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                plan_json = json.loads(content)
                return {
                    "tasks": plan_json.get("tasks", []),
                    "modification_plan": plan_json.get("modification_plan", "Plan details failed to load.")
                }
            except Exception as e:
                print(f"[Planner] OpenAI plan generation failed, falling back to rule-based planner: {e}")

        # Fallback Offline Planner
        return self._generate_fallback_plan(requirement, impacted_files, rag_str)

    def _generate_fallback_plan(self, requirement: str, impacted_files: List[str], rag_str: str) -> Dict[str, Any]:
        """
        Rule-based plan generator that mimics LLM behavior when offline.
        """
        tasks = []
        plan_md = f"# Modification Plan for: {requirement}\n\n"
        
        plan_md += "## Enterprise Guidelines Applied (RAG)\n"
        plan_md += f"{rag_str}\n\n"
        
        plan_md += "## Impact Analysis & Planned Changes\n"
        
        # Scan files and generate logical tasks
        for f in impacted_files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".js", ".ts", ".jsx", ".tsx"]:
                if "routes" in f or "server" in f or "app.js" in f or "backend" in f:
                    title = f"Expose Endpoint in {os.path.basename(f)}"
                    desc = f"Modify file to expose API route or controller function supporting: '{requirement}'"
                else:
                    title = f"Update Component in {os.path.basename(f)}"
                    desc = f"Integrate backend changes and update user interface rendering for: '{requirement}'"
            elif ext == ".java":
                title = f"Modify Service/Repository in {os.path.basename(f)}"
                desc = f"Implement business logic and query processing matching: '{requirement}'"
            elif ext == ".cs":
                title = f"Modify Controller/Entity in {os.path.basename(f)}"
                desc = f"Add data model properties and API endpoints matching: '{requirement}'"
            else:
                title = f"Modify Config/HTML in {os.path.basename(f)}"
                desc = f"Add parameters or elements matching: '{requirement}'"
                
            tasks.append({
                "title": title,
                "description": desc,
                "target_file": f
            })
            
            plan_md += f"### [MODIFY] {f}\n"
            plan_md += f"- **Task**: {title}\n"
            plan_md += f"- **Details**: {desc}\n\n"

        plan_md += "## Risk & Safety Recommendations\n"
        plan_md += "- Ensure database connections are securely managed.\n"
        plan_md += "- Perform regression check on modified routes.\n"
        plan_md += "- Follow coding standards regarding camelCase/snake_case.\n"
        
        return {
            "tasks": tasks,
            "modification_plan": plan_md
        }
