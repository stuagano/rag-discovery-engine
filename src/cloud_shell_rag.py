"""
Cloud Shell RAG Implementation
One-command deployment for BigQuery RAG with multiple embedding options
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

# Optional embedding models
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Text processing
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Fallback simple text splitter
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size=1000, chunk_overlap=200, **kwargs):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
        
        def split_text(self, text: str) -> List[str]:
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunks.append(text[start:end])
                start = end - self.chunk_overlap if end < len(text) else end
            return chunks

class EmbeddingModelManager:
    """Manage different embedding models"""
    
    def __init__(self, model_type: str, model_name: str, project_id: str = None):
        self.model_type = model_type
        self.model_name = model_name
        self.project_id = project_id
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model based on type"""
        
        if self.model_type == "vertex":
            if self.project_id:
                vertexai.init(project=self.project_id, location=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"))
            self.model = TextEmbeddingModel.from_pretrained(self.model_name)
            self.embedding_dim = 768  # Gecko embedding dimension
            
        elif self.model_type == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI not available. Install with: pip install openai")
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.embedding_dim = 1536 if "3-large" in self.model_name else 1536 if "3-small" in self.model_name else 1536
            
        elif self.model_type == "sentence_transformers":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("Sentence Transformers not available. Install with: pip install sentence-transformers")
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            
        elif self.model_type == "huggingface":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("Sentence Transformers required for HuggingFace models")
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            
        else:
            raise ValueError(f"Unsupported embedding model type: {self.model_type}")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        
        if self.model_type == "vertex":
            embeddings = self.model.get_embeddings(texts)
            return [emb.values for emb in embeddings]
            
        elif self.model_type == "openai":
            response = openai.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [emb.embedding for emb in response.data]
            
        elif self.model_type in ["sentence_transformers", "huggingface"]:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

class CloudShellRAG:
    """Production-ready RAG system for Cloud Shell deployment"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1") 
        self.dataset_id = os.getenv("BIGQUERY_DATASET", "rag_poc")
        
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set in .env file")
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=self.project_id)
        
        # Initialize embedding model
        embedding_type = os.getenv("EMBEDDING_MODEL", "vertex")
        embedding_name = os.getenv("EMBEDDING_MODEL_NAME", "textembedding-gecko@003")
        
        print(f"🧠 Initializing {embedding_type} embedding model: {embedding_name}")
        self.embedding_manager = EmbeddingModelManager(
            model_type=embedding_type,
            model_name=embedding_name,
            project_id=self.project_id
        )
        
        # Text splitter
        chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len
        )
        
        # Performance settings
        self.batch_size = int(os.getenv("BATCH_SIZE", "100"))
        self.max_concurrent = int(os.getenv("MAX_CONCURRENT_EMBEDDINGS", "10"))
        
        print(f"✅ CloudShell RAG initialized for project: {self.project_id}")
    
    def setup_bigquery_resources(self) -> Dict[str, Any]:
        """Create BigQuery dataset and tables"""
        
        print("🏗️  Setting up BigQuery resources...")
        
        # Create dataset
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = self.region
        dataset.description = "RAG POC for manufacturing documents"
        
        try:
            dataset = self.bq_client.create_dataset(dataset, timeout=30)
            print(f"   Created dataset: {dataset_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   Dataset exists: {dataset_id}")
            else:
                raise e
        
        # Create embeddings table
        table_id = f"{dataset_id}.document_embeddings"
        schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_text", "STRING"),
            bigquery.SchemaField("chunk_index", "INTEGER"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("metadata", "JSON"),
            bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP()"),
        ]
        
        table = bigquery.Table(table_id, schema=schema)
        
        # Add partitioning and clustering for performance
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="created_at"
        )
        table.clustering_fields = ["document_id", "chunk_index"]
        
        try:
            table = self.bq_client.create_table(table)
            print(f"   Created table: {table_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   Table exists: {table_id}")
            else:
                raise e
        
        return {"dataset": dataset_id, "table": table_id}
    
    def generate_sample_documents(self, num_docs: int = None) -> List[Dict[str, Any]]:
        """Generate sample manufacturing documents"""
        
        if num_docs is None:
            num_docs = int(os.getenv("NUM_TEST_DOCS", "10"))
        
        print(f"📄 Generating {num_docs} sample manufacturing documents...")
        
        # Manufacturing document templates
        templates = [
            {
                "type": "maintenance_manual",
                "title": "Ion Implanter Maintenance Manual",
                "content": """
                Maintenance Schedule for Ion Implanter Model X200:
                
                Daily Checks:
                - Verify chamber vacuum levels (< 1e-6 Torr)
                - Check beam current stability (±2%)
                - Monitor particle contamination levels
                - Inspect mechanical components for wear
                
                Weekly Maintenance:
                - Clean ion source components
                - Calibrate beam alignment system
                - Replace consumable parts as needed
                - Verify safety interlocks
                
                Monthly Procedures:
                - Complete system calibration
                - Replace filters and seals
                - Perform electrical safety checks
                - Update maintenance logs
                
                Critical Safety Points:
                - Always power down before maintenance
                - Use proper lockout/tagout procedures
                - Wear appropriate PPE
                - Follow contamination control protocols
                """
            },
            {
                "type": "quality_report", 
                "title": "Wafer Quality Inspection Report",
                "content": """
                Quality Inspection Report - Lot WF2024001:
                
                Inspection Date: 2024-01-15
                Product: 300mm Silicon Wafers
                Inspector: J. Smith
                
                Measurements:
                - Thickness: 775.2 μm (Spec: 775 ± 25 μm) ✓ PASS
                - Resistivity: 15.3 Ω·cm (Spec: 10-20 Ω·cm) ✓ PASS  
                - Total Thickness Variation: 0.8 μm (Spec: < 2 μm) ✓ PASS
                - Particle Count: 3 (Spec: < 10) ✓ PASS
                
                Surface Analysis:
                - Surface roughness: 0.3 nm Ra (Spec: < 0.5 nm) ✓ PASS
                - No visible contamination detected
                - Edge exclusion zone clear
                
                Recommendation: Lot approved for production
                """
            },
            {
                "type": "process_spec",
                "title": "Photolithography Process Specification", 
                "content": """
                Process Specification: Advanced Photolithography
                
                Process Parameters:
                - Wavelength: 193 nm ArF
                - Exposure Dose: 25 mJ/cm²
                - Focus Setting: 0 nm ± 50 nm
                - Temperature: 23°C ± 0.1°C
                - Humidity: 45% ± 2% RH
                
                Critical Control Points:
                1. Resist coating uniformity: ±2%
                2. Bake temperature control: ±0.5°C
                3. Exposure dose control: ±1%
                4. Development time: 60s ± 2s
                
                Quality Checks:
                - CD uniformity across wafer
                - Overlay accuracy < 5 nm
                - Defect density < 0.1/cm²
                - Pattern fidelity verification
                
                Equipment: ASML NXT:2000i Scanner
                Recipe: ADV_PHOLITHO_v2.3
                """
            }
        ]
        
        documents = []
        for i in range(num_docs):
            template = templates[i % len(templates)]
            doc_id = f"doc_{i+1:04d}"
            
            # Add some variation
            doc_content = template["content"].replace("X200", f"X{200 + i}")
            doc_content = doc_content.replace("WF2024001", f"WF2024{i+1:03d}")
            
            documents.append({
                "document_id": doc_id,
                "title": f"{template['title']} #{i+1}",
                "content": doc_content,
                "document_type": template["type"],
                "facility": f"FAB-{(i % 3) + 1}",
                "equipment_type": ["ion_implanter", "inspection_tool", "lithography"][i % 3],
                "created_date": datetime.now().isoformat()
            })
        
        print(f"   Generated {len(documents)} documents")
        return documents
    
    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """Process documents into chunks with embeddings"""
        
        print(f"⚙️  Processing {len(documents)} documents into chunks...")
        
        processed_chunks = []
        
        for doc in tqdm(documents, desc="Processing documents"):
            # Split into chunks
            chunks = self.text_splitter.split_text(doc["content"])
            
            # Process chunks in batches for embedding
            chunk_texts = []
            chunk_data = []
            
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc['document_id']}_chunk_{i:04d}"
                
                chunk_info = {
                    "document_id": doc["document_id"],
                    "chunk_id": chunk_id,
                    "chunk_text": chunk_text,
                    "chunk_index": i,
                    "metadata": {
                        "title": doc["title"],
                        "document_type": doc["document_type"],
                        "facility": doc["facility"], 
                        "equipment_type": doc["equipment_type"],
                        "created_date": doc["created_date"],
                        "chunk_length": len(chunk_text),
                        "total_chunks": len(chunks)
                    }
                }
                
                chunk_texts.append(chunk_text)
                chunk_data.append(chunk_info)
                
                # Process in batches
                if len(chunk_texts) >= self.batch_size:
                    embeddings = self.embedding_manager.get_embeddings(chunk_texts)
                    
                    for chunk_info, embedding in zip(chunk_data, embeddings):
                        chunk_info["embedding"] = embedding
                        processed_chunks.append(chunk_info)
                    
                    chunk_texts = []
                    chunk_data = []
            
            # Process remaining chunks
            if chunk_texts:
                embeddings = self.embedding_manager.get_embeddings(chunk_texts)
                
                for chunk_info, embedding in zip(chunk_data, embeddings):
                    chunk_info["embedding"] = embedding
                    processed_chunks.append(chunk_info)
        
        print(f"   Processed {len(processed_chunks)} chunks with embeddings")
        return processed_chunks
    
    def upload_to_bigquery(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Upload processed chunks to BigQuery"""
        
        print(f"📤 Uploading {len(chunks)} chunks to BigQuery...")
        
        table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings"
        
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(chunks)
        
        # Configure load job
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("document_id", "STRING"),
                bigquery.SchemaField("chunk_id", "STRING"), 
                bigquery.SchemaField("chunk_text", "STRING"),
                bigquery.SchemaField("chunk_index", "INTEGER"),
                bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
                bigquery.SchemaField("metadata", "JSON"),
            ],
            write_disposition="WRITE_APPEND" if os.getenv("SKIP_EXISTING_DATA", "true").lower() == "true" else "WRITE_TRUNCATE",
        )
        
        # Upload to BigQuery
        job = self.bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Wait for job to complete
        
        print(f"   Successfully uploaded to {table_id}")
        
        return {
            "status": "success", 
            "chunks_uploaded": len(chunks),
            "table": table_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def query(self, query_text: str, k: int = 5) -> Dict[str, Any]:
        """Query the RAG system"""
        
        # Generate query embedding
        query_embedding = self.embedding_manager.get_embeddings([query_text])[0]
        
        # Build similarity search query
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
                -- Cosine similarity calculation
                (
                    (
                        SELECT SUM(a * b)
                        FROM UNNEST(de.embedding) a WITH OFFSET pos1,
                             UNNEST((SELECT query_vec FROM query_embedding)) b WITH OFFSET pos2  
                        WHERE pos1 = pos2
                    ) / (
                        SQRT((
                            SELECT SUM(a * a) 
                            FROM UNNEST(de.embedding) a
                        )) * SQRT((
                            SELECT SUM(b * b)
                            FROM UNNEST((SELECT query_vec FROM query_embedding)) b
                        ))
                    )
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
                "similarity_score": row.similarity_score,
                "metadata": json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata
            })
        
        # Generate answer (simple concatenation for now)
        context = "\n\n".join([r["chunk_text"] for r in formatted_results[:3]])
        answer = f"Based on the manufacturing documentation:\n\n{context}"
        
        return {
            "query": query_text,
            "answer": answer,
            "sources": formatted_results,
            "query_time_ms": query_time * 1000,
            "num_sources": len(formatted_results)
        }
    
    def deploy(self) -> Dict[str, Any]:
        """Complete deployment of RAG system"""
        
        print("🚀 Starting RAG system deployment...\n")
        
        try:
            # Step 1: Setup BigQuery resources
            bq_resources = self.setup_bigquery_resources()
            
            # Step 2: Generate sample documents
            documents = self.generate_sample_documents()
            
            # Step 3: Process documents
            chunks = self.process_documents(documents)
            
            # Step 4: Upload to BigQuery
            upload_result = self.upload_to_bigquery(chunks)
            
            print("\n✅ RAG system deployed successfully!")
            
            return {
                "success": True,
                "documents_processed": len(documents),
                "embeddings_generated": len(chunks),
                "bigquery_resources": bq_resources,
                "upload_result": upload_result,
                "endpoint": f"CloudShellRAG.query()",
                "embedding_model": f"{self.embedding_manager.model_type}:{self.embedding_manager.model_name}",
                "embedding_dimension": self.embedding_manager.embedding_dim
            }
            
        except Exception as e:
            print(f"❌ Deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_tests(self) -> Dict[str, Dict]:
        """Run validation tests"""
        
        print("🧪 Running system tests...\n")
        
        test_results = {}
        
        # Test 1: Basic query
        try:
            result = self.query("maintenance schedule for ion implanter")
            test_results["basic_query"] = {
                "passed": len(result["sources"]) > 0,
                "message": f"Retrieved {len(result['sources'])} results in {result['query_time_ms']:.2f}ms"
            }
        except Exception as e:
            test_results["basic_query"] = {
                "passed": False,
                "message": f"Query failed: {str(e)}"
            }
        
        # Test 2: BigQuery connectivity
        try:
            query = f"SELECT COUNT(*) as total FROM `{self.project_id}.{self.dataset_id}.document_embeddings`"
            result = list(self.bq_client.query(query).result())[0]
            test_results["bigquery_connectivity"] = {
                "passed": result.total > 0,
                "message": f"Found {result.total} chunks in BigQuery"
            }
        except Exception as e:
            test_results["bigquery_connectivity"] = {
                "passed": False,
                "message": f"BigQuery test failed: {str(e)}"
            }
        
        # Test 3: Embedding generation
        try:
            test_text = "Test embedding generation"
            embedding = self.embedding_manager.get_embeddings([test_text])[0]
            test_results["embedding_generation"] = {
                "passed": len(embedding) == self.embedding_manager.embedding_dim,
                "message": f"Generated {len(embedding)}-dim embedding"
            }
        except Exception as e:
            test_results["embedding_generation"] = {
                "passed": False,
                "message": f"Embedding test failed: {str(e)}"
            }
        
        return test_results
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        
        # Query statistics
        stats_query = f"""
        SELECT 
            COUNT(DISTINCT document_id) as total_documents,
            COUNT(*) as total_chunks,
            AVG(ARRAY_LENGTH(embedding)) as avg_embedding_dim,
            MIN(LENGTH(chunk_text)) as min_chunk_length,
            MAX(LENGTH(chunk_text)) as max_chunk_length,
            AVG(LENGTH(chunk_text)) as avg_chunk_length
        FROM `{self.project_id}.{self.dataset_id}.document_embeddings`
        """
        
        try:
            result = list(self.bq_client.query(stats_query).result())[0]
            
            return {
                "status": "healthy",
                "project_id": self.project_id,
                "dataset": self.dataset_id,
                "embedding_model": f"{self.embedding_manager.model_type}:{self.embedding_manager.model_name}",
                "embedding_dimension": self.embedding_manager.embedding_dim,
                "statistics": {
                    "total_documents": result.total_documents,
                    "total_chunks": result.total_chunks,
                    "avg_embedding_dim": result.avg_embedding_dim,
                    "avg_chunk_length": result.avg_chunk_length
                },
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }

if __name__ == "__main__":
    # Quick CLI interface
    import sys
    
    rag = CloudShellRAG()
    
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
                print(f"Query: {result['query']}")
                print(f"Answer: {result['answer'][:500]}...")
                print(f"Sources: {result['num_sources']}")
            else:
                print("Usage: python cloud_shell_rag.py query <your question>")
        else:
            print("Commands: deploy, test, status, query")
    else:
        print("RAG system ready. Use: deploy, test, status, or query")