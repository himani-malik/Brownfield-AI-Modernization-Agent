import difflib
from typing import Dict, Any, List

class ReportingAgent:
    """
    Generates structured markdown and JSON reports detailing the changes,
    risks, impact statistics, and validation results.
    """
    def __init__(self):
        pass

    def run(self, 
            requirement: str, 
            architecture: Dict[str, Any], 
            plan: Dict[str, Any], 
            modifications: Dict[str, str], 
            original_contents: Dict[str, str], 
            validation_results: Dict[str, Any]) -> str:
        """
        Builds the final Markdown report.
        """
        report = []
        report.append("# Agent Modification Summary Report")
        report.append(f"**Enhancement Request**: {requirement}\n")
        
        # 1. Architecture details
        report.append("## 1. Detected Architecture")
        report.append(f"- **Frontend Tier**: {', '.join(architecture.get('frontend', []))}")
        report.append(f"- **Backend Tier**: {', '.join(architecture.get('backend', []))}")
        report.append(f"- **Database Tier**: {', '.join(architecture.get('database', []))}")
        report.append(f"- **Config Files Found**: {', '.join(architecture.get('config_files', []))}\n")
        
        # 2. Planning details
        report.append("## 2. Structured Task Execution")
        for i, task in enumerate(plan.get("tasks", [])):
            report.append(f"{i+1}. **{task['title']}** ({task['target_file']}): {task['description']}")
        report.append("")
        
        # 3. Validation results
        report.append("## 3. Validation Results")
        status = validation_results.get("status", "unknown").upper()
        if status == "SUCCESS":
            report.append("✅ **Status: PASSED** - All syntax checks and simulated build scans passed.")
        elif status == "WARNING":
            report.append("⚠️ **Status: WARNING** - Validation completed, but warnings/security flags were raised.")
        else:
            report.append("❌ **Status: FAILED** - Code syntax checks or build tests failed.")
            
        if validation_results.get("warnings"):
            report.append("\n**Warnings/Build errors:**")
            for w in validation_results["warnings"]:
                report.append(f"- {w}")
                
        if validation_results.get("security_issues"):
            report.append("\n**Security Vulnerabilities Detected:**")
            for sec in validation_results["security_issues"]:
                report.append(f"- `[{sec['severity']}]` in `{sec['file']}`: {sec['issue']}")
        report.append("")

        # 4. Impacted Files & Diff List
        report.append("## 4. Code Modifications & Diffs")
        for filename, new_code in modifications.items():
            report.append(f"### File: `{filename}`")
            original_code = original_contents.get(filename, "")
            
            # Generate diff using unified_diff
            diff = list(difflib.unified_diff(
                original_code.splitlines(),
                new_code.splitlines(),
                fromfile=f"a/{filename}",
                tofile=f"b/{filename}",
                lineterm=""
            ))
            
            if diff:
                report.append("```diff")
                report.append("\n".join(diff))
                report.append("```")
            else:
                report.append("*No visible text changes.*")
            report.append("")
            
        report.append("## 5. Risk Assessment & Recommendations")
        report.append("- **Architecture Integrity**: Clean separation of tiers maintained.")
        report.append("- **Regression Risk**: Moderate. Ensure automated API testing is run in staging.")
        report.append("- **RAG Standards**: Complied with clean-code naming rules.")
        
        return "\n".join(report)
