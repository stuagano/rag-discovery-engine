"""
Enhanced BigQuery RAG Implementation
Advanced features including hybrid search, caching, and analytics
"""

import os
import time
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Google Cloud imports
from google.cloud import bigquery
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel

# Document processing
import PyPDF2
import pdfplumber
from typing import Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextSplitter:
    """Advanced text splitter with multiple strategies"""
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 strategy: str = "recursive"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
    
    def split_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text with metadata about chunks"""
        
        if self.strategy == "recursive":
            return self._recursive_split(text)
        elif self.strategy == "sentence":
            return self._sentence_split(text)
        else:
            return self._simple_split(text)
    
    def _simple_split(self, text: str) -> List[Dict[str, Any]]:
        """Simple overlapping window split"""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            chunks.append({
                "text": chunk_text,
                "start_char": start,
                "end_char": end,
                "chunk_index": chunk_index,
                "chunk_length": len(chunk_text)
            })
            
            start = end - self.chunk_overlap if end < len(text) else end
            chunk_index += 1
        
        return chunks
    
    def _sentence_split(self, text: str) -> List[Dict[str, Any]]:
        """Split by sentences, respecting chunk size"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "chunk_length": len(chunk_text),
                    "sentence_count": len(current_chunk)
                })
                
                # Keep last sentence for overlap
                current_chunk = [current_chunk[-1]] if self.chunk_overlap > 0 else []
                current_size = len(current_chunk[0]) if current_chunk else 0
                chunk_index += 1
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "chunk_index": chunk_index,
                "chunk_length": len(chunk_text),
                "sentence_count": len(current_chunk)
            })
        
        return chunks
    
    def _recursive_split(self, text: str) -> List[Dict[str, Any]]:
        """Recursively split by paragraphs, then sentences, then characters"""
        
        # First try to split by paragraphs
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if para_size > self.chunk_size:
                # Paragraph too large, split by sentences
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "chunk_length": len(chunk_text),
                        "paragraph_count": len(current_chunk)
                    })
                    current_chunk = []
                    current_size = 0
                    chunk_index += 1
                
                # Split large paragraph
                para_chunks = self._sentence_split(para)
                chunks.extend(para_chunks)
                chunk_index += len(para_chunks)
                
            elif current_size + para_size > self.chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "chunk_length": len(chunk_text),
                    "paragraph_count": len(current_chunk)
                })
                current_chunk = [para]
                current_size = para_size
                chunk_index += 1
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "chunk_index": chunk_index,
                "chunk_length": len(chunk_text),
                "paragraph_count": len(current_chunk)
            })
        
        return chunks


