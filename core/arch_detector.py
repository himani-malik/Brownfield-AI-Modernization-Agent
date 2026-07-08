import os
import json
from typing import Dict, Any, List

class ArchitectureDetectionAgent:
    """
    Scans the workspace to identify the stack used for frontend, backend, and database tiers.
    """
    def __init__(self):
        pass

    def run(self, workspace_path: str) -> Dict[str, Any]:
        if not os.path.exists(workspace_path):
            return {"error": "Workspace directory does not exist."}

        frontend_tech = []
        backend_tech = []
        database_tech = []
        
        detected_configs = []
        
        # Walk workspace to analyze files and extensions
        for root, dirs, files in os.walk(workspace_path):
            # Skip common dependency folders to avoid false positives
            if any(p in root for p in ["node_modules", "target", "bin", "obj", ".git", ".venv"]):
                continue

            for file in files:
                filepath = os.path.join(root, file)
                
                # Check config files
                if file == "package.json":
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                            
                            # Frontend checks
                            if "react" in deps:
                                frontend_tech.append("React")
                            if "angular" in deps or "@angular/core" in deps:
                                frontend_tech.append("Angular")
                            if "vue" in deps:
                                frontend_tech.append("Vue.js")
                                
                            # Backend checks
                            if "express" in deps:
                                backend_tech.append("Node.js (Express)")
                            if "typescript" in deps:
                                detected_configs.append("TypeScript Configured")
                    except Exception:
                        pass
                
                elif file == "pom.xml":
                    backend_tech.append("Spring Boot (Java)")
                    detected_configs.append("Maven POM")
                    # Check pom contents for database drivers
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if "mysql-connector" in content:
                                database_tech.append("MySQL")
                            if "postgresql" in content:
                                database_tech.append("PostgreSQL")
                            if "h2" in content:
                                database_tech.append("H2 Database (In-Memory)")
                    except Exception:
                        pass

                elif file == "build.gradle":
                    backend_tech.append("Spring Boot (Java/Gradle)")
                    detected_configs.append("Gradle Build")

                elif file.endswith(".csproj"):
                    backend_tech.append(".NET Core (C#)")
                    detected_configs.append("C# Project File")
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if "Microsoft.EntityFrameworkCore.SqlServer" in content:
                                database_tech.append("SQL Server")
                            if "Npgsql.EntityFrameworkCore.PostgreSQL" in content:
                                database_tech.append("PostgreSQL")
                    except Exception:
                        pass

                elif file == "requirements.txt" or file == "Pipfile" or file == "pyproject.toml":
                    backend_tech.append("Python (FastAPI/Flask/Django)")
                    detected_configs.append("Python Package Specs")
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if "psycopg2" in content:
                                database_tech.append("PostgreSQL")
                            if "mysqlclient" in content or "pymysql" in content:
                                database_tech.append("MySQL")
                    except Exception:
                        pass

                # Check file extensions or inline code strings
                elif file.endswith(".js") or file.endswith(".ts") or file.endswith(".jsx") or file.endswith(".tsx"):
                    if not any(x in frontend_tech for x in ["React", "Angular", "Vue.js"]):
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read(2000) # Read first 2000 chars
                                if "import React" in content or "from 'react'" in content or "from \"react\"" in content:
                                    frontend_tech.append("React")
                                if "@Component" in content and ("from '@angular/" in content or "from \"@angular/" in content):
                                    frontend_tech.append("Angular")
                        except Exception:
                            pass

                elif file.endswith(".html"):
                    if "HTML/CSS/JavaScript" not in frontend_tech:
                        frontend_tech.append("HTML/CSS/JavaScript")

                # Database connection configuration scanning
                elif file in ["application.properties", "application.yml", "appsettings.json", ".env"]:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                            if "mysql" in content or "jdbc:mysql:" in content:
                                database_tech.append("MySQL")
                            if "postgresql" in content or "jdbc:postgresql:" in content:
                                database_tech.append("PostgreSQL")
                            if "sqlserver" in content or "jdbc:sqlserver:" in content or "sql server" in content:
                                database_tech.append("SQL Server")
                            if "sqlite" in content or "jdbc:sqlite:" in content:
                                database_tech.append("SQLite")
                    except Exception:
                        pass

        # Deduplicate list
        frontend_tech = list(set(frontend_tech))
        backend_tech = list(set(backend_tech))
        database_tech = list(set(database_tech))
        
        # Default fallbacks
        if not frontend_tech:
            frontend_tech = ["HTML/CSS/JavaScript (Fallback)"]
        if not backend_tech:
            backend_tech = ["Generic Node.js / HTML Backend (Fallback)"]
        if not database_tech:
            database_tech = ["PostgreSQL / MySQL / File-based SQLite (Fallback)"]

        return {
            "frontend": frontend_tech,
            "backend": backend_tech,
            "database": database_tech,
            "config_files": detected_configs
        }
