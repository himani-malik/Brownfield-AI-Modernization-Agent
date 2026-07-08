import os
import re
from typing import Dict, Any, List

class CodeParsingAgent:
    """
    Parses code files using a robust fallback-enabled parser.
    Extracts structural information such as classes, functions/methods, imports,
    REST API endpoints, and database queries.
    """
    def __init__(self):
        # Compiled patterns for our fallback regex parser
        self.js_import_pattern = re.compile(r'(?:import|const|let)\s+(?:[\w\s\{\},*]+)\s+(?:from|require)\s*\(?[\'"]([^\'"]+)[\'"]\)?')
        self.py_import_pattern = re.compile(r'(?:from\s+([\w\.]+)\s+import\s+[\w\*]+|import\s+([\w\.]+))')
        self.java_import_pattern = re.compile(r'import\s+([\w\.]+);')
        self.cs_import_pattern = re.compile(r'using\s+([\w\.]+);')
        
        # Endpoint patterns
        self.java_route_pattern = re.compile(r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*["\']([^"\']+)["\']')
        self.js_route_pattern = re.compile(r'(?:app|router|express)\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
        self.py_route_pattern = re.compile(r'@(?:app|router)\.(?:get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']')
        self.cs_route_pattern = re.compile(r'\[(?:HttpGet|HttpPost|HttpPut|HttpDelete|Route)\s*\(\s*["\']([^"\']+)["\']')
        
        # DB queries (e.g. SELECT, INSERT, UPDATE, DELETE, repository calls)
        self.sql_pattern = re.compile(r'(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([\w`\.]+)', re.IGNORECASE)
        self.jpa_repo_pattern = re.compile(r'interface\s+(\w+)\s+extends\s+JpaRepository')

    def run(self, workspace_path: str) -> Dict[str, Any]:
        """
        Parses all supported code files in the workspace.
        """
        parsed_data = {}
        
        for root, dirs, files in os.walk(workspace_path):
            if any(p in root for p in ["node_modules", "target", "bin", "obj", ".git", ".venv", "dist", "build"]):
                continue
                
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, workspace_path).replace("\\", "/")
                
                # Check if it's a code file we care about
                ext = os.path.splitext(file)[1].lower()
                if ext in [".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".cs", ".html", ".css"]:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            parsed_data[rel_path] = self.parse_file(rel_path, content, ext)
                    except Exception as e:
                        print(f"[Parser] Error parsing {rel_path}: {e}")
                        
        return parsed_data

    def parse_file(self, filename: str, content: str, ext: str) -> Dict[str, Any]:
        """
        Extracts structural details using standard regex AST fallback.
        """
        imports = []
        endpoints = []
        queries = []
        classes = []
        functions = []

        # 1. Extract Imports based on language
        if ext in [".js", ".jsx", ".ts", ".tsx"]:
            imports = self.js_import_pattern.findall(content)
            # Find routes
            endpoints = self.js_route_pattern.findall(content)
            # Classes & functions
            classes = re.findall(r'class\s+(\w+)', content)
            functions = re.findall(r'(?:const|let|function)\s+(\w+)\s*=\s*(?:\([^)]*\)|val)?\s*=>|function\s+(\w+)', content)
            functions = [f[0] if f[0] else f[1] for f in functions if f[0] or f[1]]

        elif ext == ".py":
            py_matches = self.py_import_pattern.findall(content)
            for m in py_matches:
                imp = m[0] if m[0] else m[1]
                if imp:
                    imports.append(imp)
            endpoints = self.py_route_pattern.findall(content)
            classes = re.findall(r'class\s+(\w+)', content)
            functions = re.findall(r'def\s+(\w+)\s*\(', content)

        elif ext == ".java":
            imports = self.java_import_pattern.findall(content)
            endpoints = self.java_route_pattern.findall(content)
            classes = re.findall(r'(?:public\s+|private\s+)?class\s+(\w+)', content)
            functions = re.findall(r'(?:public|private|protected|static|\s) +[\w\<\>\[\]]+\s+(\w+)\s*\(', content)
            # Remove Java keywords that might match method declarations
            keywords = {"class", "if", "for", "while", "switch", "return", "catch", "new", "throw"}
            functions = [f for f in functions if f not in keywords]
            
            # Check for Spring Data Repositories
            if self.jpa_repo_pattern.search(content):
                queries.append("JPA Repository Database Access")

        elif ext == ".cs":
            imports = self.cs_import_pattern.findall(content)
            endpoints = self.cs_route_pattern.findall(content)
            classes = re.findall(r'class\s+(\w+)', content)
            functions = re.findall(r'(?:public|private|protected|internal|static|\s) +[\w\<\>\[\]]+\s+(\w+)\s*\(', content)
            keywords = {"class", "if", "for", "while", "switch", "return", "catch", "new", "using", "namespace"}
            functions = [f for f in functions if f not in keywords]

        # 2. Look for SQL Queries across all backends/configurations
        sql_matches = self.sql_pattern.findall(content)
        for op, table in sql_matches:
            queries.append(f"{op.upper()} {table}")

        # Clean up lists
        imports = list(set(imports))
        endpoints = list(set(endpoints))
        queries = list(set(queries))
        classes = list(set(classes))
        functions = list(set(functions))

        # Check for DB calls by sniffing common patterns (like Prisma, Entity Framework, Hibernate, raw pg/mysql)
        db_keywords = ["db.query", "db.execute", "prisma.", "context.", "dbContext", "entityManager", "connection.query"]
        for kw in db_keywords:
            if kw in content:
                queries.append(f"ORM/DB call: {kw}")
        queries = list(set(queries))

        return {
            "filename": filename,
            "extension": ext,
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "endpoints": endpoints,
            "database_queries": queries,
            "lines_of_code": len(content.splitlines())
        }
