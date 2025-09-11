#!/usr/bin/env python3
"""
Enhanced Vertex AI RAG Engine Implementation
Uses the latest stable RAG API with both upload_file and import_files methods
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Google Cloud imports - try stable API first, fallback to preview
try:
    import vertexai
    from vertexai import rag  # Stable API
    USING_STABLE_API = True
    logger = logging.getLogger(__name__)
    logger.info("Using stable Vertex AI RAG API")
except ImportError:
    try:
        import vertexai
        from vertexai.preview import rag  # Preview API fallback
        USING_STABLE_API = False
        logger = logging.getLogger(__name__)
        logger.info("Using preview Vertex AI RAG API")
    except ImportError as e:
        raise ImportError(f"Cannot import Vertex AI RAG: {e}")

from vertexai.generative_models import GenerativeModel
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRAGEngine:
    """Enhanced RAG Engine using latest Vertex AI API"""
    
    def __init__(self):
        """Initialize RAG Engine with auto-detection of API version"""
        load_dotenv()
        
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-east4")
        self.corpus_name = os.getenv("RAG_CORPUS_NAME", "enhanced_manufacturing_docs")
        self.bucket_name = os.getenv("GCS_BUCKET", f"{self.project_id}-rag-enhanced")
        
        # Validate region for RAG Engine
        supported_regions = ["us-central1", "us-east4", "europe-west3", "europe-west4"]
        if self.location not in supported_regions:
            logger.warning(f"Region {self.location} not optimal for RAG Engine, switching to us-east4")
            self.location = "us-east4"
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        logger.info(f"✓ Vertex AI initialized: {self.project_id} in {self.location}")
        
        self.corpus = None
        self.storage_client = storage.Client()
        
        # Generation model
        self.model = GenerativeModel("gemini-1.5-flash")
    
    def create_corpus(self, display_name: str = None, description: str = None):
        """Create a new RAG corpus"""
        try:
            display_name = display_name or self.corpus_name
            description = description or f"Enhanced manufacturing documentation corpus"
            
            logger.info(f"Creating RAG corpus: {display_name}")
            
            if USING_STABLE_API:
                # Use stable API method
                self.corpus = rag.create_corpus(
                    display_name=display_name,
                    description=description
                )
            else:
                # Use preview API method (fallback)
                self.corpus = rag.create_corpus(
                    display_name=display_name,
                    description=description
                )
            
            logger.info(f"✅ Corpus created: {self.corpus.name}")
            return self.corpus
            
        except Exception as e:
            logger.error(f"Error creating corpus: {e}")
            raise
    
    def get_or_create_corpus(self):
        """Get existing corpus or create new one"""
        try:
            # List existing corpora
            corpora = rag.list_corpora()
            
            # Find corpus by display name
            for corpus in corpora:
                if hasattr(corpus, 'display_name') and self.corpus_name in corpus.display_name:
                    self.corpus = corpus
                    logger.info(f"✅ Found existing corpus: {corpus.name}")
                    return self.corpus
            
            # Create new corpus if not found
            logger.info("No existing corpus found, creating new one...")
            return self.create_corpus()
            
        except Exception as e:
            logger.error(f"Error getting/creating corpus: {e}")
            raise
    
    def upload_file(self, file_path: str, display_name: str = None, description: str = None):
        """Upload a single file using the new upload_file API"""
        if not self.corpus:
            self.get_or_create_corpus()
        
        try:
            file_path = Path(file_path)
            display_name = display_name or file_path.name
            description = description or f"Document: {file_path.name}"
            
            logger.info(f"Uploading file: {file_path.name}")
            
            if USING_STABLE_API:
                # Use new stable API
                rag_file = rag.upload_file(
                    corpus_name=self.corpus.name,
                    path=str(file_path),
                    display_name=display_name,
                    description=description
                )
            else:
                # Fallback to import_files for single file
                rag_file = rag.import_files(
                    corpus=self.corpus.name,
                    source=[str(file_path)]
                )
            
            logger.info(f"✅ File uploaded: {display_name}")
            return rag_file
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return None
    
    def upload_multiple_files(self, file_paths: List[str], descriptions: Dict[str, str] = None):
        """Upload multiple files efficiently"""
        descriptions = descriptions or {}
        results = []
        
        logger.info(f"Uploading {len(file_paths)} files...")
        
        for file_path in file_paths:
            file_name = Path(file_path).name
            description = descriptions.get(file_name, f"Document: {file_name}")
            
            result = self.upload_file(file_path, file_name, description)
            results.append(result)
        
        successful = sum(1 for r in results if r is not None)
        logger.info(f"✅ Uploaded {successful}/{len(file_paths)} files successfully")
        
        return results
    
    def query_rag(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the RAG corpus and generate response"""
        if not self.corpus:
            raise ValueError("No corpus available. Create or load a corpus first.")
        
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Querying: {query}")
            
            # Retrieve relevant contexts
            retrieval_start = time.time()
            response = rag.retrieve(
                corpus=self.corpus.name,
                query=query,
                top_k=top_k
            )
            retrieval_time = (time.time() - retrieval_start) * 1000
            
            # Generate answer using the contexts
            generation_start = time.time()
            contexts = response.contexts if hasattr(response, 'contexts') else []
            
            if contexts:
                # Prepare context for generation
                context_text = "\n\n".join([ctx.text for ctx in contexts[:3]])
                prompt = f"""Based on the following context, answer this question: {query}

Context:
{context_text}

Answer:"""
                
                answer_response = self.model.generate_content(prompt)
                answer = answer_response.text
            else:
                answer = "No relevant information found in the corpus."
            
            generation_time = (time.time() - generation_start) * 1000
            total_time = (time.time() - start_time) * 1000
            
            # Format response
            result = {
                "query": query,
                "answer": answer,
                "contexts": [
                    {
                        "text": ctx.text[:500] + "..." if len(ctx.text) > 500 else ctx.text,
                        "score": getattr(ctx, 'score', 0.0),
                        "source": getattr(ctx, 'source', 'unknown')
                    } for ctx in contexts
                ],
                "num_contexts": len(contexts),
                "confidence": getattr(response, 'confidence', 0.0),
                "timings": {
                    "retrieval_ms": round(retrieval_time, 2),
                    "generation_ms": round(generation_time, 2),
                    "total_ms": round(total_time, 2)
                },
                "model": "gemini-1.5-flash",
                "corpus": self.corpus.name,
                "api_version": "stable" if USING_STABLE_API else "preview"
            }
            
            logger.info(f"✅ Query completed in {total_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
            return {
                "query": query,
                "error": str(e),
                "success": False
            }
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List all files in the corpus"""
        if not self.corpus:
            raise ValueError("No corpus available")
        
        try:
            files = rag.list_files(corpus=self.corpus.name)
            return [{
                "name": f.name,
                "display_name": getattr(f, 'display_name', 'Unknown'),
                "description": getattr(f, 'description', ''),
                "size_bytes": getattr(f, 'size_bytes', 0),
                "create_time": getattr(f, 'create_time', None)
            } for f in files]
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_corpus_status(self) -> Dict[str, Any]:
        """Get detailed corpus status"""
        if not self.corpus:
            return {"status": "no_corpus", "message": "No corpus loaded"}
        
        try:
            files = self.list_files()
            
            return {
                "status": "active",
                "corpus_name": self.corpus.name,
                "display_name": getattr(self.corpus, 'display_name', 'Unknown'),
                "file_count": len(files),
                "total_size_bytes": sum(f.get('size_bytes', 0) for f in files),
                "api_version": "stable" if USING_STABLE_API else "preview",
                "location": self.location,
                "files": files[:5]  # Show first 5 files
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "corpus_name": self.corpus.name if self.corpus else None
            }

def main():
    """Main function for command-line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rag_engine_enhanced.py <command> [args]")
        print("Commands: create, upload <file>, query <question>, status, list")
        return
    
    rag_engine = EnhancedRAGEngine()
    command = sys.argv[1].lower()
    
    if command == "create":
        rag_engine.get_or_create_corpus()
        print("✅ Corpus created/loaded successfully")
    
    elif command == "upload" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        result = rag_engine.upload_file(file_path)
        if result:
            print(f"✅ File uploaded: {file_path}")
        else:
            print(f"❌ Failed to upload: {file_path}")
    
    elif command == "query" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        result = rag_engine.query_rag(query)
        
        if "error" in result:
            print(f"❌ Query failed: {result['error']}")
        else:
            print(f"Query: {result['query']}")
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['num_contexts']}")
            print(f"Time: {result['timings']['total_ms']}ms")
    
    elif command == "status":
        status = rag_engine.get_corpus_status()
        print(json.dumps(status, indent=2, default=str))
    
    elif command == "list":
        files = rag_engine.list_files()
        print(f"Files in corpus ({len(files)} total):")
        for f in files:
            print(f"  • {f['display_name']} ({f['size_bytes']} bytes)")
    
    else:
        print("Unknown command or missing arguments")

if __name__ == "__main__":
    main()