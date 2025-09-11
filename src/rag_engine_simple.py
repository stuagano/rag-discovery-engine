"""
Simplified Vertex AI RAG Engine Implementation
Uses the basic RAG API without complex configurations
"""

import os
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import logging

# Google Cloud imports
import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRAGEngine:
    """Simplified RAG Engine using basic Vertex AI RAG API"""
    
    def __init__(self):
        """Initialize RAG Engine with minimal configuration"""
        load_dotenv()
        
        # Configuration
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.bucket_name = os.getenv("GCS_BUCKET", f"{self.project_id}-rag-docs")
        
        # Validate region
        self.location = self._validate_region(self.location)
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Generation model
        self.generation_model_name = os.getenv("VERTEX_GENERATION_MODEL", "gemini-2.5-flash")
        self.generation_model = GenerativeModel(self.generation_model_name)
        
        # Storage client
        self.storage_client = storage.Client(project=self.project_id)
        
        # RAG corpus (will be created/loaded)
        self.corpus = None
        self.corpus_name = os.getenv("RAG_CORPUS_NAME", "simple_rag_corpus")
        
        logger.info(f"✅ Simple RAG Engine initialized for project: {self.project_id}")
    
    def _validate_region(self, region: str) -> str:
        """Validate and correct region for Vertex AI"""
        valid_regions = {'us-central1', 'us-east1', 'us-east4', 'us-west1', 
                        'europe-west1', 'europe-west2', 'europe-west4',
                        'asia-east1', 'asia-northeast1', 'asia-southeast1'}
        
        if region in valid_regions:
            logger.info(f"✓ Using region: {region}")
            return region
        else:
            logger.warning(f"⚠️ Region '{region}' not supported, using us-central1")
            return 'us-central1'
    
    def create_corpus(self) -> Any:
        """Create or get a RAG corpus"""
        try:
            # Check for existing corpus
            corpora = rag.list_corpora()
            for corpus in corpora:
                if corpus.display_name == self.corpus_name:
                    logger.info(f"✓ Found existing corpus: {corpus.name}")
                    self.corpus = corpus
                    return corpus
            
            # Create new corpus with minimal configuration
            logger.info(f"Creating new corpus: {self.corpus_name}")
            self.corpus = rag.create_corpus(
                display_name=self.corpus_name,
                description="Simple RAG corpus for testing"
            )
            
            logger.info(f"✅ Created corpus: {self.corpus.name}")
            return self.corpus
            
        except Exception as e:
            logger.error(f"Error with corpus: {str(e)}")
            raise
    
    def upload_sample_data(self) -> List[str]:
        """Upload sample documents to GCS"""
        
        # Create bucket if needed
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self.bucket_name,
                    location=self.location
                )
                logger.info(f"✅ Created bucket: {self.bucket_name}")
        except Exception as e:
            logger.warning(f"Bucket creation issue: {str(e)}")
            bucket = self.storage_client.bucket(self.bucket_name)
        
        # Sample documents
        documents = [
            {
                "name": "maintenance_guide.txt",
                "content": """Equipment Maintenance Guide
                
Daily Tasks:
- Check system pressure: 10-15 PSI
- Monitor temperature: 20-25°C
- Inspect safety valves
- Record all readings

Weekly Tasks:
- Clean filters
- Test emergency systems
- Calibrate sensors
- Update maintenance log

Monthly Tasks:
- Full system inspection
- Replace worn parts
- Performance testing
- Generate reports"""
            },
            {
                "name": "quality_standards.txt",
                "content": """Quality Control Standards

Product Specifications:
- Dimensions: 100mm x 50mm x 25mm
- Weight: 250g ± 5g
- Material: Grade A Steel
- Finish: Polished

Testing Requirements:
- Visual inspection: 100% of products
- Dimensional check: Every 10th unit
- Stress test: Daily sample
- Documentation: All test results

Acceptance Criteria:
- Zero critical defects
- Minor defects < 1%
- All specs within tolerance
- Proper documentation"""
            },
            {
                "name": "safety_procedures.txt",
                "content": """Safety Procedures

Emergency Response:
1. Sound alarm immediately
2. Evacuate area if needed
3. Call emergency services
4. Report to supervisor

PPE Requirements:
- Safety glasses: Always required
- Hard hat: In production areas
- Steel-toe boots: Mandatory
- Gloves: When handling materials

Training:
- Initial safety training: 8 hours
- Annual refresher: 2 hours
- Specialized training as needed
- Documentation of all training"""
            }
        ]
        
        # Upload to GCS
        file_uris = []
        for doc in documents:
            blob = bucket.blob(f"documents/{doc['name']}")
            blob.upload_from_string(doc['content'])
            uri = f"gs://{self.bucket_name}/documents/{doc['name']}"
            file_uris.append(uri)
            logger.info(f"✓ Uploaded: {doc['name']}")
        
        return file_uris
    
    def import_documents(self, file_uris: List[str]) -> bool:
        """Import documents into RAG corpus"""
        
        if not self.corpus:
            raise ValueError("No corpus available. Create corpus first.")
        
        try:
            logger.info(f"Importing {len(file_uris)} documents...")
            
            # Simple import without complex configuration
            response = rag.import_files(
                corpus=self.corpus.name,
                source=file_uris,
                chunk_size=512,
                chunk_overlap=100
            )
            
            # Wait for completion
            logger.info("⏳ Waiting for import to complete...")
            while not response.done():
                time.sleep(5)
                logger.info("   Still importing...")
            
            result = response.result()
            logger.info(f"✅ Import completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            return False
    
    def query(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the RAG corpus"""
        
        if not self.corpus:
            raise ValueError("No corpus available. Create corpus first.")
        
        try:
            # Retrieve relevant contexts
            logger.info(f"🔍 Searching for: {query_text}")
            
            contexts = rag.retrieve(
                corpus=self.corpus.name,
                query=query_text,
                similarity_top_k=top_k
            )
            
            # Format contexts
            context_texts = []
            for ctx in contexts.contexts:
                context_texts.append(ctx.text)
            
            # Generate answer using contexts
            if context_texts:
                context_str = "\n\n".join(context_texts[:3])
                prompt = f"""Based on the following information, answer the question.

Context:
{context_str}

Question: {query_text}

Answer:"""
                
                response = self.generation_model.generate_content(prompt)
                answer = response.text
            else:
                answer = "No relevant information found."
            
            return {
                "query": query_text,
                "answer": answer,
                "num_contexts": len(context_texts),
                "contexts": context_texts[:3]
            }
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return {
                "query": query_text,
                "answer": f"Error: {str(e)}",
                "num_contexts": 0,
                "contexts": []
            }
    
    def deploy(self) -> Dict[str, Any]:
        """Complete deployment process"""
        
        logger.info("🚀 Starting Simple RAG Engine deployment...\n")
        
        try:
            # Step 1: Create corpus
            self.create_corpus()
            
            # Step 2: Upload sample data
            file_uris = self.upload_sample_data()
            
            # Step 3: Import to corpus
            success = self.import_documents(file_uris)
            
            if not success:
                raise Exception("Document import failed")
            
            # Step 4: Test query
            test_result = self.query("What are the maintenance procedures?")
            
            logger.info("\n✅ RAG Engine deployed successfully!")
            
            return {
                "success": True,
                "corpus": self.corpus.name if self.corpus else None,
                "documents_uploaded": len(file_uris),
                "test_query": {
                    "answer": test_result["answer"][:200] + "...",
                    "num_contexts": test_result["num_contexts"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def cleanup(self) -> bool:
        """Delete corpus and clean up resources"""
        
        if not self.corpus:
            logger.warning("No corpus to delete")
            return False
        
        try:
            rag.delete_corpus(corpus=self.corpus.name)
            logger.info(f"✅ Deleted corpus: {self.corpus.name}")
            self.corpus = None
            return True
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return False


# CLI Interface
if __name__ == "__main__":
    import sys
    
    engine = SimpleRAGEngine()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "deploy":
            result = engine.deploy()
            print(json.dumps(result, indent=2))
            
        elif command == "query":
            if len(sys.argv) > 2:
                query_text = " ".join(sys.argv[2:])
                result = engine.query(query_text)
                print(f"\nQuery: {result['query']}")
                print(f"Answer: {result['answer']}")
                print(f"Contexts: {result['num_contexts']}")
            else:
                print("Usage: python rag_engine_simple.py query <your question>")
                
        elif command == "cleanup":
            if engine.cleanup():
                print("✅ Cleanup successful")
            else:
                print("❌ Cleanup failed")
                
        else:
            print("Commands: deploy, query, cleanup")
    else:
        print("Simple RAG Engine ready. Commands: deploy, query, cleanup")