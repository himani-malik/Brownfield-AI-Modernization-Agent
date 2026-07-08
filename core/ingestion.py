import os
import shutil
import zipfile
import subprocess
import urllib.parse
from typing import Dict, Any

class ProjectIngestionAgent:
    """
    Ingests projects from git repositories or zip files and prepares a local workspace.
    """
    def __init__(self, workspace_base_dir: str):
        self.workspace_base_dir = workspace_base_dir
        os.makedirs(workspace_base_dir, exist_ok=True)

    def run(self, source: str) -> Dict[str, Any]:
        """
        source can be:
        1. A git URL (e.g., https://github.com/user/repo.git)
        2. A local path to a zip file
        3. A local directory path
        
        Returns:
            Dict containing status, local_path, and file_count.
        """
        # Determine unique workspace folder name
        if source.endswith(".git") or "github.com" in source:
            # Git Repo
            parsed = urllib.parse.urlparse(source)
            repo_name = os.path.basename(parsed.path).replace(".git", "")
            target_dir = os.path.join(self.workspace_base_dir, f"git_{repo_name}")
            
            # Clean up target directory if it exists
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
                
            print(f"[Ingestion] Cloning repository {source} into {target_dir}")
            try:
                # Run git clone
                result = subprocess.run(
                    ["git", "clone", source, target_dir],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                return {
                    "status": "success",
                    "local_path": target_dir,
                    "file_count": self._count_files(target_dir),
                    "message": "Repository successfully cloned."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "local_path": "",
                    "file_count": 0,
                    "message": f"Failed to clone repository: {str(e)}"
                }
                
        elif source.endswith(".zip") and os.path.exists(source):
            # Local ZIP file
            zip_name = os.path.basename(source).replace(".zip", "")
            target_dir = os.path.join(self.workspace_base_dir, f"zip_{zip_name}")
            
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            os.makedirs(target_dir, exist_ok=True)
            
            print(f"[Ingestion] Extracting ZIP {source} to {target_dir}")
            try:
                with zipfile.ZipFile(source, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
                return {
                    "status": "success",
                    "local_path": target_dir,
                    "file_count": self._count_files(target_dir),
                    "message": "ZIP file successfully extracted."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "local_path": "",
                    "file_count": 0,
                    "message": f"Failed to extract ZIP: {str(e)}"
                }
                
        elif os.path.isdir(source):
            # Already a local directory - copy it to base_dir to avoid modifying user's original copy
            dir_name = os.path.basename(os.path.normpath(source))
            target_dir = os.path.join(self.workspace_base_dir, f"local_{dir_name}")
            
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
                
            print(f"[Ingestion] Copying local directory {source} to {target_dir}")
            try:
                shutil.copytree(source, target_dir)
                return {
                    "status": "success",
                    "local_path": target_dir,
                    "file_count": self._count_files(target_dir),
                    "message": "Local directory successfully copied to workspace."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "local_path": "",
                    "file_count": 0,
                    "message": f"Failed to copy local directory: {str(e)}"
                }
        else:
            return {
                "status": "error",
                "local_path": "",
                "file_count": 0,
                "message": f"Invalid source specified: {source}. Must be a git repository, a valid local ZIP, or a local directory."
            }

    def _count_files(self, path: str) -> int:
        count = 0
        for _, _, files in os.walk(path):
            count += len(files)
        return count
