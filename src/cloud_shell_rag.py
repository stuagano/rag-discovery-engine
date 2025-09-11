"""
Google Cloud RAG Implementation for Cloud Shell
Pure GCP solution using BigQuery and Vertex AI
"""

import os
import time
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv

# Google Cloud imports
from google.cloud import bigquery
from google.cloud import aiplatform
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel

# Text processing
class TextSplitter:
    """Simple text splitter for chunking documents"""
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - self.chunk_overlap if end < len(text) else end
        return chunks

class GoogleCloudRAG:
    """Production-ready RAG system using only Google Cloud services"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1") 
        self.dataset_id = os.getenv("BIGQUERY_DATASET", "rag_poc")
        
        if not self.project_id:
            # Try to get from gcloud config if not in env
            import subprocess
            try:
                result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                                      capture_output=True, text=True)
                self.project_id = result.stdout.strip()
            except:
                raise ValueError("GOOGLE_CLOUD_PROJECT must be set or gcloud must be configured")
        
        print(f"🔧 Initializing Google Cloud RAG for project: {self.project_id}")
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=self.project_id)
        
        # Validate and initialize Vertex AI
        self.region = self._validate_vertex_region(self.region)
        vertexai.init(project=self.project_id, location=self.region)
        
        # Vertex AI Embedding Model
        self.embedding_model_name = os.getenv("VERTEX_EMBEDDING_MODEL", "gemini-embedding-001")
        self.embedding_model = TextEmbeddingModel.from_pretrained(self.embedding_model_name)
        self.embedding_dim = 768  # Gecko embedding dimension
        
        # Vertex AI Generative Model for answer synthesis
        self.generation_model_name = os.getenv("VERTEX_GENERATION_MODEL", "gemini-2.5-flash")
        self.generation_model = GenerativeModel(self.generation_model_name)
        
        # Text splitter
        chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)
        
        # Performance settings
        self.batch_size = int(os.getenv("BATCH_SIZE", "100"))
        
        print(f"✅ Google Cloud RAG initialized")
        print(f"   • Embedding Model: {self.embedding_model_name}")
        print(f"   • Generation Model: {self.generation_model_name}")
        print(f"   • BigQuery Dataset: {self.dataset_id}")
    
    def _validate_vertex_region(self, region: str) -> str:
        """Validate and correct region for Vertex AI compatibility"""
        vertex_regions = {
            'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2',
            'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4',
            'asia-east1', 'asia-northeast1', 'asia-southeast1'
        }
        if region in vertex_regions:
            return region
        else:
            print(f"⚠️ Region '{region}' not supported by Vertex AI, using us-central1")
            return 'us-central1'
    
    def setup_bigquery_resources(self) -> Dict[str, Any]:
        """Create BigQuery dataset and tables optimized for vector search"""
        
        print("🏗️  Setting up BigQuery resources...")
        
        # Create dataset
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = self.region
        dataset.description = "RAG POC using Google Cloud services"
        
        try:
            dataset = self.bq_client.create_dataset(dataset, timeout=30)
            print(f"   ✓ Created dataset: {dataset_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   ✓ Dataset exists: {dataset_id}")
            else:
                raise e
        
        # Create embeddings table with optimizations
        table_id = f"{dataset_id}.document_embeddings"
        schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_text", "STRING"),
            bigquery.SchemaField("chunk_index", "INTEGER"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("embedding_model", "STRING"),
            bigquery.SchemaField("metadata", "JSON"),
            bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP()"),
        ]
        
        table = bigquery.Table(table_id, schema=schema)
        
        # Add partitioning for performance
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="created_at"
        )
        
        # Add clustering for better query performance
        table.clustering_fields = ["document_id", "chunk_index"]
        
        try:
            table = self.bq_client.create_table(table)
            print(f"   ✓ Created table: {table_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   ✓ Table exists: {table_id}")
            else:
                raise e
        
        # Create vector search function (for demonstration)
        create_function_sql = f"""
        CREATE OR REPLACE FUNCTION `{self.project_id}.{self.dataset_id}.cosine_similarity`(
            vector1 ARRAY<FLOAT64>,
            vector2 ARRAY<FLOAT64>
        ) AS (
            (
                SELECT 
                    COALESCE(
                        SUM(v1 * v2) / (
                            SQRT(SUM(v1 * v1)) * SQRT(SUM(v2 * v2))
                        ),
                        0
                    )
                FROM UNNEST(vector1) v1 WITH OFFSET pos1
                JOIN UNNEST(vector2) v2 WITH OFFSET pos2
                ON pos1 = pos2
            )
        );
        """
        
        try:
            query_job = self.bq_client.query(create_function_sql)
            query_job.result()
            print(f"   ✓ Created cosine similarity function")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   ✓ Function exists: cosine_similarity")
            else:
                print(f"   ⚠ Function creation skipped: {str(e)[:100]}")
        
        return {"dataset": dataset_id, "table": table_id}
    
    def generate_sample_documents(self, num_docs: int = None) -> List[Dict[str, Any]]:
        """Generate sample manufacturing documents for testing"""
        
        if num_docs is None:
            num_docs = int(os.getenv("NUM_TEST_DOCS", "10"))
        
        print(f"📄 Generating {num_docs} sample manufacturing documents...")
        
        templates = [
            {
                "type": "maintenance_manual",
                "title": "Equipment Maintenance Manual",
                "content": """
                Equipment Maintenance Schedule and Procedures:
                
                Daily Maintenance Tasks:
                1. Check vacuum levels - Target: < 1e-6 Torr
                2. Verify temperature stability - Range: 23°C ± 0.5°C
                3. Monitor particle counts - Threshold: < 10 particles/cf
                4. Inspect safety interlocks - All systems operational
                
                Weekly Maintenance:
                - Clean optical components with approved solvents
                - Calibrate measurement systems
                - Replace consumable filters
                - Document all maintenance activities
                
                Monthly Deep Maintenance:
                - Complete system calibration
                - Replace all seals and o-rings
                - Perform electrical safety testing
                - Update maintenance database
                
                Safety Requirements:
                - Lockout/tagout procedures mandatory
                - Clean room protocol required
                - ESD protection equipment required
                - Chemical handling certification needed
                """
            },
            {
                "type": "quality_inspection",
                "title": "Quality Control Report",
                "content": """
                Manufacturing Quality Inspection Report:
                
                Product Specifications:
                - Wafer diameter: 300mm ± 0.5mm
                - Thickness: 775μm ± 25μm
                - Resistivity: 10-20 Ω·cm
                - Surface roughness: < 0.5nm Ra
                
                Inspection Results:
                - Visual inspection: PASS - No visible defects
                - Dimensional check: PASS - Within tolerance
                - Electrical test: PASS - Resistivity 15.2 Ω·cm
                - Surface analysis: PASS - Roughness 0.3nm Ra
                
                Defect Analysis:
                - Total defects found: 2
                - Critical defects: 0
                - Minor defects: 2 (edge exclusion zone)
                - Action required: None - within acceptance criteria
                
                Quality Certification:
                - Lot approved for production use
                - ISO 9001 compliant
                - Certificate number: QC-2024-001
                """
            },
            {
                "type": "process_specification",
                "title": "Manufacturing Process Specification",
                "content": """
                Process Control Specification:
                
                Process Parameters:
                - Temperature: 850°C ± 5°C
                - Pressure: 10 Torr ± 0.5 Torr
                - Gas flow rate: 100 sccm ± 2 sccm
                - Process time: 120 seconds ± 5 seconds
                
                Critical Control Points:
                1. Pre-process particle count < 5
                2. Temperature uniformity < 2°C across wafer
                3. Gas purity > 99.999%
                4. Chamber base pressure < 1e-7 Torr
                
                Process Monitoring:
                - Real-time temperature tracking
                - Continuous pressure monitoring
                - Gas flow verification every 10 seconds
                - End-point detection system active
                
                Quality Gates:
                - Pre-process inspection required
                - In-situ monitoring mandatory
                - Post-process measurement within 30 minutes
                - SPC data collection for all parameters
                """
            }
        ]
        
        documents = []
        for i in range(num_docs):
            template = templates[i % len(templates)]
            doc_id = f"doc_{i+1:04d}"
            
            documents.append({
                "document_id": doc_id,
                "title": f"{template['title']} - {doc_id}",
                "content": template["content"],
                "document_type": template["type"],
                "facility": f"FAB-{(i % 3) + 1}",
                "created_date": datetime.now().isoformat()
            })
        
        print(f"   ✓ Generated {len(documents)} documents")
        return documents
    
    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """Process documents into chunks with Vertex AI embeddings"""
        
        print(f"⚙️  Processing {len(documents)} documents with Vertex AI...")
        
        processed_chunks = []
        
        for doc in tqdm(documents, desc="Processing documents"):
            # Split into chunks
            chunks = self.text_splitter.split_text(doc["content"])
            
            # Process chunks in batches
            chunk_texts = []
            chunk_data = []
            
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc['document_id']}_chunk_{i:04d}"
                
                chunk_info = {
                    "document_id": doc["document_id"],
                    "chunk_id": chunk_id,
                    "chunk_text": chunk_text,
                    "chunk_index": i,
                    "embedding_model": self.embedding_model_name,
                    "metadata": {
                        "title": doc["title"],
                        "document_type": doc["document_type"],
                        "facility": doc.get("facility", "unknown"),
                        "created_date": doc["created_date"],
                        "chunk_length": len(chunk_text),
                        "total_chunks": len(chunks)
                    }
                }
                
                chunk_texts.append(chunk_text)
                chunk_data.append(chunk_info)
                
                # Process in batches for efficiency
                if len(chunk_texts) >= self.batch_size:
                    embeddings = self.embedding_model.get_embeddings(chunk_texts)
                    
                    for chunk_info, embedding in zip(chunk_data, embeddings):
                        chunk_info["embedding"] = embedding.values
                        processed_chunks.append(chunk_info)
                    
                    chunk_texts = []
                    chunk_data = []
            
            # Process remaining chunks
            if chunk_texts:
                embeddings = self.embedding_model.get_embeddings(chunk_texts)
                
                for chunk_info, embedding in zip(chunk_data, embeddings):
                    chunk_info["embedding"] = embedding.values
                    processed_chunks.append(chunk_info)
        
        print(f"   ✓ Processed {len(processed_chunks)} chunks with Vertex AI embeddings")
        return processed_chunks
    
    def upload_to_bigquery(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Upload processed chunks to BigQuery"""
        
        print(f"📤 Uploading {len(chunks)} chunks to BigQuery...")
        
        table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings"
        
        # Convert to DataFrame
        df = pd.DataFrame(chunks)
        
        # Configure load job
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("document_id", "STRING"),
                bigquery.SchemaField("chunk_id", "STRING"),
                bigquery.SchemaField("chunk_text", "STRING"),
                bigquery.SchemaField("chunk_index", "INTEGER"),
                bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
                bigquery.SchemaField("embedding_model", "STRING"),
                bigquery.SchemaField("metadata", "JSON"),
            ],
            write_disposition="WRITE_APPEND",
        )
        
        # Upload to BigQuery
        job = self.bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Wait for completion
        
        print(f"   ✓ Successfully uploaded to {table_id}")
        
        return {
            "status": "success",
            "chunks_uploaded": len(chunks),
            "table": table_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def query(self, query_text: str, k: int = 5) -> Dict[str, Any]:
        """Query the RAG system using Vertex AI and BigQuery"""
        
        print(f"🔍 Querying: {query_text[:50]}...")
        
        # Generate query embedding using Vertex AI
        query_embedding = self.embedding_model.get_embeddings([query_text])[0].values
        
        # Build BigQuery similarity search
        embedding_str = ",".join(str(x) for x in query_embedding)
        
        sql_query = f"""
        WITH query_embedding AS (
            SELECT [{embedding_str}] as query_vec
        ),
        similarities AS (
            SELECT 
                de.document_id,
                de.chunk_id,
                de.chunk_text,
                de.metadata,
                -- Cosine similarity using BigQuery
                `{self.project_id}.{self.dataset_id}.cosine_similarity`(
                    de.embedding,
                    (SELECT query_vec FROM query_embedding)
                ) as similarity_score
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings` de
        )
        SELECT *
        FROM similarities
        WHERE similarity_score > 0.3
        ORDER BY similarity_score DESC
        LIMIT {k}
        """
        
        # Execute query
        start_time = time.time()
        query_job = self.bq_client.query(sql_query)
        results = list(query_job.result())
        query_time = time.time() - start_time
        
        # Format results
        formatted_results = []
        for row in results:
            formatted_results.append({
                "document_id": row.document_id,
                "chunk_id": row.chunk_id,
                "chunk_text": row.chunk_text,
                "similarity_score": float(row.similarity_score),
                "metadata": json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata
            })
        
        # Generate answer using Vertex AI Gemini
        if formatted_results:
            context = "\n\n".join([r["chunk_text"] for r in formatted_results[:3]])
            
            prompt = f"""Based on the following manufacturing documentation, provide a concise and accurate answer to the question.

Context:
{context}

Question: {query_text}

Answer:"""
            
            response = self.generation_model.generate_content(prompt)
            answer = response.text
        else:
            answer = "No relevant information found in the documentation."
        
        return {
            "query": query_text,
            "answer": answer,
            "sources": formatted_results,
            "query_time_ms": query_time * 1000,
            "num_sources": len(formatted_results),
            "models_used": {
                "embedding": self.embedding_model_name,
                "generation": self.generation_model_name
            }
        }
    
    def deploy(self) -> Dict[str, Any]:
        """Complete deployment of Google Cloud RAG system"""
        
        print("🚀 Starting Google Cloud RAG deployment...\n")
        
        try:
            # Step 1: Setup BigQuery
            bq_resources = self.setup_bigquery_resources()
            
            # Step 2: Generate sample documents
            documents = self.generate_sample_documents()
            
            # Step 3: Process with Vertex AI
            chunks = self.process_documents(documents)
            
            # Step 4: Upload to BigQuery
            upload_result = self.upload_to_bigquery(chunks)
            
            print("\n✅ Google Cloud RAG system deployed successfully!")
            
            return {
                "success": True,
                "project_id": self.project_id,
                "documents_processed": len(documents),
                "embeddings_generated": len(chunks),
                "bigquery_dataset": self.dataset_id,
                "vertex_ai_models": {
                    "embedding": self.embedding_model_name,
                    "generation": self.generation_model_name
                },
                "upload_result": upload_result
            }
            
        except Exception as e:
            print(f"❌ Deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_tests(self) -> Dict[str, Dict]:
        """Run validation tests"""
        
        print("🧪 Running Google Cloud RAG tests...\n")
        
        test_results = {}
        
        # Test 1: Vertex AI Embedding
        try:
            test_text = "Test embedding generation"
            embedding = self.embedding_model.get_embeddings([test_text])[0].values
            test_results["vertex_ai_embedding"] = {
                "passed": len(embedding) == self.embedding_dim,
                "message": f"Generated {len(embedding)}-dim embedding with {self.embedding_model_name}"
            }
        except Exception as e:
            test_results["vertex_ai_embedding"] = {
                "passed": False,
                "message": f"Embedding test failed: {str(e)}"
            }
        
        # Test 2: BigQuery connectivity
        try:
            query = f"SELECT COUNT(*) as total FROM `{self.project_id}.{self.dataset_id}.document_embeddings`"
            result = list(self.bq_client.query(query).result())[0]
            test_results["bigquery_connectivity"] = {
                "passed": True,
                "message": f"BigQuery connected: {result.total} chunks found"
            }
        except Exception as e:
            test_results["bigquery_connectivity"] = {
                "passed": False,
                "message": f"BigQuery test failed: {str(e)}"
            }
        
        # Test 3: Query execution
        try:
            result = self.query("What is the maintenance schedule?")
            test_results["query_execution"] = {
                "passed": len(result["sources"]) > 0,
                "message": f"Query returned {len(result['sources'])} results in {result['query_time_ms']:.2f}ms"
            }
        except Exception as e:
            test_results["query_execution"] = {
                "passed": False,
                "message": f"Query test failed: {str(e)}"
            }
        
        # Test 4: Gemini generation
        try:
            prompt = "Test generation"
            response = self.generation_model.generate_content(prompt)
            test_results["gemini_generation"] = {
                "passed": len(response.text) > 0,
                "message": f"Gemini {self.generation_model_name} working"
            }
        except Exception as e:
            test_results["gemini_generation"] = {
                "passed": False,
                "message": f"Gemini test failed: {str(e)}"
            }
        
        return test_results
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        
        stats_query = f"""
        SELECT 
            COUNT(DISTINCT document_id) as total_documents,
            COUNT(*) as total_chunks,
            COUNT(DISTINCT embedding_model) as models_used
        FROM `{self.project_id}.{self.dataset_id}.document_embeddings`
        """
        
        try:
            result = list(self.bq_client.query(stats_query).result())[0]
            
            return {
                "status": "healthy",
                "project_id": self.project_id,
                "dataset": self.dataset_id,
                "google_cloud_services": {
                    "bigquery": "active",
                    "vertex_ai": "active",
                    "embedding_model": self.embedding_model_name,
                    "generation_model": self.generation_model_name
                },
                "statistics": {
                    "total_documents": result.total_documents,
                    "total_chunks": result.total_chunks,
                    "models_used": result.models_used
                },
                "region": self.region,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }

if __name__ == "__main__":
    # CLI interface
    import sys
    
    rag = GoogleCloudRAG()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "deploy":
            result = rag.deploy()
            print(json.dumps(result, indent=2))
            
        elif command == "test":
            results = rag.run_tests()
            for test, result in results.items():
                status = "✅" if result["passed"] else "❌"
                print(f"{status} {test}: {result['message']}")
                
        elif command == "status":
            status = rag.get_status()
            print(json.dumps(status, indent=2))
            
        elif command == "query":
            if len(sys.argv) > 2:
                query_text = " ".join(sys.argv[2:])
                result = rag.query(query_text)
                print(f"\nQuery: {result['query']}")
                print(f"Answer: {result['answer'][:500]}...")
                print(f"Sources: {result['num_sources']}")
                print(f"Time: {result['query_time_ms']:.2f}ms")
            else:
                print("Usage: python cloud_shell_rag.py query <your question>")
        else:
            print("Commands: deploy, test, status, query")
    else:
        print("Google Cloud RAG ready. Commands: deploy, test, status, query")