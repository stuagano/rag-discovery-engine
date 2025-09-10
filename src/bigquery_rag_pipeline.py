"""
BigQuery-Optimized RAG Pipeline for Manufacturing Documents
Implements high-performance RAG system with enterprise security
"""

from google.cloud import bigquery
from google.cloud import aiplatform
from google.oauth2 import service_account
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import time
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import hashlib
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedManufacturingRAG:
    """High-performance RAG pipeline optimized for BigQuery and manufacturing content"""
    
    def __init__(self, project_id: str, dataset_id: str = "manufacturing_rag_optimized"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        
        # Initialize Vertex AI with latest embedding model
        aiplatform.init(project=project_id, location="us-central1")
        self.embedding_model = self._initialize_embedding_model()
        
        # Performance tracking
        self.performance_metrics = {
            'queries_executed': 0,
            'total_query_time': 0,
            'cache_hits': 0,
            'embeddings_generated': 0
        }
        
        # Query cache for performance
        self.query_cache = {}
        
    def _initialize_embedding_model(self):
        """Initialize state-of-the-art embedding model for technical content"""
        from vertexai.language_models import TextEmbeddingModel
        
        # Use latest Gecko model optimized for technical content
        return TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
    
    def setup_optimized_schema(self) -> bigquery.Table:
        """Create optimized BigQuery schema with partitioning and clustering"""
        
        logger.info("Setting up optimized BigQuery schema...")
        
        # Create dataset
        dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset_id)
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "us-central1"
        dataset.description = "Optimized RAG system for manufacturing documents"
        
        try:
            dataset = self.client.create_dataset(dataset, timeout=30, exists_ok=True)
            logger.info(f"Dataset {self.dataset_id} ready")
        except Exception as e:
            logger.info(f"Dataset exists or creation handled: {e}")
        
        # Optimized table schema with manufacturing-specific fields
        schema = [
            # Core document fields
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED", description="Unique document identifier"),
            bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED", description="Unique chunk identifier"),
            bigquery.SchemaField("chunk_text", "STRING", mode="REQUIRED", description="Document chunk content"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED", description="Text embedding vector"),
            
            # Manufacturing-specific categorization
            bigquery.SchemaField("document_type", "STRING", mode="REQUIRED", description="Document type for partitioning"),
            bigquery.SchemaField("facility_code", "STRING", description="Manufacturing facility code"),
            bigquery.SchemaField("equipment_type", "STRING", description="Related equipment type"),
            bigquery.SchemaField("process_category", "STRING", description="Manufacturing process category"),
            bigquery.SchemaField("safety_level", "STRING", description="Safety criticality level"),
            
            # Content analysis fields
            bigquery.SchemaField("section_type", "STRING", description="Document section type"),
            bigquery.SchemaField("technical_complexity", "INTEGER", description="Technical complexity score 1-10"),
            bigquery.SchemaField("quality_score", "FLOAT64", description="Content quality score"),
            bigquery.SchemaField("keyword_tags", "STRING", mode="REPEATED", description="Extracted keywords"),
            
            # Multimodal content
            bigquery.SchemaField("tables_json", "JSON", description="Extracted table data"),
            bigquery.SchemaField("images_metadata", "JSON", description="Image metadata and descriptions"),
            bigquery.SchemaField("has_diagrams", "BOOLEAN", description="Contains technical diagrams"),
            
            # Metadata and tracking
            bigquery.SchemaField("source_system", "STRING", description="Source system (discovery_engine, manual, etc.)"),
            bigquery.SchemaField("version", "STRING", description="Document version"),
            bigquery.SchemaField("last_updated", "TIMESTAMP", description="Last document update"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED", description="Ingestion timestamp"),
            
            # Performance optimization fields
            bigquery.SchemaField("embedding_model", "STRING", description="Embedding model used"),
            bigquery.SchemaField("chunk_hash", "STRING", description="Content hash for deduplication"),
        ]
        
        # Create main embeddings table
        table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings_optimized"
        table = bigquery.Table(table_id, schema=schema)
        
        # Partitioning for query performance (by created_at)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="created_at"
        )
        
        # Clustering for faster similarity search and filtering
        table.clustering_fields = ["document_type", "facility_code", "process_category", "safety_level"]
        
        # Table description
        table.description = "Optimized document embeddings for manufacturing RAG system"
        
        try:
            table = self.client.create_table(table, exists_ok=True)
            logger.info(f"Created optimized embeddings table: {table_id}")
        except Exception as e:
            logger.info(f"Table exists or creation handled: {e}")
        
        # Create vector index if supported
        self._create_vector_search_functions()
        
        # Create summary/analytics table
        self._create_analytics_tables()
        
        return table
    
    def _create_vector_search_functions(self):
        """Create optimized vector search SQL functions"""
        
        # Optimized cosine similarity function
        cosine_similarity_sql = f"""
        CREATE OR REPLACE FUNCTION `{self.project_id}.{self.dataset_id}.cosine_similarity`(
            embedding1 ARRAY<FLOAT64>,
            embedding2 ARRAY<FLOAT64>
        ) RETURNS FLOAT64
        LANGUAGE js AS '''
            if (!embedding1 || !embedding2 || embedding1.length !== embedding2.length) {{
                return 0.0;
            }}
            
            let dotProduct = 0.0;
            let norm1 = 0.0;
            let norm2 = 0.0;
            
            for (let i = 0; i < embedding1.length; i++) {{
                dotProduct += embedding1[i] * embedding2[i];
                norm1 += embedding1[i] * embedding1[i];
                norm2 += embedding2[i] * embedding2[i];
            }}
            
            if (norm1 === 0.0 || norm2 === 0.0) {{
                return 0.0;
            }}
            
            return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
        ''';
        """
        
        # Euclidean distance function for alternative similarity
        euclidean_distance_sql = f"""
        CREATE OR REPLACE FUNCTION `{self.project_id}.{self.dataset_id}.euclidean_distance`(
            embedding1 ARRAY<FLOAT64>,
            embedding2 ARRAY<FLOAT64>
        ) RETURNS FLOAT64
        LANGUAGE js AS '''
            if (!embedding1 || !embedding2 || embedding1.length !== embedding2.length) {{
                return 999999.0;
            }}
            
            let sum = 0.0;
            for (let i = 0; i < embedding1.length; i++) {{
                let diff = embedding1[i] - embedding2[i];
                sum += diff * diff;
            }}
            
            return Math.sqrt(sum);
        ''';
        """
        
        try:
            self.client.query(cosine_similarity_sql).result()
            self.client.query(euclidean_distance_sql).result()
            logger.info("Created optimized vector similarity functions")
        except Exception as e:
            logger.error(f"Error creating vector functions: {e}")
    
    def _create_analytics_tables(self):
        """Create analytics and summary tables"""
        
        # Query analytics table
        analytics_schema = [
            bigquery.SchemaField("query_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("query_text", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("query_embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("execution_time_ms", "INTEGER"),
            bigquery.SchemaField("result_count", "INTEGER"),
            bigquery.SchemaField("top_similarity_score", "FLOAT64"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("facility_filter", "STRING"),
            bigquery.SchemaField("query_timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        analytics_table_id = f"{self.project_id}.{self.dataset_id}.query_analytics"
        analytics_table = bigquery.Table(analytics_table_id, schema=analytics_schema)
        
        # Partition by query_timestamp
        analytics_table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="query_timestamp"
        )
        
        try:
            self.client.create_table(analytics_table, exists_ok=True)
            logger.info("Created query analytics table")
        except Exception as e:
            logger.info(f"Analytics table exists: {e}")
    
    def process_manufacturing_documents_batch(self, documents: List[Dict[str, Any]], batch_size: int = 50) -> Dict[str, Any]:
        """Process manufacturing documents in optimized batches with parallel processing"""
        
        logger.info(f"Processing {len(documents)} documents in batches of {batch_size}")
        
        processing_stats = {
            'total_documents': len(documents),
            'processed_chunks': 0,
            'failed_documents': 0,
            'processing_time': 0,
            'embedding_time': 0
        }
        
        start_time = time.time()
        
        # Process documents in batches
        for batch_start in range(0, len(documents), batch_size):
            batch_end = min(batch_start + batch_size, len(documents))
            batch = documents[batch_start:batch_end]
            
            batch_start_time = time.time()
            
            # Parallel processing within batch
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(self._process_single_manufacturing_document, doc)
                    for doc in batch
                ]
                
                batch_results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            batch_results.extend(result)
                    except Exception as e:
                        logger.error(f"Document processing error: {e}")
                        processing_stats['failed_documents'] += 1
                
                # Batch insert to BigQuery
                if batch_results:
                    insert_errors = self._batch_insert_optimized(batch_results)
                    if insert_errors:
                        logger.error(f"BigQuery insert errors: {insert_errors}")
                    else:
                        processing_stats['processed_chunks'] += len(batch_results)
            
            batch_time = time.time() - batch_start_time
            progress = (batch_end / len(documents)) * 100
            rate = len(batch) / batch_time if batch_time > 0 else 0
            
            logger.info(f"Batch progress: {progress:.1f}% complete, {rate:.1f} docs/sec")
        
        processing_stats['processing_time'] = time.time() - start_time
        
        logger.info(f"Processing complete: {processing_stats['processed_chunks']} chunks, "
                   f"{processing_stats['failed_documents']} failures")
        
        return processing_stats
    
    def _process_single_manufacturing_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process single manufacturing document with enhanced metadata extraction"""
        
        try:
            content = document.get('content', '')
            if not content or len(content) < 50:
                return []
            
            # Intelligent chunking for manufacturing content
            chunks = self._chunk_manufacturing_document(content, document)
            
            # Generate embeddings for all chunks at once (batch processing)
            chunk_texts = [chunk['text'] for chunk in chunks]
            embeddings = self._generate_batch_embeddings(chunk_texts)
            
            # Process chunks with embeddings
            processed_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                
                # Extract manufacturing-specific metadata
                manufacturing_metadata = self._extract_manufacturing_metadata(chunk['text'], document)
                
                processed_chunk = {
                    # Core fields
                    'document_id': document.get('id', f"doc_{int(time.time())}"),
                    'chunk_id': f"{document.get('id', 'unknown')}_chunk_{i}",
                    'chunk_text': chunk['text'],
                    'embedding': embedding,
                    
                    # Manufacturing categorization
                    'document_type': manufacturing_metadata['document_type'],
                    'facility_code': document.get('facility_code', manufacturing_metadata['facility_code']),
                    'equipment_type': manufacturing_metadata['equipment_type'],
                    'process_category': manufacturing_metadata['process_category'],
                    'safety_level': manufacturing_metadata['safety_level'],
                    
                    # Content analysis
                    'section_type': chunk['section_type'],
                    'technical_complexity': manufacturing_metadata['technical_complexity'],
                    'quality_score': self._calculate_content_quality_score(chunk['text']),
                    'keyword_tags': manufacturing_metadata['keywords'],
                    
                    # Multimodal content
                    'tables_json': chunk.get('tables', []),
                    'images_metadata': chunk.get('images', []),
                    'has_diagrams': manufacturing_metadata['has_diagrams'],
                    
                    # Metadata
                    'source_system': document.get('source', 'manual_upload'),
                    'version': document.get('version', '1.0'),
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    
                    # Performance optimization
                    'embedding_model': 'textembedding-gecko@003',
                    'chunk_hash': hashlib.md5(chunk['text'].encode()).hexdigest(),
                }
                
                processed_chunks.append(processed_chunk)
            
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Error processing document {document.get('id', 'unknown')}: {e}")
            return []
    
    def _chunk_manufacturing_document(self, content: str, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Intelligent chunking optimized for manufacturing documents"""
        
        # Manufacturing-specific separators (in priority order)
        separators = [
            "\\n## ",        # Major section headers
            "\\nStep ",      # Procedure steps
            "\\nWARNING:",   # Safety warnings (high priority)
            "\\nCAUTION:",   # Caution notices
            "\\nNOTE:",      # Important notes
            "\\nPROCEDURE:", # Procedure sections
            "\\nSPECIFICATION:", # Technical specifications
            "\\n\\n",        # Paragraph breaks
            "\\n",           # Line breaks
            ". ",            # Sentence boundaries
            ", ",            # Clause boundaries
        ]
        
        # Dynamic chunk size based on document type
        doc_type = document.get('doc_type', 'general')
        if doc_type in ['procedure', 'manual']:
            chunk_size = 800   # Smaller chunks for step-by-step procedures
            overlap = 150
        elif doc_type in ['specification', 'standard']:
            chunk_size = 1200  # Larger chunks for technical specifications
            overlap = 200
        else:
            chunk_size = 1000  # Default chunk size
            overlap = 200
        
        # Simple chunking implementation (in production, use LangChain's RecursiveCharacterTextSplitter)
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            
            # Try to end at a sentence boundary
            if end < len(content):
                # Find the last period within the chunk
                last_period = content.rfind('.', start, end)
                if last_period > start + chunk_size * 0.5:  # At least 50% of chunk size
                    end = last_period + 1
            
            chunk_text = content[start:end].strip()
            
            if len(chunk_text) > 100:  # Minimum chunk size
                section_type = self._classify_manufacturing_section(chunk_text)
                
                chunks.append({
                    'text': chunk_text,
                    'section_type': section_type,
                    'chunk_id': chunk_id,
                    'start_pos': start,
                    'end_pos': end
                })
                chunk_id += 1
            
            # Move to next chunk with overlap
            start = max(end - overlap, start + 1)
            if start >= len(content):
                break
        
        return chunks
    
    def _classify_manufacturing_section(self, text: str) -> str:
        """Classify the type of manufacturing content section"""
        text_lower = text.lower()
        
        # Safety-related content (highest priority)
        if any(word in text_lower for word in ['warning', 'caution', 'danger', 'hazard', 'safety', 'emergency']):
            return 'safety'
        
        # Procedure/process content
        elif any(word in text_lower for word in ['procedure', 'step', 'process', 'method', 'operation']):
            return 'procedure'
        
        # Technical specifications
        elif any(word in text_lower for word in ['specification', 'requirement', 'parameter', 'tolerance', 'standard']):
            return 'specification'
        
        # Maintenance content
        elif any(word in text_lower for word in ['maintenance', 'service', 'repair', 'inspection', 'calibration']):
            return 'maintenance'
        
        # Quality control
        elif any(word in text_lower for word in ['quality', 'control', 'test', 'measurement', 'defect', 'inspection']):
            return 'quality_control'
        
        # Equipment-related
        elif any(word in text_lower for word in ['equipment', 'machine', 'tool', 'instrument', 'device']):
            return 'equipment'
        
        # General content
        else:
            return 'general'
    
    def _extract_manufacturing_metadata(self, text: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract manufacturing-specific metadata from text content"""
        
        text_lower = text.lower()
        
        # Determine document type
        doc_types = {
            'procedure': ['procedure', 'process', 'method', 'step-by-step'],
            'specification': ['specification', 'spec', 'requirement', 'standard'],
            'manual': ['manual', 'guide', 'handbook', 'instruction'],
            'safety': ['safety', 'hazard', 'warning', 'emergency'],
            'maintenance': ['maintenance', 'service', 'repair', 'pm'],
            'quality': ['quality', 'qc', 'inspection', 'test']
        }
        
        document_type = 'general'
        for doc_type, keywords in doc_types.items():
            if any(keyword in text_lower for keyword in keywords):
                document_type = doc_type
                break
        
        # Extract equipment type
        equipment_keywords = {
            'ion_implanter': ['ion implanter', 'implanter', 'ion implantation'],
            'cvd': ['cvd', 'chemical vapor deposition', 'deposition'],
            'etcher': ['etcher', 'etch', 'etching', 'plasma etch'],
            'lithography': ['lithography', 'stepper', 'scanner', 'photolithography'],
            'metrology': ['metrology', 'measurement', 'inspection', 'sem', 'microscope'],
            'cmp': ['cmp', 'chemical mechanical', 'polishing', 'planarization']
        }
        
        equipment_type = 'general'
        for eq_type, keywords in equipment_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                equipment_type = eq_type
                break
        
        # Determine safety level
        safety_keywords_high = ['danger', 'toxic', 'hazardous', 'emergency', 'explosion', 'fire']
        safety_keywords_medium = ['warning', 'caution', 'hot', 'electrical', 'chemical']
        
        if any(keyword in text_lower for keyword in safety_keywords_high):
            safety_level = 'high'
        elif any(keyword in text_lower for keyword in safety_keywords_medium):
            safety_level = 'medium'
        else:
            safety_level = 'low'
        
        # Extract process category
        process_categories = {
            'frontend': ['photolithography', 'etch', 'deposition', 'implant', 'diffusion'],
            'backend': ['metallization', 'packaging', 'assembly', 'wire bond'],
            'test': ['test', 'probe', 'burn-in', 'final test', 'validation'],
            'quality': ['inspection', 'metrology', 'defect', 'yield', 'quality']
        }
        
        process_category = 'general'
        for category, keywords in process_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                process_category = category
                break
        
        # Calculate technical complexity (1-10 scale)
        technical_indicators = [
            'specification', 'parameter', 'tolerance', 'measurement', 'calibration',
            'procedure', 'process', 'method', 'algorithm', 'formula', 'equation',
            'temperature', 'pressure', 'flow', 'voltage', 'current', 'frequency'
        ]
        
        complexity_score = min(10, sum(1 for indicator in technical_indicators if indicator in text_lower))
        
        # Extract keywords
        important_terms = []
        manufacturing_terms = [
            'wafer', 'semiconductor', 'silicon', 'photoresist', 'plasma', 'vacuum',
            'temperature', 'pressure', 'flow rate', 'voltage', 'current', 'frequency',
            'thickness', 'uniformity', 'defect', 'yield', 'throughput', 'cycle time'
        ]
        
        for term in manufacturing_terms:
            if term in text_lower:
                important_terms.append(term)
        
        # Check for diagrams/visual content indicators
        has_diagrams = any(indicator in text_lower for indicator in [
            'figure', 'diagram', 'chart', 'graph', 'image', 'illustration',
            'see figure', 'refer to', 'shown in', 'table'
        ])
        
        # Determine facility code (placeholder logic)
        facility_code = document.get('facility_code', 'fab_01')
        
        return {
            'document_type': document_type,
            'facility_code': facility_code,
            'equipment_type': equipment_type,
            'process_category': process_category,
            'safety_level': safety_level,
            'technical_complexity': complexity_score,
            'keywords': important_terms,
            'has_diagrams': has_diagrams
        }
    
    def _generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches for efficiency"""
        try:
            # Batch size for Vertex AI Text Embedding
            batch_size = 100  # Adjust based on API limits
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Generate embeddings for batch
                embeddings = self.embedding_model.get_embeddings(batch_texts)
                batch_embeddings = [embedding.values for embedding in embeddings]
                all_embeddings.extend(batch_embeddings)
                
                self.performance_metrics['embeddings_generated'] += len(batch_texts)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Fallback to individual generation
            return [self._generate_single_embedding(text) for text in texts]
    
    def _generate_single_embedding(self, text: str) -> List[float]:
        """Generate single embedding with error handling"""
        try:
            embeddings = self.embedding_model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # Gecko embedding dimension
    
    def _calculate_content_quality_score(self, text: str) -> float:
        """Calculate comprehensive content quality score"""
        
        score = 1.0
        
        # Length scoring
        text_length = len(text)
        if text_length < 100:
            score *= 0.6  # Very short content penalty
        elif text_length < 200:
            score *= 0.8  # Short content penalty
        elif text_length > 2000:
            score *= 0.9  # Very long content slight penalty
        
        # Technical content indicators (positive)
        technical_terms = [
            'procedure', 'specification', 'requirement', 'standard',
            'measurement', 'tolerance', 'quality', 'control', 'safety',
            'temperature', 'pressure', 'voltage', 'current'
        ]
        
        technical_score = sum(1 for term in technical_terms if term.lower() in text.lower())
        score += min(technical_score * 0.1, 0.5)  # Max 0.5 bonus
        
        # Structure indicators (positive)
        structure_indicators = ['step', ':', ';', 'note:', 'warning:', 'caution:']
        structure_score = sum(1 for indicator in structure_indicators if indicator.lower() in text.lower())
        score += min(structure_score * 0.05, 0.2)  # Max 0.2 bonus
        
        # Readability (sentence structure)
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if sentences:
            avg_sentence_length = text_length / len(sentences)
            if 20 <= avg_sentence_length <= 100:  # Good readability range
                score += 0.1
        
        return min(score, 2.0)  # Cap at 2.0
    
    def _batch_insert_optimized(self, rows: List[Dict[str, Any]]) -> List[Any]:
        """Optimized batch insert to BigQuery with error handling"""
        
        table_id = f"{self.project_id}.{self.dataset_id}.document_embeddings_optimized"
        
        try:
            # Configure job for better performance
            job_config = bigquery.LoadJobConfig(
                # Optimize for batch loading
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
            )
            
            # Insert rows
            errors = self.client.insert_rows_json(
                table_id, 
                rows, 
                timeout=300  # 5 minute timeout for large batches
            )
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
            else:
                logger.info(f"Successfully inserted {len(rows)} chunks")
            
            return errors
            
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            return [str(e)]
    
    def search_manufacturing_documents(self, 
                                     query: str, 
                                     k: int = 5, 
                                     filters: Optional[Dict[str, Any]] = None,
                                     similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Optimized search for manufacturing documents with filtering"""
        
        search_start_time = time.time()
        
        # Check cache first
        cache_key = hashlib.md5(f"{query}_{k}_{filters}_{similarity_threshold}".encode()).hexdigest()
        if cache_key in self.query_cache:
            self.performance_metrics['cache_hits'] += 1
            logger.info(f"Cache hit for query: {query[:50]}...")
            return self.query_cache[cache_key]
        
        try:
            # Generate query embedding
            query_embedding = self._generate_single_embedding(query)
            embedding_str = ",".join(str(x) for x in query_embedding)
            
            # Build optimized query with filters
            filter_conditions = self._build_filter_conditions(filters)
            
            # Advanced similarity search query
            search_sql = f"""
            WITH query_embedding AS (
                SELECT [{embedding_str}] as query_vector
            ),
            similarity_search AS (
                SELECT 
                    document_id,
                    chunk_id,
                    chunk_text,
                    document_type,
                    facility_code,
                    equipment_type,
                    process_category,
                    safety_level,
                    section_type,
                    technical_complexity,
                    quality_score,
                    keyword_tags,
                    tables_json,
                    images_metadata,
                    has_diagrams,
                    source_system,
                    version,
                    last_updated,
                    -- Optimized similarity calculation
                    `{self.project_id}.{self.dataset_id}.cosine_similarity`(
                        embedding, 
                        (SELECT query_vector FROM query_embedding)
                    ) as similarity_score
                FROM `{self.project_id}.{self.dataset_id}.document_embeddings_optimized`
                WHERE 
                    -- Similarity threshold pre-filter for performance
                    TRUE {filter_conditions}
            ),
            ranked_results AS (
                SELECT *,
                    ROW_NUMBER() OVER (ORDER BY similarity_score DESC, quality_score DESC) as rank_num
                FROM similarity_search
                WHERE similarity_score >= {similarity_threshold}
            )
            SELECT *
            FROM ranked_results
            WHERE rank_num <= {k}
            ORDER BY similarity_score DESC, quality_score DESC
            """
            
            # Execute search query
            query_job = self.client.query(search_sql)
            results = list(query_job.result())
            
            # Format results
            formatted_results = []
            for row in results:
                formatted_result = {
                    'document_id': row.document_id,
                    'chunk_id': row.chunk_id,
                    'chunk_text': row.chunk_text,
                    'similarity_score': float(row.similarity_score),
                    'quality_score': float(row.quality_score),
                    'document_type': row.document_type,
                    'facility_code': row.facility_code,
                    'equipment_type': row.equipment_type,
                    'process_category': row.process_category,
                    'safety_level': row.safety_level,
                    'section_type': row.section_type,
                    'technical_complexity': row.technical_complexity,
                    'keyword_tags': row.keyword_tags,
                    'has_diagrams': row.has_diagrams,
                    'source_system': row.source_system,
                    'version': row.version,
                    'last_updated': row.last_updated.isoformat() if row.last_updated else None
                }
                
                # Add multimodal content if available
                if row.tables_json:
                    formatted_result['tables'] = json.loads(row.tables_json) if isinstance(row.tables_json, str) else row.tables_json
                
                if row.images_metadata:
                    formatted_result['images'] = json.loads(row.images_metadata) if isinstance(row.images_metadata, str) else row.images_metadata
                
                formatted_results.append(formatted_result)
            
            # Cache results
            self.query_cache[cache_key] = formatted_results
            
            # Update performance metrics
            search_time = (time.time() - search_start_time) * 1000
            self.performance_metrics['queries_executed'] += 1
            self.performance_metrics['total_query_time'] += search_time
            
            # Log query analytics
            self._log_query_analytics(query, query_embedding, len(formatted_results), 
                                    formatted_results[0]['similarity_score'] if formatted_results else 0,
                                    search_time, filters)
            
            logger.info(f"Search completed in {search_time:.2f}ms, {len(formatted_results)} results")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")
            return []
    
    def _build_filter_conditions(self, filters: Optional[Dict[str, Any]]) -> str:
        """Build SQL WHERE conditions from filters"""
        
        if not filters:
            return ""
        
        conditions = []
        
        # Document type filter
        if 'document_types' in filters:
            doc_types = "', '".join(filters['document_types'])
            conditions.append(f"AND document_type IN ('{doc_types}')")
        
        # Facility filter
        if 'facilities' in filters:
            facilities = "', '".join(filters['facilities'])
            conditions.append(f"AND facility_code IN ('{facilities}')")
        
        # Equipment type filter
        if 'equipment_types' in filters:
            equipment = "', '".join(filters['equipment_types'])
            conditions.append(f"AND equipment_type IN ('{equipment}')")
        
        # Safety level filter
        if 'safety_levels' in filters:
            safety = "', '".join(filters['safety_levels'])
            conditions.append(f"AND safety_level IN ('{safety}')")
        
        # Technical complexity filter
        if 'min_complexity' in filters:
            conditions.append(f"AND technical_complexity >= {filters['min_complexity']}")
        
        if 'max_complexity' in filters:
            conditions.append(f"AND technical_complexity <= {filters['max_complexity']}")
        
        # Quality score filter
        if 'min_quality_score' in filters:
            conditions.append(f"AND quality_score >= {filters['min_quality_score']}")
        
        # Date range filter
        if 'date_from' in filters:
            conditions.append(f"AND created_at >= '{filters['date_from']}'")
        
        if 'date_to' in filters:
            conditions.append(f"AND created_at <= '{filters['date_to']}'")
        
        return " ".join(conditions)
    
    def _log_query_analytics(self, query_text: str, query_embedding: List[float], 
                           result_count: int, top_score: float, execution_time: float,
                           filters: Optional[Dict[str, Any]]):
        """Log query analytics for performance monitoring"""
        
        analytics_row = {
            'query_id': hashlib.md5(f"{query_text}_{time.time()}".encode()).hexdigest(),
            'query_text': query_text,
            'query_embedding': query_embedding,
            'execution_time_ms': int(execution_time),
            'result_count': result_count,
            'top_similarity_score': top_score,
            'user_id': 'system',  # In production, get from auth context
            'facility_filter': filters.get('facilities', [None])[0] if filters and filters.get('facilities') else None,
            'query_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Async insert to analytics table (don't block main query)
        try:
            analytics_table_id = f"{self.project_id}.{self.dataset_id}.query_analytics"
            self.client.insert_rows_json(analytics_table_id, [analytics_row])
        except Exception as e:
            logger.error(f"Analytics logging failed: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        
        metrics = self.performance_metrics.copy()
        
        if metrics['queries_executed'] > 0:
            metrics['avg_query_time_ms'] = metrics['total_query_time'] / metrics['queries_executed']
            metrics['cache_hit_rate'] = metrics['cache_hits'] / metrics['queries_executed']
        else:
            metrics['avg_query_time_ms'] = 0
            metrics['cache_hit_rate'] = 0
        
        return metrics
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        
        try:
            # Get document count and statistics
            stats_query = f"""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(DISTINCT document_id) as total_documents,
                AVG(quality_score) as avg_quality_score,
                AVG(technical_complexity) as avg_complexity,
                COUNT(DISTINCT document_type) as unique_doc_types,
                COUNT(DISTINCT facility_code) as unique_facilities
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings_optimized`
            """
            
            result = list(self.client.query(stats_query).result())[0]
            
            # Get document type distribution
            type_dist_query = f"""
            SELECT document_type, COUNT(*) as count
            FROM `{self.project_id}.{self.dataset_id}.document_embeddings_optimized`
            GROUP BY document_type
            ORDER BY count DESC
            """
            
            type_distribution = {
                row.document_type: row.count 
                for row in self.client.query(type_dist_query).result()
            }
            
            return {
                'total_chunks': result.total_chunks,
                'total_documents': result.total_documents,
                'avg_quality_score': float(result.avg_quality_score) if result.avg_quality_score else 0,
                'avg_complexity': float(result.avg_complexity) if result.avg_complexity else 0,
                'unique_doc_types': result.unique_doc_types,
                'unique_facilities': result.unique_facilities,
                'document_type_distribution': type_distribution,
                'performance_metrics': self.get_performance_metrics()
            }
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {'error': str(e)}

def main():
    """Demonstration of the optimized manufacturing RAG pipeline"""
    
    # Configuration
    PROJECT_ID = "your-gcp-project"  # Replace with actual project
    DATASET_ID = "manufacturing_rag_demo"
    
    # Initialize pipeline
    rag_pipeline = OptimizedManufacturingRAG(PROJECT_ID, DATASET_ID)
    
    # Setup schema
    print("🏗️ Setting up optimized BigQuery schema...")
    rag_pipeline.setup_optimized_schema()
    
    # Test search functionality
    print("🔍 Testing search functionality...")
    
    test_queries = [
        "How to perform daily maintenance on ion implanter equipment?",
        "Safety procedures for chemical vapor deposition process",
        "Quality control checklist for semiconductor wafer inspection"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = rag_pipeline.search_manufacturing_documents(
            query, 
            k=3,
            filters={'safety_levels': ['medium', 'high']},
            similarity_threshold=0.5
        )
        
        for i, result in enumerate(results, 1):
            print(f"  Result {i}: {result['similarity_score']:.3f} - {result['chunk_text'][:100]}...")
    
    # Show performance metrics
    print("\n📊 Performance Metrics:")
    metrics = rag_pipeline.get_performance_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()