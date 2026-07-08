import os
import uuid
import numpy as np
from typing import List, Dict, Any
from pymilvus import MilvusClient

class RetrievalAgent:
    """
    Manages Enterprise Reference Documents RAG storage and retrieval using Milvus Lite.
    Ensures zero external dependency issues by running milvus.db locally.
    """
    def __init__(self, db_path: str = "milvus.db", collection_name: str = "enterprise_docs"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.dimension = 1536  # Default dimension for text-embedding-3-small
        
        # Initialize MilvusClient (creates milvus.db locally if not exists)
        self.client = MilvusClient(uri=self.db_path)
        self._initialize_collection()

    def _initialize_collection(self):
        """
        Creates the collection if it doesn't already exist.
        """
        if not self.client.has_collection(collection_name=self.collection_name):
            print(f"[Milvus] Creating collection '{self.collection_name}' with local storage.")
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=self.dimension
            )

    def _get_embedding(self, text: str) -> List[float]:
        """
        Generates embedding using OpenAI if OPENAI_API_KEY is available;
        otherwise, falls back to a deterministic dummy vector for local POC execution.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.embeddings.create(
                    input=[text],
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"[Retrieval] OpenAI embedding failed, using fallback vector: {e}")
        
        # Fallback deterministic pseudo-random embedding vector
        np.random.seed(hash(text) % (2**32 - 1))
        vector = np.random.uniform(-1.0, 1.0, self.dimension).tolist()
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = (np.array(vector) / norm).tolist()
        return vector

    def add_document(self, title: str, content: str, category: str) -> str:
        """
        Chunks and adds a document to the collection.
        """
        doc_id = str(uuid.uuid4())
        chunks = []
        chunk_size = 800
        overlap = 150
        
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunks.append(content[start:end])
            if end == len(content):
                break
            start += chunk_size - overlap
            
        data = []
        for i, chunk in enumerate(chunks):
            embedding = self._get_embedding(chunk)
            data.append({
                "id": f"{doc_id}_{i}",
                "vector": embedding,
                "title": title,
                "content": chunk,
                "category": category
            })
            
        self.client.insert(
            collection_name=self.collection_name,
            data=data
        )
        return doc_id

    def query(self, text: str, category: str = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Queries the vector database for matching enterprise guidelines/docs.
        """
        query_vector = self._get_embedding(text)
        
        filter_expr = f'category == "{category}"' if category else ""
        
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=limit,
            filter=filter_expr,
            output_fields=["title", "content", "category"]
        )
        
        hits = []
        for r in results[0]:
            hits.append({
                "score": r["distance"],
                "title": r["entity"].get("title"),
                "content": r["entity"].get("content"),
                "category": r["entity"].get("category")
            })
        return hits
        
    def populate_default_rules(self):
        """
        Adds sample enterprise coding standards, architecture definitions, and security policies
        to demonstrate RAG capability.
        """
        defaults = [
            {
                "title": "Secure Coding Policy - Backend APIs",
                "category": "security",
                "content": "All backend APIs must enforce request validation and sanitization. Avoid raw SQL queries; use prepared statements or ORM parameters. Sensitive information should never be returned in HTTP payloads or logs. JWT tokens must be verified and have an expiry."
            },
            {
                "title": "Clean Code & Naming Guidelines",
                "category": "coding_standards",
                "content": "Follow standard naming patterns: CamelCase for Java classes, snake_case for Python, camelCase for JavaScript functions. Maintain a maximum class length of 500 lines. Keep methods clean, single-responsibility, and document logic with clear inline comments."
            },
            {
                "title": "Three-Tier Architecture Mapping Standards",
                "category": "architecture",
                "content": "UI components communicate only with Backend API controllers. Backend controllers route calls to Services, which fetch data from DB Repositories. Frontend applications must utilize a routing library. Direct DB access from frontend is forbidden."
            }
        ]
        
        existing = self.client.query(
            collection_name=self.collection_name,
            filter='category != ""',
            limit=1
        )
        
        if not existing:
            print("[Milvus] Populating default enterprise guidelines in local Milvus DB...")
            for doc in defaults:
                self.add_document(doc["title"], doc["content"], doc["category"])
