"""
Step 1: Basic Hello World RAG on BigQuery
Proof of Concept Implementation
"""

from google.cloud import bigquery
from google.cloud import aiplatform
import numpy as np
from typing import List, Dict, Any
import time

class HelloWorldRAG:
    """Basic RAG implementation on BigQuery"""
    
    def __init__(self, project_id: str, dataset_id: str = "rag_poc"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        
        # Initialize Vertex AI for embeddings
        aiplatform.init(project=project_id, location="us-central1")
        
    def setup_bigquery_schema(self):
        """Create BigQuery dataset and tables for RAG"""
        
        # Create dataset
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "us-central1"
        dataset.description = "RAG POC for manufacturing documents"
        
        try:
            dataset = self.client.create_dataset(dataset, timeout=30)
            print(f"Created dataset {dataset_id}")
        except Exception as e:
            print(f"Dataset may already exist: {e}")
        
        # Create embeddings table
        table_id = f"{dataset_id}.document_embeddings"
        schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_text", "STRING"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("metadata", "JSON"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
        ]
        
        table = bigquery.Table(table_id, schema=schema)
        try:
            table = self.client.create_table(table)
            print(f"Created table {table_id}")
        except Exception as e:
            print(f"Table may already exist: {e}")
            
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Vertex AI"""
        from vertexai.language_models import TextEmbeddingModel
        
        model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        embeddings = model.get_embeddings([text])
        return embeddings[0].values
    
    def insert_document(self, doc_id: str, text: str, metadata: Dict = None):
        """Insert document with embeddings into BigQuery"""
        
        # Generate chunks (simple fixed-size for POC)
        chunk_size = 500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        rows_to_insert = []
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embedding(chunk)
            
            row = {
                "document_id": doc_id,
                "chunk_id": f"{doc_id}_chunk_{i}",
                "chunk_text": chunk,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": None  # Will use default CURRENT_TIMESTAMP
            }
            rows_to_insert.append(row)
        
        # Insert rows
        table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings"
        errors = self.client.insert_rows_json(table_id, rows_to_insert)
        
        if errors:
            print(f"Error inserting rows: {errors}")
        else:
            print(f"Inserted {len(rows_to_insert)} chunks for document {doc_id}")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Build BigQuery query with cosine similarity
        # Note: This is simplified - production would use optimized vector search
        embedding_str = ",".join(str(x) for x in query_embedding)
        
        query_sql = f"""
        WITH query_embedding AS (
            SELECT [{embedding_str}] as embedding
        ),
        similarities AS (
            SELECT 
                de.document_id,
                de.chunk_id,
                de.chunk_text,
                de.metadata,
                -- Simplified cosine similarity calculation
                (
                    SELECT SUM(a * b) / 
                    (SQRT(SUM(a * a)) * SQRT(SUM(b * b)))
                    FROM UNNEST(de.embedding) a WITH OFFSET pos1,
                         UNNEST((SELECT embedding FROM query_embedding)) b WITH OFFSET pos2
                    WHERE pos1 = pos2
                ) as similarity_score
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings` de
        )
        SELECT *
        FROM similarities
        WHERE similarity_score > 0.5
        ORDER BY similarity_score DESC
        LIMIT {k}
        """
        
        # Execute query and measure time
        start_time = time.time()
        query_job = self.client.query(query_sql)
        results = list(query_job.result())
        query_time = time.time() - start_time
        
        # Format results
        formatted_results = []
        for row in results:
            formatted_results.append({
                "document_id": row.document_id,
                "chunk_id": row.chunk_id,
                "chunk_text": row.chunk_text,
                "similarity_score": row.similarity_score,
                "metadata": row.metadata
            })
        
        print(f"Query completed in {query_time:.2f} seconds")
        return formatted_results

def run_hello_world_test():
    """Run basic Hello World RAG test"""
    
    # Initialize
    rag = HelloWorldRAG(
        project_id="your-project-id",  # Replace with actual project
        dataset_id="rag_poc"
    )
    
    # Setup schema
    print("Setting up BigQuery schema...")
    rag.setup_bigquery_schema()
    
    # Insert sample manufacturing documents
    print("\nInserting sample documents...")
    
    sample_docs = [
        {
            "id": "doc_001",
            "text": "Manufacturing process for semiconductor wafer production involves photolithography, etching, and deposition steps. Quality control is critical at each stage.",
            "metadata": {"type": "process", "facility": "fab_1"}
        },
        {
            "id": "doc_002", 
            "text": "Equipment maintenance schedule for ion implanter requires daily checks, weekly calibration, and monthly deep cleaning. Preventive maintenance reduces downtime.",
            "metadata": {"type": "maintenance", "equipment": "ion_implanter"}
        },
        {
            "id": "doc_003",
            "text": "Defect analysis shows particle contamination is the leading cause of yield loss. Clean room protocols must be strictly enforced.",
            "metadata": {"type": "quality", "issue": "contamination"}
        }
    ]
    
    for doc in sample_docs:
        rag.insert_document(doc["id"], doc["text"], doc["metadata"])
    
    # Test search
    print("\nTesting search functionality...")
    
    test_queries = [
        "How to maintain ion implanter equipment?",
        "What causes yield loss in manufacturing?",
        "Semiconductor wafer production process"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = rag.search(query, k=3)
        
        for i, result in enumerate(results, 1):
            print(f"  Result {i}:")
            print(f"    Document: {result['document_id']}")
            print(f"    Score: {result['similarity_score']:.3f}")
            print(f"    Text: {result['chunk_text'][:100]}...")
    
    print("\n✅ Hello World RAG test completed!")

if __name__ == "__main__":
    run_hello_world_test()