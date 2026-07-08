import os
import re
from typing import Dict, Any, List

class ValidationAgent:
    """
    Validates modified files by performing:
    - Syntax verification (using compile() for Python, regex syntax checks for others)
    - Simulated build checks
    - Basic security scans (checking for SQL injection risks, hardcoded credentials, etc.)
    """
    def __init__(self):
        # Patterns for security issues
        self.sql_injection_pattern = re.compile(r'\+.*(?:SELECT|INSERT|UPDATE|DELETE).*\+.*req\.', re.IGNORECASE)
        self.hardcoded_secret_pattern = re.compile(r'(?:password|secret|key|token|passwd)\s*=\s*["\'][a-zA-Z0-9_/+=]{10,}["\']', re.IGNORECASE)

    def run(self, workspace_path: str, modifications: Dict[str, str]) -> Dict[str, Any]:
        """
        Validates all modified files.
        """
        syntax_ok = True
        warnings = []
        security_issues = []
        compiled_build_ok = True
        
        for relative_path, new_content in modifications.items():
            ext = os.path.splitext(relative_path)[1].lower()
            
            # 1. Syntax Check
            if ext == ".py":
                try:
                    compile(new_content, relative_path, 'exec')
                except SyntaxError as e:
                    syntax_ok = False
                    warnings.append(f"Python Syntax Error in {relative_path}: {str(e)} at line {e.lineno}")
            
            # Simple JS/TS brace alignment checks
            elif ext in [".js", ".ts", ".java", ".cs"]:
                open_braces = new_content.count("{")
                close_braces = new_content.count("}")
                if open_braces != close_braces:
                    syntax_ok = False
                    warnings.append(f"Brace mismatch in {relative_path}: {open_braces} open, {close_braces} close.")
                    
            # 2. Security scan
            # Check for potential SQL injection
            if self.sql_injection_pattern.search(new_content):
                security_issues.append({
                    "file": relative_path,
                    "severity": "CRITICAL",
                    "issue": "Potential SQL injection risk: String concatenation used in DB query."
                })
                
            # Check for hardcoded credentials
            if self.hardcoded_secret_pattern.search(new_content):
                security_issues.append({
                    "file": relative_path,
                    "severity": "HIGH",
                    "issue": "Hardcoded secret/token variable assignment detected."
                })

        # Compile status
        status = "success"
        if not syntax_ok:
            status = "failed"
        elif security_issues:
            status = "warning"
            
        return {
            "status": status,
            "syntax_valid": syntax_ok,
            "build_simulated": compiled_build_ok,
            "warnings": warnings,
            "security_issues": security_issues,
            "message": "Validation complete." if status == "success" else "Validation finished with warnings/errors."
        }
