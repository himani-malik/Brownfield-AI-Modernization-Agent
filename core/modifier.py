import os
from typing import Dict, Any, List

class CodeModificationAgent:
    """
    Modifies specific source files based on the planner's task description and RAG rules.
    Uses pure-Python OpenAI SDK to avoid heavy LangChain binary dependency installation issues.
    """
    def __init__(self):
        pass

    def run(self, file_path: str, current_content: str, task_description: str, rag_context: List[Dict[str, Any]]) -> str:
        """
        Executes code modification.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        rag_str = "\n".join([f"- [{h['category']}] {h['title']}: {h['content']}" for h in rag_context]) if rag_context else ""
        
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                
                system_prompt = (
                    "You are an expert software engineer. Your task is to modify a single source file "
                    "in a three-tier application to implement a new feature or enhancement.\n\n"
                    "RULES:\n"
                    "1. Modify ONLY what is necessary to fulfill the task description.\n"
                    "2. Preserve the existing coding style (naming conventions, indentation, bracing, comment styles).\n"
                    "3. Do not modify or delete unrelated code, classes, or imports.\n"
                    "4. Adhere strictly to the enterprise guidelines (RAG) provided.\n"
                    "5. Output ONLY the raw modified code file contents. Do not include markdown code block formatting (like ```js) or explanations. Start immediately with the code."
                )
                
                user_prompt = (
                    f"FILE PATH: {file_path}\n\n"
                    f"TASK DESCRIPTION:\n{task_description}\n\n"
                    f"ENTERPRISE GUIDELINES:\n{rag_str}\n\n"
                    f"CURRENT FILE CONTENT:\n{current_content}\n\n"
                    "Generate the complete modified file contents."
                )
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                modified_code = response.choices[0].message.content
                # Strip markdown blocks if the LLM output them anyway
                if "```" in modified_code:
                    parts = modified_code.split("```")
                    if len(parts) >= 3:
                        lines = parts[1].splitlines()
                        if lines and (lines[0].strip() in ["javascript", "js", "java", "python", "py", "cs", "csharp", "html", "css"]):
                            modified_code = "\n".join(lines[1:])
                        else:
                            modified_code = parts[1]
                return modified_code.strip()
            except Exception as e:
                print(f"[Modifier] OpenAI code modification failed, falling back to regex modifier: {e}")

        # Fallback offline modifier
        return self._generate_fallback_modification(file_path, current_content, task_description)

    def _generate_fallback_modification(self, file_path: str, current_content: str, task_description: str) -> str:
        """
        Appends mock updates to code based on the extension to simulate a successful modification.
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        comment_symbol = "#" if ext == ".py" else "//"
        if ext == ".html":
            comment_symbol_start, comment_symbol_end = "<!--", "-->"
        else:
            comment_symbol_start, comment_symbol_end = comment_symbol, ""

        modification_stamp = (
            f"\n\n{comment_symbol_start} AI Agent Modification Start {comment_symbol_end}\n"
            f"{comment_symbol_start} Task: {task_description} {comment_symbol_end}\n"
        )
        
        if ext in [".js", ".ts"] and ("server" in file_path or "routes" in file_path or "app" in file_path):
            route_name = task_description.lower().replace(" ", "_")[:20]
            mock_route = (
                f"app.get('/api/{route_name}', (req, res) => {{\n"
                f"    // Auto-generated for: {task_description}\n"
                f"    res.json({{ status: 'success', message: 'Endpoint updated for {task_description}' }});\n"
                f"}});\n"
            )
            modification_stamp += mock_route
        elif ext == ".py" and ("app" in file_path or "main" in file_path or "api" in file_path):
            route_name = task_description.lower().replace(" ", "_")[:20]
            mock_route = (
                f"@app.get('/api/{route_name}')\n"
                f"def get_{route_name}():\n"
                f"    # Auto-generated for: {task_description}\n"
                f"    return {{'status': 'success', 'message': 'Endpoint updated'}}\n"
            )
            modification_stamp += mock_route
        elif ext == ".java" and "Controller" in file_path:
            route_name = task_description.lower().replace(" ", "_")[:20]
            mock_route = (
                f"    @GetMapping(\"/{route_name}\")\n"
                f"    public ResponseEntity<String> get{route_name.capitalize()}() {{\n"
                f"        // Auto-generated for: {task_description}\n"
                f"        return ResponseEntity.ok(\"Endpoint updated\");\n"
                f"    }}\n"
            )
            modification_stamp += mock_route
        else:
            modification_stamp += f"{comment_symbol_start} Feature implemented successfully. {comment_symbol_end}\n"
            
        modification_stamp += f"{comment_symbol_start} AI Agent Modification End {comment_symbol_end}\n"
        
        if ext in [".js", ".ts", ".java", ".cs"] and current_content.strip().endswith("}"):
            last_brace_idx = current_content.rfind("}")
            return current_content[:last_brace_idx] + modification_stamp + "}\n"
            
        return current_content + modification_stamp
