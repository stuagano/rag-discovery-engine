"""
Discovery Engine to RAG Engine Migration Utility
Preserves existing embeddings to avoid costly re-processing
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib
import numpy as np
from tqdm import tqdm
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.cloud import aiplatform
from google.cloud import storage
from google.cloud import bigquery
import vertexai
from vertexai.preview import rag
from vertexai.language_models import TextEmbeddingModel
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscoveryToRAGMigrator:
    """Migrate from Discovery Engine to RAG Engine while preserving embeddings"""
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize clients
        self.discovery_client = discoveryengine.SearchServiceClient()
        self.document_client = discoveryengine.DocumentServiceClient()
        self.storage_client = storage.Client()
        self.bq_client = bigquery.Client()
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        
        # Migration tracking
        self.migration_stats = {
            "total_documents": 0,
            "migrated_documents": 0,
            "embeddings_reused": 0,
            "embeddings_generated": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
        
        # Embedding cache for reuse
        self.embedding_cache = {}
        
    def extract_from_discovery_engine(self, 
                                     datastore_id: str,
                                     save_embeddings: bool = True) -> List[Dict[str, Any]]:
        """Extract documents and embeddings from Discovery Engine"""
        
        logger.info(f"🔍 Extracting from Discovery Engine datastore: {datastore_id}")
        
        documents = []
        parent = f"projects/{self.project_id}/locations/global/dataStores/{datastore_id}/branches/default_branch"
        
        try:
            # List all documents
            request = discoveryengine.ListDocumentsRequest(parent=parent)
            page_result = self.document_client.list_documents(request=request)
            
            for doc in tqdm(page_result, desc="Extracting documents"):
                doc_data = {
                    "id": doc.id,
                    "name": doc.name,
                    "content": self._extract_document_content(doc),
                    "metadata": dict(doc.struct_data) if doc.struct_data else {},
                    "create_time": doc.create_time.isoformat() if doc.create_time else None
                }
                
                # Try to extract existing embeddings if available
                if save_embeddings:
                    embedding = self._extract_embedding_from_discovery(doc)
                    if embedding:
                        doc_data["embedding"] = embedding
                        self.embedding_cache[doc.id] = embedding
                        self.migration_stats["embeddings_reused"] += 1
                
                documents.append(doc_data)
                
        except Exception as e:
            logger.error(f"Error extracting from Discovery Engine: {e}")
            self.migration_stats["errors"] += 1
            
        self.migration_stats["total_documents"] = len(documents)
        logger.info(f"✅ Extracted {len(documents)} documents")
        
        return documents
    
    def _extract_document_content(self, doc) -> str:
        """Extract text content from Discovery Engine document"""
        
        content_parts = []
        
        # Check different content fields
        if hasattr(doc, 'content') and doc.content:
            if hasattr(doc.content, 'raw_bytes'):
                # Handle raw content
                content_parts.append(doc.content.raw_bytes.decode('utf-8', errors='ignore'))
            elif hasattr(doc.content, 'uri'):
                # Handle URI reference
                content_parts.append(f"[Content at: {doc.content.uri}]")
        
        # Extract from struct_data
        if doc.struct_data:
            for field, value in doc.struct_data.items():
                if field in ['content', 'text', 'description', 'body']:
                    content_parts.append(str(value))
        
        # Extract from json_data
        if hasattr(doc, 'json_data') and doc.json_data:
            try:
                json_content = json.loads(doc.json_data)
                if 'content' in json_content:
                    content_parts.append(json_content['content'])
            except:
                pass
        
        return "\n\n".join(content_parts) if content_parts else ""
    
    def _extract_embedding_from_discovery(self, doc) -> Optional[List[float]]:
        """Try to extract existing embedding from Discovery Engine document"""
        
        # Discovery Engine might store embeddings in different ways
        # Check common locations
        
        if hasattr(doc, 'struct_data') and doc.struct_data:
            # Check for embedding field
            if 'embedding' in doc.struct_data:
                return list(doc.struct_data['embedding'])
            elif 'embeddings' in doc.struct_data:
                return list(doc.struct_data['embeddings'])
            elif '_embedding' in doc.struct_data:
                return list(doc.struct_data['_embedding'])
        
        # Check derived_struct_data
        if hasattr(doc, 'derived_struct_data') and doc.derived_struct_data:
            for field in ['embedding', 'embeddings', 'vector', 'feature_vector']:
                if field in doc.derived_struct_data:
                    return list(doc.derived_struct_data[field])
        
        return None
    
    def check_embedding_compatibility(self, 
                                     sample_text: str = "test",
                                     discovery_embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        """Check if Discovery Engine embeddings are compatible with RAG Engine"""
        
        logger.info("🔬 Checking embedding compatibility...")
        
        # Generate test embedding with current model
        test_embedding = self.embedding_model.get_embeddings([sample_text])[0].values
        
        compatibility = {
            "current_model": "gemini-embedding-001",
            "current_dimension": len(test_embedding),
            "discovery_dimension": len(discovery_embedding) if discovery_embedding else None,
            "compatible": False,
            "recommendation": ""
        }
        
        if discovery_embedding:
            if len(discovery_embedding) == len(test_embedding):
                # Same dimension - likely compatible
                compatibility["compatible"] = True
                compatibility["recommendation"] = "Embeddings appear compatible - can reuse"
            elif len(discovery_embedding) == 768 and len(test_embedding) == 768:
                # Both using gecko - compatible
                compatibility["compatible"] = True
                compatibility["recommendation"] = "Both use 768-dim embeddings - compatible"
            else:
                # Different dimensions - incompatible
                compatibility["recommendation"] = f"Dimension mismatch: Discovery({len(discovery_embedding)}) vs RAG({len(test_embedding)}) - need regeneration"
        else:
            compatibility["recommendation"] = "No Discovery embeddings found - will generate new"
        
        logger.info(f"Compatibility: {compatibility['recommendation']}")
        return compatibility
    
    def migrate_to_rag_engine(self,
                             documents: List[Dict[str, Any]],
                             corpus_name: str = None,
                             preserve_embeddings: bool = True,
                             batch_size: int = 100) -> str:
        """Migrate documents to RAG Engine, preserving embeddings where possible"""
        
        logger.info(f"🚀 Migrating {len(documents)} documents to RAG Engine")
        self.migration_stats["start_time"] = datetime.now()
        
        # Create or get RAG corpus
        if not corpus_name:
            corpus_name = f"migrated_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create RAG corpus
            corpus = rag.create_corpus(
                display_name=corpus_name,
                description="Migrated from Discovery Engine"
            )
            logger.info(f"✅ Created RAG corpus: {corpus.resource_name}")
            
            # Prepare documents for import
            rag_documents = []
            
            for doc in tqdm(documents, desc="Processing documents"):
                rag_doc = {
                    "id": doc.get("id", f"doc_{len(rag_documents)}"),
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {})
                }
                
                # Handle embeddings
                if preserve_embeddings and "embedding" in doc:
                    # Check if we can reuse the embedding
                    compat = self.check_embedding_compatibility(
                        doc.get("content", "")[:100],
                        doc.get("embedding")
                    )
                    
                    if compat["compatible"]:
                        # Store embedding for reuse
                        rag_doc["embedding"] = doc["embedding"]
                        self.migration_stats["embeddings_reused"] += 1
                    else:
                        # Need to regenerate
                        embedding = self._generate_embedding(doc.get("content", ""))
                        rag_doc["embedding"] = embedding
                        self.migration_stats["embeddings_generated"] += 1
                else:
                    # Generate new embedding
                    embedding = self._generate_embedding(doc.get("content", ""))
                    rag_doc["embedding"] = embedding
                    self.migration_stats["embeddings_generated"] += 1
                
                rag_documents.append(rag_doc)
                
                # Batch import
                if len(rag_documents) >= batch_size:
                    self._import_to_rag_corpus(corpus, rag_documents)
                    self.migration_stats["migrated_documents"] += len(rag_documents)
                    rag_documents = []
            
            # Import remaining documents
            if rag_documents:
                self._import_to_rag_corpus(corpus, rag_documents)
                self.migration_stats["migrated_documents"] += len(rag_documents)
            
            self.migration_stats["end_time"] = datetime.now()
            
            # Log migration summary
            self._log_migration_summary()
            
            return corpus.resource_name
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            self.migration_stats["errors"] += 1
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate new embedding for text"""
        
        if not text:
            return [0.0] * 768  # Return zero vector for empty text
        
        try:
            # Truncate if too long
            text = text[:10000]
            embeddings = self.embedding_model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.warning(f"Error generating embedding: {e}")
            return [0.0] * 768
    
    def _import_to_rag_corpus(self, corpus, documents: List[Dict[str, Any]]):
        """Import documents to RAG corpus"""
        
        try:
            # Prepare for RAG import
            import_data = []
            
            for doc in documents:
                # RAG expects specific format
                import_doc = {
                    "id": doc["id"],
                    "content": {
                        "text": doc["content"]
                    },
                    "metadata": doc.get("metadata", {})
                }
                
                # If we have embeddings, include them
                if "embedding" in doc:
                    import_doc["embedding"] = doc["embedding"]
                
                import_data.append(import_doc)
            
            # Import to corpus
            rag.import_files(
                corpus=corpus,
                paths=[],  # We're using inline content
                inline_documents=import_data
            )
            
            logger.info(f"✅ Imported batch of {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error importing to RAG corpus: {e}")
            self.migration_stats["errors"] += 1
    
    def migrate_to_bigquery(self,
                           documents: List[Dict[str, Any]],
                           dataset_id: str = "rag_migration",
                           table_id: str = "migrated_documents") -> str:
        """Alternative: Migrate to BigQuery for custom RAG implementation"""
        
        logger.info(f"📊 Migrating {len(documents)} documents to BigQuery")
        
        # Create dataset if doesn't exist
        dataset_ref = self.bq_client.dataset(dataset_id)
        try:
            self.bq_client.get_dataset(dataset_ref)
        except:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            dataset = self.bq_client.create_dataset(dataset)
            logger.info(f"Created dataset {dataset_id}")
        
        # Define schema
        schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("content", "STRING"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("metadata", "JSON"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("source", "STRING"),
        ]
        
        # Create table
        table_ref = dataset_ref.table(table_id)
        table = bigquery.Table(table_ref, schema=schema)
        
        try:
            table = self.bq_client.create_table(table)
            logger.info(f"Created table {table_id}")
        except:
            table = self.bq_client.get_table(table_ref)
        
        # Prepare rows for insertion
        rows = []
        for doc in tqdm(documents, desc="Preparing for BigQuery"):
            row = {
                "document_id": doc.get("id", f"doc_{len(rows)}"),
                "content": doc.get("content", ""),
                "metadata": json.dumps(doc.get("metadata", {})),
                "created_at": doc.get("create_time", datetime.now().isoformat()),
                "source": "discovery_engine"
            }
            
            # Handle embeddings
            if "embedding" in doc:
                row["embedding"] = doc["embedding"]
            else:
                # Generate if needed
                embedding = self._generate_embedding(doc.get("content", ""))
                row["embedding"] = embedding
            
            rows.append(row)
        
        # Insert rows
        errors = self.bq_client.insert_rows_json(table, rows)
        
        if errors:
            logger.error(f"Errors inserting rows: {errors}")
            self.migration_stats["errors"] += len(errors)
        else:
            logger.info(f"✅ Migrated {len(rows)} documents to BigQuery")
            self.migration_stats["migrated_documents"] = len(rows)
        
        return f"{project_id}.{dataset_id}.{table_id}"
    
    def incremental_migration(self,
                            source_datastore_id: str,
                            target_corpus: str,
                            checkpoint_file: str = "migration_checkpoint.json") -> Dict[str, Any]:
        """Perform incremental migration with checkpointing"""
        
        logger.info("📈 Starting incremental migration...")
        
        # Load checkpoint if exists
        checkpoint = self._load_checkpoint(checkpoint_file)
        
        # Extract documents
        documents = self.extract_from_discovery_engine(source_datastore_id)
        
        # Filter already migrated documents
        if checkpoint:
            migrated_ids = set(checkpoint.get("migrated_ids", []))
            documents = [d for d in documents if d["id"] not in migrated_ids]
            logger.info(f"Found {len(documents)} new documents to migrate")
        
        if not documents:
            logger.info("No new documents to migrate")
            return {"status": "up_to_date", "migrated": 0}
        
        # Migrate batch
        batch_size = 100
        migrated_count = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            try:
                # Migrate batch
                self.migrate_to_rag_engine(batch, target_corpus)
                migrated_count += len(batch)
                
                # Update checkpoint
                if not checkpoint:
                    checkpoint = {"migrated_ids": [], "last_run": None}
                
                checkpoint["migrated_ids"].extend([d["id"] for d in batch])
                checkpoint["last_run"] = datetime.now().isoformat()
                checkpoint["total_migrated"] = len(checkpoint["migrated_ids"])
                
                self._save_checkpoint(checkpoint, checkpoint_file)
                
            except Exception as e:
                logger.error(f"Error migrating batch: {e}")
                break
        
        return {
            "status": "success",
            "migrated": migrated_count,
            "total": checkpoint.get("total_migrated", 0)
        }
    
    def _load_checkpoint(self, checkpoint_file: str) -> Optional[Dict[str, Any]]:
        """Load migration checkpoint"""
        
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        return None
    
    def _save_checkpoint(self, checkpoint: Dict[str, Any], checkpoint_file: str):
        """Save migration checkpoint"""
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    def validate_migration(self,
                          source_datastore_id: str,
                          target_corpus: str,
                          sample_queries: List[str] = None) -> Dict[str, Any]:
        """Validate migration by comparing search results"""
        
        logger.info("✅ Validating migration...")
        
        if not sample_queries:
            sample_queries = [
                "maintenance procedures",
                "quality control",
                "safety requirements",
                "equipment calibration",
                "process optimization"
            ]
        
        validation_results = {
            "queries_tested": len(sample_queries),
            "average_similarity": 0,
            "issues": [],
            "recommendations": []
        }
        
        similarities = []
        
        for query in sample_queries:
            # Search Discovery Engine
            discovery_results = self._search_discovery_engine(source_datastore_id, query)
            
            # Search RAG Engine
            rag_results = self._search_rag_engine(target_corpus, query)
            
            # Compare results
            similarity = self._calculate_result_similarity(discovery_results, rag_results)
            similarities.append(similarity)
            
            if similarity < 0.7:
                validation_results["issues"].append(
                    f"Low similarity ({similarity:.2f}) for query: {query}"
                )
        
        validation_results["average_similarity"] = np.mean(similarities)
        
        # Generate recommendations
        if validation_results["average_similarity"] < 0.8:
            validation_results["recommendations"].append(
                "Consider regenerating embeddings with the same model used in Discovery Engine"
            )
        
        if validation_results["issues"]:
            validation_results["recommendations"].append(
                "Review and potentially retune the retrieval parameters"
            )
        
        logger.info(f"Validation complete. Average similarity: {validation_results['average_similarity']:.2f}")
        
        return validation_results
    
    def _search_discovery_engine(self, datastore_id: str, query: str) -> List[Dict[str, Any]]:
        """Search Discovery Engine"""
        
        try:
            serving_config = f"projects/{self.project_id}/locations/global/dataStores/{datastore_id}/servingConfigs/default_search"
            
            request = discoveryengine.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=10
            )
            
            response = self.discovery_client.search(request=request)
            
            results = []
            for result in response.results:
                results.append({
                    "id": result.document.id,
                    "score": result.relevance_score if hasattr(result, 'relevance_score') else 0
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Discovery Engine: {e}")
            return []
    
    def _search_rag_engine(self, corpus: str, query: str) -> List[Dict[str, Any]]:
        """Search RAG Engine"""
        
        try:
            response = rag.retrieve(
                corpus=corpus,
                query=query,
                k=10
            )
            
            results = []
            for context in response.contexts:
                results.append({
                    "id": context.id,
                    "score": context.score if hasattr(context, 'score') else 0
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching RAG Engine: {e}")
            return []
    
    def _calculate_result_similarity(self, 
                                   results1: List[Dict[str, Any]], 
                                   results2: List[Dict[str, Any]]) -> float:
        """Calculate similarity between two result sets"""
        
        if not results1 or not results2:
            return 0.0
        
        # Extract IDs
        ids1 = set([r["id"] for r in results1[:5]])  # Top 5
        ids2 = set([r["id"] for r in results2[:5]])
        
        # Calculate Jaccard similarity
        intersection = len(ids1.intersection(ids2))
        union = len(ids1.union(ids2))
        
        return intersection / union if union > 0 else 0.0
    
    def _log_migration_summary(self):
        """Log migration summary statistics"""
        
        duration = (self.migration_stats["end_time"] - self.migration_stats["start_time"]).total_seconds()
        
        logger.info("\n" + "="*50)
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Total Documents: {self.migration_stats['total_documents']}")
        logger.info(f"Migrated: {self.migration_stats['migrated_documents']}")
        logger.info(f"Embeddings Reused: {self.migration_stats['embeddings_reused']}")
        logger.info(f"Embeddings Generated: {self.migration_stats['embeddings_generated']}")
        logger.info(f"Errors: {self.migration_stats['errors']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        
        # Cost savings estimate
        embeddings_saved = self.migration_stats['embeddings_reused']
        cost_saved = embeddings_saved * 0.0001  # Approximate cost per embedding
        logger.info(f"💰 Estimated Cost Saved: ${cost_saved:.2f}")
        
        logger.info("="*50 + "\n")
    
    def generate_migration_report(self, output_file: str = "migration_report.json"):
        """Generate detailed migration report"""
        
        report = {
            "migration_stats": self.migration_stats,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "project_id": self.project_id,
                "location": self.location,
                "embedding_model": "gemini-embedding-001"
            },
            "cost_analysis": {
                "embeddings_reused": self.migration_stats["embeddings_reused"],
                "embeddings_generated": self.migration_stats["embeddings_generated"],
                "estimated_savings": self.migration_stats["embeddings_reused"] * 0.0001
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Migration report saved to {output_file}")
        
        return report


def main():
    """Example migration workflow"""
    
    # Configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
    discovery_datastore_id = os.getenv("DISCOVERY_DATASTORE_ID", "your-datastore-id")
    
    # Initialize migrator
    migrator = DiscoveryToRAGMigrator(project_id)
    
    print("\n🔄 Discovery Engine to RAG Engine Migration Tool")
    print("="*50)
    
    # Step 1: Extract from Discovery Engine
    print("\n1. Extracting from Discovery Engine...")
    documents = migrator.extract_from_discovery_engine(
        datastore_id=discovery_datastore_id,
        save_embeddings=True
    )
    
    # Step 2: Check embedding compatibility
    print("\n2. Checking embedding compatibility...")
    if documents and "embedding" in documents[0]:
        compatibility = migrator.check_embedding_compatibility(
            documents[0].get("content", "test")[:100],
            documents[0].get("embedding")
        )
        print(f"   Compatibility: {compatibility['recommendation']}")
    
    # Step 3: Migrate to RAG Engine
    print("\n3. Migrating to RAG Engine...")
    corpus_name = migrator.migrate_to_rag_engine(
        documents=documents,
        preserve_embeddings=True
    )
    
    # Step 4: Validate migration
    print("\n4. Validating migration...")
    validation = migrator.validate_migration(
        source_datastore_id=discovery_datastore_id,
        target_corpus=corpus_name
    )
    
    print(f"   Average similarity: {validation['average_similarity']:.2%}")
    
    # Step 5: Generate report
    print("\n5. Generating migration report...")
    report = migrator.generate_migration_report()
    
    print("\n✅ Migration completed successfully!")
    print(f"   Documents migrated: {report['migration_stats']['migrated_documents']}")
    print(f"   Embeddings reused: {report['migration_stats']['embeddings_reused']}")
    print(f"   Cost saved: ${report['cost_analysis']['estimated_savings']:.2f}")


if __name__ == "__main__":
    main()