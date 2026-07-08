import os
import networkx as nx
from typing import Dict, Any, List, Set, Tuple

class DependencyAnalysisAgent:
    """
    Constructs a NetworkX directed dependency graph from parsed files.
    Performs impact analysis to detect cascading file modifications across tiers.
    """
    def __init__(self):
        pass

    def run(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds the graph and serializes it.
        """
        G = nx.DiGraph()
        
        # 1. Add all files as nodes
        for filename, info in parsed_data.items():
            G.add_node(filename, type="file", ext=info["extension"], info=info)

        # 2. Extract and match endpoints
        endpoint_to_file = {}
        for filename, info in parsed_data.items():
            for ep in info["endpoints"]:
                # Normalize endpoint (remove trailing/leading slashes for matching)
                norm_ep = ep.strip("/")
                endpoint_to_file[norm_ep] = filename

        # 3. Add edges: Imports
        for filename, info in parsed_data.items():
            for imp in info["imports"]:
                # Try to match import to actual file in workspace
                resolved_file = self._resolve_import(filename, imp, list(parsed_data.keys()))
                if resolved_file:
                    G.add_edge(filename, resolved_file, relation="import")

        # 4. Add edges: API Calls (Frontend -> Backend)
        for filename, info in parsed_data.items():
            # Check if this is a frontend file (HTML, JS/TS/JSX/TSX containing fetch/axios calls)
            if info["extension"] in [".html", ".js", ".jsx", ".ts", ".tsx"]:
                # We search the backend endpoints list to see if frontend mentions them
                for norm_ep, backend_file in endpoint_to_file.items():
                    # We check if the backend route pattern is found in the frontend file
                    # We can load the file content, or if we want it robust, scan the endpoints list
                    # Since we don't have the original raw file content directly here, we check imports/strings
                    # (in a real system we'd run regex on the content; for the POC we search for parts of the ep string)
                    if norm_ep and norm_ep in filename: # simple check, but let's make it smarter
                        G.add_edge(filename, backend_file, relation="api_call")

        # 5. Add edges: Backend -> Database
        db_node = "Database"
        G.add_node(db_node, type="database")
        
        for filename, info in parsed_data.items():
            if info["database_queries"]:
                G.add_edge(filename, db_node, relation="database_access")

        # Generate a serialized representation of the graph for JSON API / UI visualization
        nodes_list = []
        for node, attrs in G.nodes(data=True):
            nodes_list.append({
                "id": node,
                "type": attrs.get("type", "unknown"),
                "ext": attrs.get("ext", "")
            })
            
        edges_list = []
        for u, v, attrs in G.edges(data=True):
            edges_list.append({
                "source": u,
                "target": v,
                "relation": attrs.get("relation", "dependency")
            })

        return {
            "graph": G, # Return NetworkX object for local calculations
            "serialized_graph": {
                "nodes": nodes_list,
                "edges": edges_list
            }
        }

    def analyze_impact(self, G: nx.DiGraph, initial_modified_files: List[str]) -> List[str]:
        """
        Traces transitive dependencies downstream (transitive closures / descendants)
        to identify all files impacted by changing the initial files.
        """
        impacted = set(initial_modified_files)
        
        # We look at both upstream and downstream since backend changes affect frontend,
        # and model changes affect controllers. In a directed graph, if file A imports B,
        # changing B impacts A. So we must traverse the graph in REVERSE to find affected nodes!
        for file in initial_modified_files:
            if file in G:
                # Find all nodes that can reach this node (ancestors in directed graph)
                # Since A -> B represents A imports B, changing B means A is affected.
                # In NetworkX, ancestors(G, B) returns all nodes that have a path to B.
                ancestors = nx.ancestors(G, file)
                impacted.update(ancestors)
                
                # Also include direct successors (if we modify code, things it uses might need checks)
                successors = G.successors(file)
                impacted.update(successors)

        # Remove "Database" from files list (since it's a virtual node)
        if "Database" in impacted:
            impacted.remove("Database")
            
        return list(impacted)

    def _resolve_import(self, current_file: str, import_str: str, all_files: List[str]) -> str:
        """
        Tries to resolve import paths to files in the codebase.
        Handles relative imports (e.g. './service', '../controller') and exact matches.
        """
        # Clean import string
        import_str = import_str.replace("\"", "").replace("'", "").strip()
        
        # 1. Check direct matches or suffix matches
        for f in all_files:
            if f.endswith(import_str) or import_str in f:
                return f

        # 2. Check relative resolving
        curr_dir = os.path.dirname(current_file)
        if import_str.startswith("."):
            parts = import_str.split("/")
            temp_dir = curr_dir
            for p in parts:
                if p == "..":
                    temp_dir = os.path.dirname(temp_dir)
                elif p != ".":
                    temp_dir = os.path.join(temp_dir, p)
            
            # Check if matching files exist with extensions
            for f in all_files:
                f_no_ext = os.path.splitext(f)[0]
                if f_no_ext == temp_dir.replace("\\", "/"):
                    return f
                    
        return None