class BigQueryRAGEnhanced:
    """Enhanced BigQuery RAG with advanced features"""
    
    def __init__(self):
        """Initialize enhanced RAG system"""
        load_dotenv()
        
        # Configuration
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.dataset_id = os.getenv("BIGQUERY_DATASET", "rag_enhanced")
        
        # Get project ID from gcloud if not in env
        if not self.project_id:
            import subprocess
            try:
                result = subprocess.run(['gcloud', 'config', 'get-value', 'project'],
                                      capture_output=True, text=True)
                self.project_id = result.stdout.strip()
            except:
                raise ValueError("GOOGLE_CLOUD_PROJECT must be set")
        
        logger.info(f"🔧 Initializing Enhanced BigQuery RAG for project: {self.project_id}")
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=self.project_id)
        self.storage_client = storage.Client(project=self.project_id)
        
        # Validate and fix region for Vertex AI
        self.region = self._validate_vertex_region(self.region)
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.region)
        
        # Embedding model
        self.embedding_model_name = os.getenv("VERTEX_EMBEDDING_MODEL", "gemini-embedding-001")
        self.embedding_model = TextEmbeddingModel.from_pretrained(self.embedding_model_name)
        self.embedding_dim = 768
        
        # Generation model
        self.generation_model_name = os.getenv("VERTEX_GENERATION_MODEL", "gemini-2.5-flash")
        self.generation_model = GenerativeModel(self.generation_model_name)
        
        # Text splitter with strategy
        chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        split_strategy = os.getenv("SPLIT_STRATEGY", "recursive")
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap, split_strategy)
        
        # Performance settings
        self.batch_size = int(os.getenv("BATCH_SIZE", "100"))
        self.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        self.cache_ttl_hours = int(os.getenv("CACHE_TTL_HOURS", "24"))
        
        # Search settings
        self.enable_hybrid_search = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
        self.enable_reranking = os.getenv("ENABLE_RERANKING", "true").lower() == "true"
        
        logger.info(f"✅ Enhanced BigQuery RAG initialized")
        logger.info(f"   • Embedding: {self.embedding_model_name}")
        logger.info(f"   • Generation: {self.generation_model_name}")
        logger.info(f"   • Hybrid Search: {self.enable_hybrid_search}")
        logger.info(f"   • Caching: {self.enable_caching}")
    
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
    
    def fix_table_schema(self) -> bool:
        """Fix existing table schema if it's missing required columns"""
        
        table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings"
        
        try:
            existing_table = self.bq_client.get_table(table_id)
            existing_fields = [field.name for field in existing_table.schema]
            
            # Check for missing critical columns
            required_fields = ['keywords', 'importance_score', 'summary', 'chunk_hash']
            missing_fields = [field for field in required_fields if field not in existing_fields]
            
            if missing_fields:
                logger.warning(f"🔧 Fixing table schema - missing columns: {missing_fields}")
                
                # Delete and recreate table with correct schema
                self.bq_client.delete_table(table_id)
                logger.info(f"   ✓ Deleted old table: {table_id}")
                return True
            else:
                logger.info(f"   ✓ Table schema is correct")
                return False
                
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(f"   ✓ Table doesn't exist yet - will be created")
                return False
            else:
                logger.error(f"   ❌ Error checking table: {str(e)}")
                raise e
    
    def setup_bigquery_resources(self) -> Dict[str, Any]:
        """Create enhanced BigQuery dataset and tables"""
        
        logger.info("🏗️  Setting up enhanced BigQuery resources...")
        
        # Create dataset
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = self.region
        dataset.description = "Enhanced RAG with BigQuery"
        
        try:
            dataset = self.bq_client.create_dataset(dataset, timeout=30)
            logger.info(f"   ✓ Created dataset: {dataset_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"   ✓ Dataset exists: {dataset_id}")
            else:
                raise e
        
        # Create main embeddings table with additional features
        embeddings_table_id = f"{dataset_id}.document_embeddings"
        embeddings_schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_text", "STRING"),
            bigquery.SchemaField("chunk_index", "INTEGER"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("embedding_model", "STRING"),
            bigquery.SchemaField("metadata", "JSON"),
            # Additional fields for enhanced features
            bigquery.SchemaField("chunk_hash", "STRING"),  # For deduplication
            bigquery.SchemaField("keywords", "STRING", mode="REPEATED"),  # For hybrid search
            bigquery.SchemaField("summary", "STRING"),  # Chunk summary
            bigquery.SchemaField("importance_score", "FLOAT64"),  # Chunk importance
            bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP()"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP()"),
        ]
        
        embeddings_table = bigquery.Table(embeddings_table_id, schema=embeddings_schema)
        
        # Advanced partitioning and clustering
        embeddings_table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="created_at"
        )
        embeddings_table.clustering_fields = ["document_id", "chunk_index", "importance_score"]
        
        try:
            embeddings_table = self.bq_client.create_table(embeddings_table)
            logger.info(f"   ✓ Created embeddings table: {embeddings_table_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"   ✓ Embeddings table exists: {embeddings_table_id}")
                
                # Verify the table has all required columns, especially 'keywords'
                try:
                    existing_table = self.bq_client.get_table(embeddings_table_id)
                    existing_fields = [field.name for field in existing_table.schema]
                    
                    # Check for missing critical columns
                    required_fields = ['keywords', 'importance_score', 'summary', 'chunk_hash']
                    missing_fields = [field for field in required_fields if field not in existing_fields]
                    
                    if missing_fields:
                        logger.warning(f"   ⚠️  Table missing columns: {missing_fields} - recreating table")
                        # Delete and recreate table with correct schema
                        self.bq_client.delete_table(embeddings_table_id)
                        logger.info(f"   ✓ Deleted old table: {embeddings_table_id}")
                        
                        # Recreate with full schema
                        embeddings_table = self.bq_client.create_table(embeddings_table)
                        logger.info(f"   ✓ Recreated embeddings table with full schema: {embeddings_table_id}")
                    else:
                        logger.info(f"   ✓ Table schema is up-to-date: {embeddings_table_id}")
                        
                except Exception as schema_error:
                    logger.error(f"   ❌ Error checking table schema: {str(schema_error)}")
                    # Continue anyway, might work
            else:
                raise e
        
        # Create query cache table
        if self.enable_caching:
            cache_table_id = f"{dataset_id}.query_cache"
            cache_schema = [
                bigquery.SchemaField("query_hash", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("query_text", "STRING"),
                bigquery.SchemaField("results", "JSON"),
                bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP()"),
                bigquery.SchemaField("expires_at", "TIMESTAMP"),
                bigquery.SchemaField("hit_count", "INTEGER", default_value_expression="0"),
            ]
            
            cache_table = bigquery.Table(cache_table_id, schema=cache_schema)
            
            try:
                cache_table = self.bq_client.create_table(cache_table)
                logger.info(f"   ✓ Created cache table: {cache_table_id}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"   ✓ Cache table exists: {cache_table_id}")
        
        # Create analytics table
        analytics_table_id = f"{dataset_id}.query_analytics"
        analytics_schema = [
            bigquery.SchemaField("query_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("query_text", "STRING"),
            bigquery.SchemaField("query_embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("results_count", "INTEGER"),
            bigquery.SchemaField("response_time_ms", "FLOAT64"),
            bigquery.SchemaField("user_feedback", "STRING"),  # positive/negative/neutral
            bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP()"),
        ]
        
        analytics_table = bigquery.Table(analytics_table_id, schema=analytics_schema)
        
        try:
            analytics_table = self.bq_client.create_table(analytics_table)
            logger.info(f"   ✓ Created analytics table: {analytics_table_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"   ✓ Analytics table exists: {analytics_table_id}")
        
        # Create advanced SQL functions
        self._create_sql_functions()
        
        return {
            "dataset": dataset_id,
            "embeddings_table": embeddings_table_id,
            "cache_table": f"{dataset_id}.query_cache" if self.enable_caching else None,
            "analytics_table": analytics_table_id
        }
    
    def _create_sql_functions(self):
        """Create advanced SQL functions for search"""
        
        # Cosine similarity function
        cosine_func_sql = f"""
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
            self.bq_client.query(cosine_func_sql).result()
            logger.info(f"   ✓ Created cosine similarity function")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"   ✓ Cosine similarity function exists")
        
        # BM25 scoring function for hybrid search
        if self.enable_hybrid_search:
            bm25_func_sql = f"""
            CREATE OR REPLACE FUNCTION `{self.project_id}.{self.dataset_id}.bm25_score`(
                term_frequency FLOAT64,
                doc_length FLOAT64,
                avg_doc_length FLOAT64,
                doc_frequency FLOAT64,
                total_docs FLOAT64
            ) AS (
                -- BM25 with default parameters k1=1.2, b=0.75
                (term_frequency * 2.2) / 
                (term_frequency + 1.2 * (0.25 + 0.75 * doc_length / avg_doc_length)) *
                LOG(((total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5)) + 1)
            );
            """
            
            try:
                self.bq_client.query(bm25_func_sql).result()
                logger.info(f"   ✓ Created BM25 scoring function")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"   ✓ BM25 function exists")
    
    def process_pdf(self, pdf_path: str) -> str:
        """Advanced PDF processing with layout awareness"""
        
        text = ""
        
        try:
            # Try pdfplumber first (better for tables and layout)
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                    
                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            text += " | ".join(str(cell) for cell in row if cell) + "\n"
                        text += "\n"
        except:
            # Fallback to PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                for page in pdf.pages:
                    text += page.extract_text() + "\n\n"
        
        return text
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """Extract keywords from text using TF-IDF approach"""
        
        from collections import Counter
        import re
        
        # Simple keyword extraction (can be enhanced with NLTK/spaCy)
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter stop words (basic list)
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 
                     'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by', 'from'}
        words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Get top keywords
        word_counts = Counter(words)
        keywords = [word for word, _ in word_counts.most_common(top_k)]
        
        return keywords
    
    def calculate_importance_score(self, chunk: Dict[str, Any], document: Dict[str, Any]) -> float:
        """Calculate importance score for a chunk"""
        
        # Factors for importance scoring
        score = 0.5  # Base score
        
        # Position in document (earlier chunks often more important)
        position_factor = 1.0 - (chunk["chunk_index"] / max(document.get("total_chunks", 10), 1))
        score += position_factor * 0.2
        
        # Length factor (very short or very long chunks less important)
        optimal_length = 500
        length_diff = abs(chunk["chunk_length"] - optimal_length) / optimal_length
        length_factor = max(0, 1 - length_diff)
        score += length_factor * 0.2
        
        # Keyword density (more keywords = more important)
        keywords = self.extract_keywords(chunk["text"], 5)
        keyword_factor = min(len(keywords) / 5, 1.0)
        score += keyword_factor * 0.1
        
        return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
    
    def process_documents_enhanced(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced document processing with parallel processing"""
        
        logger.info(f"⚙️  Processing {len(documents)} documents with enhanced features...")
        
        all_chunks = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for doc in documents:
                future = executor.submit(self._process_single_document, doc)
                futures.append(future)
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing documents"):
                chunks = future.result()
                all_chunks.extend(chunks)
        
        logger.info(f"   ✓ Processed {len(all_chunks)} chunks with enhanced features")
        return all_chunks
    
    def _process_single_document(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single document with all enhancements"""
        
        # Split into chunks
        chunk_dicts = self.text_splitter.split_text(doc["content"])
        doc["total_chunks"] = len(chunk_dicts)
        
        processed_chunks = []
        chunk_texts = []
        chunk_data = []
        
        for chunk_dict in chunk_dicts:
            chunk_text = chunk_dict["text"]
            chunk_id = f"{doc['document_id']}_chunk_{chunk_dict['chunk_index']:04d}"
            
            # Calculate chunk hash for deduplication
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()
            
            # Extract keywords
            keywords = self.extract_keywords(chunk_text)
            
            # Calculate importance score
            importance_score = self.calculate_importance_score(chunk_dict, doc)
            
            # Generate summary (using simple truncation, can use LLM)
            summary = chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
            
            chunk_info = {
                "document_id": doc["document_id"],
                "chunk_id": chunk_id,
                "chunk_text": chunk_text,
                "chunk_index": chunk_dict["chunk_index"],
                "chunk_hash": chunk_hash,
                "keywords": keywords,
                "summary": summary,
                "importance_score": importance_score,
                "embedding_model": self.embedding_model_name,
                "metadata": {
                    "title": doc.get("title", ""),
                    "document_type": doc.get("document_type", "unknown"),
                    "facility": doc.get("facility", "unknown"),
                    "created_date": doc.get("created_date", datetime.now().isoformat()),
                    "chunk_length": chunk_dict["chunk_length"],
                    "total_chunks": doc["total_chunks"]
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
        
        return processed_chunks
    
    def query_with_cache(self, query_text: str) -> Optional[Dict[str, Any]]:
        """Check query cache before processing"""
        
        if not self.enable_caching:
            return None
        
        query_hash = hashlib.md5(query_text.encode()).hexdigest()
        
        cache_query = f"""
        SELECT results
        FROM `{self.project_id}.{self.dataset_id}.query_cache`
        WHERE query_hash = @query_hash
          AND expires_at > CURRENT_TIMESTAMP()
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query_hash", "STRING", query_hash)
            ]
        )
        
        try:
            results = list(self.bq_client.query(cache_query, job_config=job_config).result())
            
            if results:
                # Update hit count
                update_query = f"""
                UPDATE `{self.project_id}.{self.dataset_id}.query_cache`
                SET hit_count = hit_count + 1
                WHERE query_hash = @query_hash
                """
                self.bq_client.query(update_query, job_config=job_config).result()
                
                logger.info("   ✓ Cache hit!")
                return json.loads(results[0].results)
        except:
            pass
        
        return None
    
    def save_to_cache(self, query_text: str, results: Dict[str, Any]):
        """Save query results to cache"""
        
        if not self.enable_caching:
            return
        
        query_hash = hashlib.md5(query_text.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=self.cache_ttl_hours)
        
        insert_query = f"""
        INSERT INTO `{self.project_id}.{self.dataset_id}.query_cache`
        (query_hash, query_text, results, expires_at)
        VALUES (@query_hash, @query_text, @results, @expires_at)
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query_hash", "STRING", query_hash),
                bigquery.ScalarQueryParameter("query_text", "STRING", query_text),
                bigquery.ScalarQueryParameter("results", "STRING", json.dumps(results)),
                bigquery.ScalarQueryParameter("expires_at", "TIMESTAMP", expires_at),
            ]
        )
        
        try:
            self.bq_client.query(insert_query, job_config=job_config).result()
            logger.info("   ✓ Saved to cache")
        except:
            pass
    
    def hybrid_search(self, 
                     query_text: str,
                     query_embedding: List[float],
                     k: int = 10,
                     alpha: float = 0.7) -> List[Dict[str, Any]]:
        """Hybrid search combining semantic and keyword search"""
        
        # Extract query keywords
        query_keywords = self.extract_keywords(query_text, 5)
        
        # Build hybrid search query
        hybrid_query = f"""
        WITH 
        -- Semantic search scores
        semantic_scores AS (
            SELECT 
                document_id,
                chunk_id,
                chunk_text,
                metadata,
                keywords,
                importance_score,
                `{self.project_id}.{self.dataset_id}.cosine_similarity`(
                    embedding,
                    @query_embedding
                ) as semantic_score
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings`
        ),
        -- Keyword search scores
        keyword_scores AS (
            SELECT 
                document_id,
                chunk_id,
                ARRAY_LENGTH(
                    ARRAY(
                        SELECT keyword 
                        FROM UNNEST(keywords) keyword
                        WHERE keyword IN UNNEST(@query_keywords)
                    )
                ) / ARRAY_LENGTH(keywords) as keyword_score
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings`
            WHERE EXISTS (
                SELECT 1 FROM UNNEST(keywords) keyword
                WHERE keyword IN UNNEST(@query_keywords)
            )
        )
        -- Combine scores
        SELECT 
            s.document_id,
            s.chunk_id,
            s.chunk_text,
            s.metadata,
            s.semantic_score,
            COALESCE(k.keyword_score, 0) as keyword_score,
            s.importance_score,
            -- Hybrid score with alpha weighting
            (@alpha * s.semantic_score + 
             (1 - @alpha) * COALESCE(k.keyword_score, 0) * 0.5 +
             s.importance_score * 0.2) as hybrid_score
        FROM semantic_scores s
        LEFT JOIN keyword_scores k
        ON s.document_id = k.document_id AND s.chunk_id = k.chunk_id
        WHERE s.semantic_score > 0.3 OR k.keyword_score > 0
        ORDER BY hybrid_score DESC
        LIMIT @k
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
                bigquery.ArrayQueryParameter("query_keywords", "STRING", query_keywords),
                bigquery.ScalarQueryParameter("alpha", "FLOAT64", alpha),
                bigquery.ScalarQueryParameter("k", "INT64", k),
            ]
        )
        
        results = list(self.bq_client.query(hybrid_query, job_config=job_config).result())
        
        formatted_results = []
        for row in results:
            formatted_results.append({
                "document_id": row.document_id,
                "chunk_id": row.chunk_id,
                "chunk_text": row.chunk_text,
                "semantic_score": float(row.semantic_score),
                "keyword_score": float(row.keyword_score),
                "importance_score": float(row.importance_score),
                "hybrid_score": float(row.hybrid_score),
                "metadata": json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata
            })
        
        return formatted_results
    
    def rerank_results(self, 
                       query_text: str,
                       results: List[Dict[str, Any]],
                       top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank results using cross-encoder or LLM"""
        
        if not self.enable_reranking or not results:
            return results[:top_k]
        
        # Use Gemini for reranking (cross-encoder approach)
        rerank_prompt = f"""Score the relevance of each passage to the query on a scale of 0-1.
        
Query: {query_text}

Passages:
"""
        
        for i, result in enumerate(results[:10]):  # Limit to top 10 for reranking
            rerank_prompt += f"\n{i+1}. {result['chunk_text'][:200]}..."
        
        rerank_prompt += "\n\nProvide scores as JSON: {\"1\": score1, \"2\": score2, ...}"
        
        try:
            response = self.generation_model.generate_content(
                rerank_prompt,
                generation_config={"temperature": 0}
            )
            
            # Parse scores
            scores_text = response.text
            import re
            scores_match = re.search(r'\{[^}]+\}', scores_text)
            
            if scores_match:
                scores = json.loads(scores_match.group())
                
                # Add rerank scores to results
                for i, result in enumerate(results[:10]):
                    result["rerank_score"] = float(scores.get(str(i+1), 0))
                
                # Sort by rerank score
                results = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
                
                logger.info("   ✓ Results reranked")
        except:
            logger.warning("   ⚠ Reranking failed, using original order")
        
        return results[:top_k]
    
    def query_enhanced(self,
                      query_text: str,
                      k: int = 10,
                      use_hybrid: bool = None,
                      use_cache: bool = None,
                      use_reranking: bool = None,
                      filter_sql: str = None) -> Dict[str, Any]:
        """Enhanced query with all features"""
        
        logger.info(f"🔍 Enhanced query: {query_text[:50]}...")
        
        # Override defaults if specified
        use_hybrid = use_hybrid if use_hybrid is not None else self.enable_hybrid_search
        use_cache = use_cache if use_cache is not None else self.enable_caching
        use_reranking = use_reranking if use_reranking is not None else self.enable_reranking
        
        start_time = time.time()
        
        # Check cache
        if use_cache:
            cached_result = self.query_with_cache(query_text)
            if cached_result:
                cached_result["from_cache"] = True
                return cached_result
        
        # Generate query embedding
        query_embedding = self.embedding_model.get_embeddings([query_text])[0].values
        embedding_time = time.time() - start_time
        
        # Search
        if use_hybrid:
            results = self.hybrid_search(query_text, query_embedding, k * 2)
        else:
            # Standard semantic search
            sql_query = f"""
            SELECT 
                document_id,
                chunk_id,
                chunk_text,
                metadata,
                importance_score,
                `{self.project_id}.{self.dataset_id}.cosine_similarity`(
                    embedding,
                    @query_embedding
                ) as similarity_score
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings`
            WHERE `{self.project_id}.{self.dataset_id}.cosine_similarity`(
                embedding,
                @query_embedding
            ) > 0.3
            {f"AND {filter_sql}" if filter_sql else ""}
            ORDER BY similarity_score DESC
            LIMIT @k
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
                    bigquery.ScalarQueryParameter("k", "INT64", k * 2),
                ]
            )
            
            query_job = self.bq_client.query(sql_query, job_config=job_config)
            results = list(query_job.result())
            
            results = [{
                "document_id": row.document_id,
                "chunk_id": row.chunk_id,
                "chunk_text": row.chunk_text,
                "similarity_score": float(row.similarity_score),
                "importance_score": float(row.importance_score),
                "metadata": json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata
            } for row in results]
        
        search_time = time.time() - start_time - embedding_time
        
        # Rerank if enabled
        if use_reranking:
            results = self.rerank_results(query_text, results, k)
            rerank_time = time.time() - start_time - search_time - embedding_time
        else:
            results = results[:k]
            rerank_time = 0
        
        # Generate answer
        if results:
            context = "\n\n".join([r["chunk_text"] for r in results[:3]])
            
            prompt = f"""Based on the following context, provide a comprehensive answer to the question.

Context:
{context}

Question: {query_text}

Provide a clear, accurate answer based on the given context. If the context doesn't contain enough information, say so.

Answer:"""
            
            response = self.generation_model.generate_content(prompt)
            answer = response.text
        else:
            answer = "No relevant information found."
        
        generation_time = time.time() - start_time - search_time - embedding_time - rerank_time
        total_time = time.time() - start_time
        
        # Prepare response
        response_data = {
            "query": query_text,
            "answer": answer,
            "results": results,
            "num_results": len(results),
            "search_type": "hybrid" if use_hybrid else "semantic",
            "reranked": use_reranking,
            "from_cache": False,
            "timings": {
                "embedding_ms": embedding_time * 1000,
                "search_ms": search_time * 1000,
                "rerank_ms": rerank_time * 1000,
                "generation_ms": generation_time * 1000,
                "total_ms": total_time * 1000
            },
            "models": {
                "embedding": self.embedding_model_name,
                "generation": self.generation_model_name
            }
        }
        
        # Save to cache
        if use_cache:
            self.save_to_cache(query_text, response_data)
        
        # Log analytics
        self._log_query_analytics(query_text, query_embedding, response_data)
        
        return response_data
    
    def _log_query_analytics(self, 
                            query_text: str,
                            query_embedding: List[float],
                            response_data: Dict[str, Any]):
        """Log query analytics for monitoring and improvement"""
        
        try:
            query_id = hashlib.md5(f"{query_text}{time.time()}".encode()).hexdigest()
            
            insert_query = f"""
            INSERT INTO `{self.project_id}.{self.dataset_id}.query_analytics`
            (query_id, query_text, query_embedding, results_count, response_time_ms)
            VALUES (@query_id, @query_text, @query_embedding, @results_count, @response_time_ms)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id),
                    bigquery.ScalarQueryParameter("query_text", "STRING", query_text),
                    bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
                    bigquery.ScalarQueryParameter("results_count", "INT64", response_data["num_results"]),
                    bigquery.ScalarQueryParameter("response_time_ms", "FLOAT64", response_data["timings"]["total_ms"]),
                ]
            )
            
            self.bq_client.query(insert_query, job_config=job_config).result()
        except:
            pass  # Don't fail query if analytics logging fails
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary for monitoring"""
        
        summary_query = f"""
        WITH query_stats AS (
            SELECT 
                COUNT(*) as total_queries,
                AVG(response_time_ms) as avg_response_time_ms,
                MAX(response_time_ms) as max_response_time_ms,
                MIN(response_time_ms) as min_response_time_ms,
                AVG(results_count) as avg_results_count
            FROM `{self.project_id}.{self.dataset_id}.query_analytics`
            WHERE created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ),
        cache_stats AS (
            SELECT 
                COUNT(*) as total_cached,
                AVG(hit_count) as avg_hits_per_query
            FROM `{self.project_id}.{self.dataset_id}.query_cache`
            WHERE expires_at > CURRENT_TIMESTAMP()
        ),
        document_stats AS (
            SELECT 
                COUNT(DISTINCT document_id) as total_documents,
                COUNT(*) as total_chunks,
                AVG(importance_score) as avg_importance_score
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings`
        )
        SELECT * FROM query_stats, cache_stats, document_stats
        """
        
        try:
            results = list(self.bq_client.query(summary_query).result())
            
            if results:
                row = results[0]
                return {
                    "query_statistics": {
                        "total_queries_24h": row.total_queries,
                        "avg_response_time_ms": row.avg_response_time_ms,
                        "max_response_time_ms": row.max_response_time_ms,
                        "min_response_time_ms": row.min_response_time_ms,
                        "avg_results_per_query": row.avg_results_count
                    },
                    "cache_statistics": {
                        "total_cached_queries": row.total_cached,
                        "avg_cache_hits": row.avg_hits_per_query
                    },
                    "document_statistics": {
                        "total_documents": row.total_documents,
                        "total_chunks": row.total_chunks,
                        "avg_importance_score": row.avg_importance_score
                    }
                }
        except:
            return {"status": "No analytics data available"}
    
    def deploy_enhanced(self) -> Dict[str, Any]:
        """Deploy enhanced BigQuery RAG system"""
        
        logger.info("🚀 Starting Enhanced BigQuery RAG deployment...\n")
        
        try:
            # Check and fix table schema if needed
            schema_fixed = self.fix_table_schema()
            
            # Setup BigQuery resources
            resources = self.setup_bigquery_resources()
            
            # Generate sample documents
            from src.cloud_shell_rag import GoogleCloudRAG
            basic_rag = GoogleCloudRAG()
            documents = basic_rag.generate_sample_documents()
            
            # Process with enhancements
            chunks = self.process_documents_enhanced(documents)
            
            # Upload to BigQuery
            df = pd.DataFrame(chunks)
            table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings"
            
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_APPEND",
            )
            
            job = self.bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
            job.result()
            
            # Test enhanced query
            test_result = self.query_enhanced(
                "What are the maintenance procedures?",
                use_hybrid=True,
                use_cache=False,
                use_reranking=True
            )
            
            logger.info("\n✅ Enhanced BigQuery RAG deployed successfully!")
            
            return {
                "success": True,
                "resources": resources,
                "documents_processed": len(documents),
                "chunks_created": len(chunks),
                "test_query": {
                    "answer": test_result["answer"][:200] + "...",
                    "num_results": test_result["num_results"],
                    "search_type": test_result["search_type"],
                    "timings": test_result["timings"]
                },
                "features_enabled": {
                    "hybrid_search": self.enable_hybrid_search,
                    "caching": self.enable_caching,
                    "reranking": self.enable_reranking
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {str(e)}")
            return {"success": False, "error": str(e)}


# CLI Interface
if __name__ == "__main__":
    import sys
    
    rag = BigQueryRAGEnhanced()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "deploy":
            result = rag.deploy_enhanced()
            print(json.dumps(result, indent=2))
            
        elif command == "query":
            if len(sys.argv) > 2:
                query_text = " ".join(sys.argv[2:])
                result = rag.query_enhanced(query_text)
                print(f"\nQuery: {result['query']}")
                print(f"Answer: {result['answer']}")
                print(f"Results: {result['num_results']}")
                print(f"Search Type: {result['search_type']}")
                print(f"Time: {result['timings']['total_ms']:.2f}ms")
            else:
                print("Usage: python bigquery_rag_enhanced.py query <your question>")
                
        elif command == "analytics":
            stats = rag.get_analytics_summary()
            print(json.dumps(stats, indent=2))
            
        elif command == "fix-schema":
            print("🔧 Checking and fixing BigQuery table schema...")
            schema_fixed = rag.fix_table_schema()
            if schema_fixed:
                print("✅ Table schema fixed! Re-run 'deploy' to populate data.")
            else:
                print("✅ Table schema is already correct.")
            
        else:
            print("Commands: deploy, query, analytics, fix-schema")
    else:
        print("Enhanced BigQuery RAG ready. Commands: deploy, query, analytics, fix-schema")