"""
Vertex AI RAG Engine Implementation
Complete implementation using Google's managed RAG service
"""

import os
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm

# Google Cloud imports
import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel
from google.cloud import storage
import logging

# Optional import for PDF support
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PyPDF2 not installed - PDF parsing disabled")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngineImplementation:
    """Production-ready RAG Engine implementation using Vertex AI"""
    
    def __init__(self):
        """Initialize RAG Engine with configuration"""
        load_dotenv()
        
        # Configuration
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.bucket_name = os.getenv("GCS_BUCKET", f"{self.project_id}-rag-documents")
        
        # Validate and fix region for Vertex AI
        self.location = self._validate_vertex_region(self.location)
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Generation model for answer synthesis
        self.generation_model_name = os.getenv("VERTEX_GENERATION_MODEL", "gemini-2.5-flash")
        self.generation_model = GenerativeModel(self.generation_model_name)
        
        # Storage client for document management
        self.storage_client = storage.Client(project=self.project_id)
        
        # RAG corpus (will be created/loaded)
        self.corpus = None
        self.corpus_name = os.getenv("RAG_CORPUS_NAME", "manufacturing_docs")
        
        logger.info(f"✅ RAG Engine initialized for project: {self.project_id}")
    
    def _validate_vertex_region(self, region: str) -> str:
        """Validate and correct region for Vertex AI compatibility"""
        
        # Supported Vertex AI regions (as of 2024)
        vertex_regions = {
            'us-central1', 'us-east1', 'us-east4', 'us-east5', 'us-east7', 
            'us-south1', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
            'northamerica-northeast1', 'northamerica-northeast2',
            'europe-central2', 'europe-north1', 'europe-southwest1',
            'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4',
            'europe-west6', 'europe-west8', 'europe-west9', 'europe-west12',
            'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2',
            'asia-northeast3', 'asia-south1', 'asia-south2', 'asia-southeast1',
            'asia-southeast2', 'australia-southeast1', 'australia-southeast2',
            'me-central1', 'me-central2', 'me-west1', 
            'africa-south1', 'southamerica-east1', 'southamerica-west1'
        }
        
        if region in vertex_regions:
            logger.info(f"✓ Using Vertex AI region: {region}")
            return region
        else:
            # Auto-correct to nearest supported region
            region_mappings = {
                'us-central': 'us-central1',
                'us-east': 'us-east1', 
                'us-west': 'us-west1',
                'europe-west': 'europe-west1',
                'asia-east': 'asia-east1',
                'asia-southeast': 'asia-southeast1'
            }
            
            # Try partial matches
            for partial, full in region_mappings.items():
                if region.startswith(partial):
                    logger.warning(f"⚠️  Region '{region}' not supported by Vertex AI")
                    logger.info(f"✓ Auto-correcting to: {full}")
                    return full
            
            # Default fallback
            default_region = 'us-central1'
            logger.warning(f"⚠️  Region '{region}' not supported by Vertex AI")
            logger.info(f"✓ Using default region: {default_region}")
            return default_region
    
    def create_or_get_corpus(self, 
                            display_name: str = None,
                            description: str = None) -> rag.RagCorpus:
        """Create a new RAG corpus or get existing one"""
        
        display_name = display_name or self.corpus_name
        description = description or "Manufacturing documentation RAG corpus"
        
        try:
            # Try to get existing corpus
            corpora = rag.list_corpora()
            for corpus in corpora:
                if corpus.display_name == display_name:
                    logger.info(f"✓ Found existing corpus: {corpus.name}")
                    self.corpus = corpus
                    return corpus
            
            # Create new corpus if not found
            logger.info(f"Creating new RAG corpus: {display_name}")
            
            # Create corpus with simplified API (vector DB is managed automatically)
            # The latest API version handles vector database configuration internally
            self.corpus = rag.create_corpus(
                display_name=display_name,
                description=description
            )
            
            logger.info(f"✅ Created corpus: {self.corpus.name}")
            return self.corpus
            
        except Exception as e:
            logger.error(f"Error creating/getting corpus: {str(e)}")
            raise
    
    def create_gcs_bucket(self) -> str:
        """Create GCS bucket for document storage if it doesn't exist"""
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self.bucket_name,
                    location=self.location
                )
                logger.info(f"✅ Created bucket: {self.bucket_name}")
            else:
                logger.info(f"✓ Bucket exists: {self.bucket_name}")
            
            return f"gs://{self.bucket_name}"
        
        except Exception as e:
            logger.error(f"Error creating bucket: {str(e)}")
            raise
    
    def upload_documents_to_gcs(self, 
                               documents: List[Dict[str, Any]],
                               folder: str = "documents") -> List[str]:
        """Upload documents to Google Cloud Storage"""
        
        bucket = self.storage_client.bucket(self.bucket_name)
        uploaded_files = []
        
        for doc in tqdm(documents, desc="Uploading to GCS"):
            # Create filename
            filename = f"{folder}/{doc['document_id']}.txt"
            blob = bucket.blob(filename)
            
            # Upload content
            content = f"Title: {doc['title']}\n\n{doc['content']}"
            blob.upload_from_string(content)
            
            # Store metadata
            blob.metadata = {
                "document_type": doc.get("document_type", "unknown"),
                "facility": doc.get("facility", "unknown"),
                "created_date": doc.get("created_date", datetime.now().isoformat())
            }
            blob.patch()
            
            uploaded_files.append(f"gs://{self.bucket_name}/{filename}")
        
        logger.info(f"✅ Uploaded {len(uploaded_files)} documents to GCS")
        return uploaded_files
    
    def import_documents_to_corpus(self,
                                  source_uri: str = None,
                                  file_paths: List[str] = None,
                                  chunk_size: int = 512,
                                  chunk_overlap: int = 100,
                                  parse_mode: str = "default") -> Dict[str, Any]:
        """Import documents into RAG corpus with advanced parsing"""
        
        if not self.corpus:
            self.create_or_get_corpus()
        
        try:
            # Create import configuration with simplified API
            # The latest version uses simpler configuration
            import_config = {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            }
            
            if source_uri:
                # Import from GCS bucket/folder
                logger.info(f"Importing documents from: {source_uri}")
                response = rag.import_files(
                    corpus=self.corpus.name,
                    source=[source_uri],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            elif file_paths:
                # Import specific files
                logger.info(f"Importing {len(file_paths)} files")
                response = rag.import_files(
                    corpus=self.corpus.name,
                    source=file_paths,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            else:
                raise ValueError("Either source_uri or file_paths must be provided")
            
            # Wait for import to complete
            logger.info("⏳ Waiting for import to complete...")
            while not response.done():
                time.sleep(5)
                logger.info("   Still importing...")
            
            result = response.result()
            logger.info(f"✅ Import completed: {result}")
            
            return {
                "status": "success",
                "imported_files": result.imported_rag_files_count if hasattr(result, 'imported_rag_files_count') else "unknown",
                "corpus": self.corpus.name
            }
            
        except Exception as e:
            logger.error(f"Error importing documents: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def retrieve_context(self,
                        query: str,
                        similarity_top_k: int = 10,
                        vector_distance_threshold: float = 0.3,
                        filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant context from corpus"""
        
        if not self.corpus:
            raise ValueError("No corpus available. Create or load a corpus first.")
        
        try:
            # Retrieve contexts using simplified API
            response = rag.retrieve(
                corpus=self.corpus.name,
                query=query,
                similarity_top_k=similarity_top_k,
                distance_threshold=vector_distance_threshold
            )
            
            # Format results
            contexts = []
            for context in response.contexts:
                contexts.append({
                    "text": context.text,
                    "score": context.score,
                    "source": context.source_uri if hasattr(context, 'source_uri') else "unknown",
                    "metadata": context.metadata if hasattr(context, 'metadata') else {}
                })
            
            logger.info(f"✅ Retrieved {len(contexts)} contexts")
            return contexts
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []
    
    def generate_answer(self,
                       query: str,
                       contexts: List[Dict[str, Any]] = None,
                       use_corpus: bool = True,
                       temperature: float = 0.1) -> Dict[str, Any]:
        """Generate answer using retrieved context and LLM"""
        
        try:
            if use_corpus and self.corpus:
                # Use RAG Engine's built-in generation with simplified API
                response = rag.generate_answer(
                    corpus=self.corpus.name,
                    query=query,
                    temperature=temperature
                )
                
                return {
                    "answer": response.answer.text,
                    "confidence": response.answer.confidence if hasattr(response.answer, 'confidence') else None,
                    "sources": [ctx.source_uri for ctx in response.contexts],
                    "model": self.generation_model_name
                }
            
            elif contexts:
                # Use provided contexts with Gemini
                context_text = "\n\n".join([ctx["text"] for ctx in contexts[:5]])
                
                prompt = f"""Based on the following context, provide a comprehensive answer to the question.
                
Context:
{context_text}

Question: {query}

Provide a clear, accurate answer based only on the given context. If the context doesn't contain enough information, say so.

Answer:"""
                
                response = self.generation_model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": 1024,
                    }
                )
                
                return {
                    "answer": response.text,
                    "confidence": None,
                    "sources": [ctx.get("source", "unknown") for ctx in contexts[:5]],
                    "model": self.generation_model_name
                }
            
            else:
                return {
                    "answer": "No context available to generate answer.",
                    "confidence": 0,
                    "sources": [],
                    "model": self.generation_model_name
                }
                
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "confidence": 0,
                "sources": [],
                "model": self.generation_model_name
            }
    
    def query(self,
             query_text: str,
             top_k: int = 10,
             filter_metadata: Dict[str, Any] = None,
             generate: bool = True) -> Dict[str, Any]:
        """Complete RAG query pipeline"""
        
        start_time = time.time()
        
        # Retrieve relevant contexts
        contexts = self.retrieve_context(
            query=query_text,
            similarity_top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        retrieval_time = time.time() - start_time
        
        # Generate answer if requested
        if generate:
            answer_result = self.generate_answer(
                query=query_text,
                contexts=contexts,
                use_corpus=True
            )
            generation_time = time.time() - start_time - retrieval_time
        else:
            answer_result = {"answer": None}
            generation_time = 0
        
        total_time = time.time() - start_time
        
        return {
            "query": query_text,
            "answer": answer_result.get("answer"),
            "contexts": contexts,
            "num_contexts": len(contexts),
            "confidence": answer_result.get("confidence"),
            "sources": answer_result.get("sources", []),
            "timings": {
                "retrieval_ms": retrieval_time * 1000,
                "generation_ms": generation_time * 1000,
                "total_ms": total_time * 1000
            },
            "model": self.generation_model_name,
            "corpus": self.corpus.name if self.corpus else None
        }
    
    def list_corpus_files(self) -> List[Dict[str, Any]]:
        """List all files in the corpus"""
        
        if not self.corpus:
            raise ValueError("No corpus available.")
        
        try:
            files = rag.list_files(corpus=self.corpus.name)
            
            file_list = []
            for file in files:
                file_list.append({
                    "name": file.name,
                    "display_name": file.display_name if hasattr(file, 'display_name') else None,
                    "size_bytes": file.size_bytes if hasattr(file, 'size_bytes') else None,
                    "create_time": file.create_time if hasattr(file, 'create_time') else None,
                    "update_time": file.update_time if hasattr(file, 'update_time') else None
                })
            
            logger.info(f"✅ Found {len(file_list)} files in corpus")
            return file_list
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def delete_corpus_file(self, file_name: str) -> bool:
        """Delete a file from the corpus"""
        
        try:
            rag.delete_file(file=file_name)
            logger.info(f"✅ Deleted file: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
    
    def update_corpus_file(self, 
                          file_name: str,
                          new_content: str) -> bool:
        """Update a file in the corpus"""
        
        try:
            # RAG Engine requires delete and re-import for updates
            # First delete the old file
            self.delete_corpus_file(file_name)
            
            # Upload new content to GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"updates/{file_name}")
            blob.upload_from_string(new_content)
            
            # Re-import the file
            self.import_documents_to_corpus(
                file_paths=[f"gs://{self.bucket_name}/updates/{file_name}"]
            )
            
            logger.info(f"✅ Updated file: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating file: {str(e)}")
            return False
    
    def get_corpus_statistics(self) -> Dict[str, Any]:
        """Get statistics about the corpus"""
        
        if not self.corpus:
            return {"status": "No corpus available"}
        
        try:
            files = self.list_corpus_files()
            
            total_size = sum(f.get("size_bytes", 0) for f in files)
            
            return {
                "corpus_name": self.corpus.name,
                "display_name": self.corpus.display_name,
                "description": self.corpus.description,
                "total_files": len(files),
                "total_size_mb": total_size / (1024 * 1024),
                "created_time": self.corpus.create_time if hasattr(self.corpus, 'create_time') else None,
                "updated_time": self.corpus.update_time if hasattr(self.corpus, 'update_time') else None,
                "vector_db": "RagManagedDb (Spanner)",
                "embedding_model": "gemini-embedding-001"
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def delete_corpus(self) -> bool:
        """Delete the entire corpus"""
        
        if not self.corpus:
            logger.warning("No corpus to delete")
            return False
        
        try:
            rag.delete_corpus(corpus=self.corpus.name)
            logger.info(f"✅ Deleted corpus: {self.corpus.name}")
            self.corpus = None
            return True
            
        except Exception as e:
            logger.error(f"Error deleting corpus: {str(e)}")
            return False
    
    def _build_metadata_filter(self, filter_dict: Dict[str, Any]) -> str:
        """Build metadata filter string for RAG queries"""
        
        # Convert dict to filter string
        # Example: {"facility": "FAB-1"} -> "facility = 'FAB-1'"
        filters = []
        for key, value in filter_dict.items():
            if isinstance(value, str):
                filters.append(f"{key} = '{value}'")
            else:
                filters.append(f"{key} = {value}")
        
        return " AND ".join(filters)
    
    def generate_sample_documents(self, num_docs: int = 10) -> List[Dict[str, Any]]:
        """Generate sample manufacturing documents"""
        
        templates = [
            {
                "type": "maintenance",
                "title": "Equipment Maintenance Manual",
                "content": """Daily Maintenance Tasks:
1. Check vacuum levels - Target: < 1e-6 Torr
2. Verify temperature stability - Range: 23°C ± 0.5°C
3. Monitor particle counts - Threshold: < 10 particles/cf
4. Inspect safety interlocks - All systems operational

Weekly Maintenance:
- Clean optical components with approved solvents
- Calibrate measurement systems
- Replace consumable filters
- Document all maintenance activities"""
            },
            {
                "type": "quality",
                "title": "Quality Control Report",
                "content": """Product Specifications:
- Wafer diameter: 300mm ± 0.5mm
- Thickness: 775μm ± 25μm
- Resistivity: 10-20 Ω·cm
- Surface roughness: < 0.5nm Ra

Inspection Results:
- Visual inspection: PASS
- Dimensional check: PASS
- Electrical test: PASS
- Surface analysis: PASS"""
            },
            {
                "type": "process",
                "title": "Process Specification",
                "content": """Process Parameters:
- Temperature: 850°C ± 5°C
- Pressure: 10 Torr ± 0.5 Torr
- Gas flow rate: 100 sccm ± 2 sccm
- Process time: 120 seconds ± 5 seconds

Critical Control Points:
1. Pre-process particle count < 5
2. Temperature uniformity < 2°C
3. Gas purity > 99.999%
4. Chamber base pressure < 1e-7 Torr"""
            }
        ]
        
        documents = []
        for i in range(num_docs):
            template = templates[i % len(templates)]
            documents.append({
                "document_id": f"doc_{i+1:04d}",
                "title": f"{template['title']} - {i+1:04d}",
                "content": template["content"],
                "document_type": template["type"],
                "facility": f"FAB-{(i % 3) + 1}",
                "created_date": datetime.now().isoformat()
            })
        
        return documents
    
    def deploy(self) -> Dict[str, Any]:
        """Complete deployment of RAG Engine"""
        
        logger.info("🚀 Starting RAG Engine deployment...\n")
        
        try:
            # Step 1: Create corpus
            self.create_or_get_corpus()
            
            # Step 2: Create GCS bucket
            gcs_uri = self.create_gcs_bucket()
            
            # Step 3: Generate and upload sample documents
            documents = self.generate_sample_documents()
            file_paths = self.upload_documents_to_gcs(documents)
            
            # Step 4: Import to corpus
            import_result = self.import_documents_to_corpus(
                source_uri=f"{gcs_uri}/documents/",
                chunk_size=512,
                chunk_overlap=100
            )
            
            # Step 5: Test query
            test_result = self.query("What are the maintenance procedures?")
            
            logger.info("\n✅ RAG Engine deployed successfully!")
            
            return {
                "success": True,
                "corpus": self.corpus.name,
                "gcs_bucket": gcs_uri,
                "documents_uploaded": len(documents),
                "import_status": import_result,
                "test_query": {
                    "answer": test_result["answer"][:200] + "...",
                    "num_contexts": test_result["num_contexts"],
                    "time_ms": test_result["timings"]["total_ms"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {str(e)}")
            return {"success": False, "error": str(e)}


# CLI Interface
if __name__ == "__main__":
    import sys
    
    rag_engine = RAGEngineImplementation()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "deploy":
            result = rag_engine.deploy()
            print(json.dumps(result, indent=2))
            
        elif command == "query":
            if len(sys.argv) > 2:
                query_text = " ".join(sys.argv[2:])
                # Try to get existing corpus first
                try:
                    if not rag_engine.corpus:
                        logger.info("No corpus loaded, attempting to find existing corpus...")
                        rag_engine.create_or_get_corpus()
                    result = rag_engine.query(query_text)
                    print(f"\nQuery: {result['query']}")
                    print(f"Answer: {result['answer']}")
                    print(f"Contexts: {result['num_contexts']}")
                    print(f"Time: {result['timings']['total_ms']:.2f}ms")
                except ValueError as e:
                    print(f"Error: {str(e)}")
                    print("Please run 'deploy' first to create and populate the corpus")
                except Exception as e:
                    print(f"Query failed: {str(e)}")
            else:
                print("Usage: python rag_engine_implementation.py query <your question>")
                
        elif command == "status":
            try:
                # Try to load existing corpus if not already loaded
                if not rag_engine.corpus:
                    logger.info("No corpus loaded, attempting to find existing corpus...")
                    rag_engine.create_or_get_corpus()
                stats = rag_engine.get_corpus_statistics()
                print(json.dumps(stats, indent=2))
            except Exception as e:
                print(json.dumps({"status": "error", "message": str(e)}, indent=2))
            
        elif command == "list":
            try:
                # Try to load existing corpus if not already loaded
                if not rag_engine.corpus:
                    logger.info("No corpus loaded, attempting to find existing corpus...")
                    rag_engine.create_or_get_corpus()
                files = rag_engine.list_corpus_files()
                if files:
                    for file in files:
                        print(f"- {file['display_name']} ({file.get('size_bytes', 0) / 1024:.1f}KB)")
                else:
                    print("No files in corpus")
            except Exception as e:
                print(f"Error listing files: {str(e)}")
                print("Please run 'deploy' first to create and populate the corpus")
                
        else:
            print("Commands: deploy, query, status, list")
    else:
        print("RAG Engine ready. Commands: deploy, query, status, list")