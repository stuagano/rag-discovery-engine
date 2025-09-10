"""
Discovery Engine to BigQuery RAG Migration Pipeline
Automated migration system with validation and rollback capabilities
"""

from google.cloud import discoveryengine
from google.cloud import bigquery
from google.cloud import storage
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import statistics
from dataclasses import dataclass
from enum import Enum

from bigquery_rag_pipeline import OptimizedManufacturingRAG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationStrategy(Enum):
    DIRECT_TRANSFER = "direct_transfer"
    BATCH_REPROCESSING = "batch_reprocessing"  
    STREAMING_MIGRATION = "streaming_migration"

@dataclass
class MigrationCheckpoint:
    """Migration checkpoint for rollback capability"""
    checkpoint_id: str
    timestamp: datetime
    store_info: Dict[str, Any]
    migration_state: Dict[str, Any]
    backup_location: str

class DiscoveryEngineAssessment:
    """Comprehensive assessment of existing Discovery Engine stores"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        try:
            self.discovery_client = discoveryengine.DiscoveryServiceClient()
        except Exception as e:
            logger.error(f"Failed to initialize Discovery Engine client: {e}")
            self.discovery_client = None
            
        self.storage_client = storage.Client(project=project_id)
    
    def inventory_discovery_stores(self) -> Dict[str, Any]:
        """Comprehensive inventory of all Discovery Engine stores"""
        
        logger.info("Starting Discovery Engine inventory assessment...")
        
        stores_inventory = []
        locations = ['us-central1', 'us-east1', 'us-west1', 'europe-west1', 'asia-southeast1']
        
        # For demo purposes, create sample store inventory
        # In production, replace with actual Discovery Engine API calls
        sample_stores = [
            {
                'store_id': 'projects/manufacturing-project/locations/us-central1/dataStores/semiconductor-manuals',
                'display_name': 'Semiconductor Equipment Manuals',
                'location': 'us-central1',
                'document_count': 1500,
                'total_size_mb': 2800,
                'document_types': ['maintenance_manual', 'procedure', 'safety_guide'],
                'last_update': '2024-12-15T10:30:00Z',
                'content_config': {
                    'data_type': 'UNSTRUCTURED',
                    'solution_type': 'SOLUTION_TYPE_SEARCH'
                },
                'custom_schema': True,
                'api_usage_monthly': 25000
            },
            {
                'store_id': 'projects/manufacturing-project/locations/us-central1/dataStores/quality-control-docs',
                'display_name': 'Quality Control Documentation', 
                'location': 'us-central1',
                'document_count': 800,
                'total_size_mb': 1200,
                'document_types': ['quality_manual', 'specification', 'test_procedure'],
                'last_update': '2024-12-10T14:22:00Z',
                'content_config': {
                    'data_type': 'UNSTRUCTURED',
                    'solution_type': 'SOLUTION_TYPE_SEARCH'
                },
                'custom_schema': False,
                'api_usage_monthly': 12000
            },
            {
                'store_id': 'projects/manufacturing-project/locations/us-east1/dataStores/automotive-assembly-guides',
                'display_name': 'Automotive Assembly Guides',
                'location': 'us-east1', 
                'document_count': 2200,
                'total_size_mb': 4500,
                'document_types': ['assembly_guide', 'safety_protocol', 'maintenance'],
                'last_update': '2024-12-12T09:15:00Z',
                'content_config': {
                    'data_type': 'UNSTRUCTURED',
                    'solution_type': 'SOLUTION_TYPE_SEARCH'
                },
                'custom_schema': True,
                'api_usage_monthly': 35000
            }
        ]
        
        # Analyze each store for migration planning
        for store_data in sample_stores:
            store_analysis = self._analyze_store_for_migration(store_data)
            stores_inventory.append(store_analysis)
            
            logger.info(f"Analyzed store: {store_analysis['display_name']} - "
                       f"Complexity: {store_analysis['migration_complexity']}")
        
        # Generate comprehensive migration plan
        migration_plan = self._generate_comprehensive_migration_plan(stores_inventory)
        
        return migration_plan
    
    def _analyze_store_for_migration(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual store for migration complexity and requirements"""
        
        # Base store information
        store_analysis = store_data.copy()
        
        # Calculate migration complexity
        complexity_factors = {
            'document_count': store_data['document_count'],
            'size_mb': store_data['total_size_mb'],
            'type_diversity': len(store_data['document_types']),
            'custom_schema': store_data.get('custom_schema', False),
            'api_usage': store_data.get('api_usage_monthly', 0)
        }
        
        migration_complexity = self._calculate_migration_complexity(complexity_factors)
        store_analysis['migration_complexity'] = migration_complexity
        
        # Estimate migration time and resources
        time_estimates = self._estimate_migration_time(complexity_factors, migration_complexity)
        store_analysis['estimated_migration_time'] = time_estimates
        
        # Identify migration risks
        risks = self._identify_migration_risks(store_data, migration_complexity)
        store_analysis['migration_risks'] = risks
        
        # Recommend migration strategy
        strategy = self._recommend_migration_strategy(complexity_factors, migration_complexity)
        store_analysis['recommended_strategy'] = strategy
        
        return store_analysis
    
    def _calculate_migration_complexity(self, factors: Dict[str, Any]) -> str:
        """Calculate migration complexity based on various factors"""
        
        complexity_score = 0
        
        # Document count factor (0-3 points)
        doc_count = factors['document_count']
        if doc_count > 10000:
            complexity_score += 3
        elif doc_count > 5000:
            complexity_score += 2
        elif doc_count > 1000:
            complexity_score += 1
        
        # Size factor (0-3 points)
        size_mb = factors['size_mb']
        if size_mb > 10000:  # > 10GB
            complexity_score += 3
        elif size_mb > 5000:   # > 5GB
            complexity_score += 2
        elif size_mb > 1000:   # > 1GB
            complexity_score += 1
        
        # Document type diversity (0-2 points)
        type_count = factors['type_diversity']
        if type_count > 5:
            complexity_score += 2
        elif type_count > 3:
            complexity_score += 1
        
        # Custom schema complexity (0-2 points)
        if factors['custom_schema']:
            complexity_score += 2
        
        # API usage intensity (0-2 points)
        api_usage = factors['api_usage']
        if api_usage > 50000:
            complexity_score += 2
        elif api_usage > 20000:
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score >= 10:
            return 'very_high'
        elif complexity_score >= 7:
            return 'high'
        elif complexity_score >= 4:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_migration_time(self, factors: Dict[str, Any], complexity: str) -> Dict[str, Any]:
        """Estimate migration time based on complexity and factors"""
        
        base_times = {
            'low': {'setup': 2, 'migration': 4, 'validation': 2},      # hours
            'medium': {'setup': 4, 'migration': 12, 'validation': 4},  # hours  
            'high': {'setup': 8, 'migration': 24, 'validation': 8},    # hours
            'very_high': {'setup': 12, 'migration': 48, 'validation': 12}  # hours
        }
        
        times = base_times[complexity].copy()
        
        # Adjust based on document count
        doc_count = factors['document_count']
        if doc_count > 5000:
            times['migration'] *= 1.5
        elif doc_count > 10000:
            times['migration'] *= 2.0
        
        # Adjust based on custom schema
        if factors['custom_schema']:
            times['setup'] *= 1.5
            times['validation'] *= 1.3
        
        # Calculate total time
        total_hours = sum(times.values())
        
        return {
            'setup_hours': times['setup'],
            'migration_hours': times['migration'],
            'validation_hours': times['validation'],
            'total_hours': total_hours,
            'estimated_days': total_hours / 8,  # 8-hour work days
            'recommended_parallel_workers': min(10, max(2, doc_count // 1000))
        }
    
    def _identify_migration_risks(self, store_data: Dict[str, Any], complexity: str) -> List[Dict[str, Any]]:
        """Identify potential migration risks and mitigation strategies"""
        
        risks = []
        
        # Data loss risk
        if store_data['document_count'] > 5000:
            risks.append({
                'type': 'data_loss',
                'severity': 'high',
                'description': 'Large document count increases risk of data loss during migration',
                'mitigation': 'Implement comprehensive validation and backup procedures'
            })
        
        # Performance degradation risk
        if store_data['api_usage_monthly'] > 30000:
            risks.append({
                'type': 'performance_impact',
                'severity': 'medium',
                'description': 'High API usage may cause performance impact during migration',
                'mitigation': 'Schedule migration during low-usage periods, implement gradual cutover'
            })
        
        # Custom schema compatibility risk
        if store_data.get('custom_schema'):
            risks.append({
                'type': 'schema_compatibility',
                'severity': 'medium',
                'description': 'Custom schema may not map directly to BigQuery structure',
                'mitigation': 'Design custom mapping logic and perform extensive testing'
            })
        
        # Embedding model compatibility risk
        if complexity in ['high', 'very_high']:
            risks.append({
                'type': 'embedding_compatibility',
                'severity': 'low',
                'description': 'Different embedding models may affect search relevance',
                'mitigation': 'Compare search results before and after migration, retune if necessary'
            })
        
        return risks
    
    def _recommend_migration_strategy(self, factors: Dict[str, Any], complexity: str) -> str:
        """Recommend optimal migration strategy based on analysis"""
        
        doc_count = factors['document_count']
        size_mb = factors['size_mb']
        custom_schema = factors['custom_schema']
        
        # Direct transfer for simple, small stores
        if complexity == 'low' and doc_count < 1000 and not custom_schema:
            return MigrationStrategy.DIRECT_TRANSFER.value
        
        # Streaming migration for very large stores
        elif complexity == 'very_high' or doc_count > 10000 or size_mb > 10000:
            return MigrationStrategy.STREAMING_MIGRATION.value
        
        # Batch reprocessing for most cases
        else:
            return MigrationStrategy.BATCH_REPROCESSING.value
    
    def _generate_comprehensive_migration_plan(self, stores_inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive migration plan with prioritization and scheduling"""
        
        # Calculate totals
        total_stores = len(stores_inventory)
        total_documents = sum(store['document_count'] for store in stores_inventory)
        total_size_gb = sum(store['total_size_mb'] for store in stores_inventory) / 1024
        total_estimated_hours = sum(store['estimated_migration_time']['total_hours'] for store in stores_inventory)
        
        # Prioritize stores for migration order
        prioritized_stores = self._prioritize_migration_order(stores_inventory)
        
        # Create migration waves
        migration_waves = self._create_migration_waves(prioritized_stores)
        
        # Resource requirements
        resource_requirements = self._calculate_resource_requirements(stores_inventory)
        
        # Risk assessment summary
        risk_summary = self._summarize_migration_risks(stores_inventory)
        
        migration_plan = {
            'summary': {
                'total_stores': total_stores,
                'total_documents': total_documents,
                'total_size_gb': round(total_size_gb, 2),
                'estimated_total_hours': round(total_estimated_hours, 1),
                'estimated_weeks': round(total_estimated_hours / 40, 1)  # 40-hour work weeks
            },
            'stores_inventory': stores_inventory,
            'prioritized_migration_order': prioritized_stores,
            'migration_waves': migration_waves,
            'resource_requirements': resource_requirements,
            'risk_summary': risk_summary,
            'recommendations': self._generate_migration_recommendations(stores_inventory)
        }
        
        return migration_plan

    def _prioritize_migration_order(self, stores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize stores for migration based on complexity, risk, and business value"""
        
        def migration_priority_score(store):
            score = 0
            
            # Lower complexity = higher priority (easier wins first)
            complexity_scores = {'low': 4, 'medium': 3, 'high': 2, 'very_high': 1}
            score += complexity_scores.get(store['migration_complexity'], 1)
            
            # Higher API usage = higher priority (more business impact)
            api_usage = store.get('api_usage_monthly', 0)
            if api_usage > 50000:
                score += 3
            elif api_usage > 20000:
                score += 2
            elif api_usage > 10000:
                score += 1
                
            # Recent updates = higher priority (actively used)
            # Simplified: assume all are recent for demo
            score += 1
            
            return score
        
        return sorted(stores, key=migration_priority_score, reverse=True)
    
    def _create_migration_waves(self, prioritized_stores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create migration waves for phased rollout"""
        
        waves = []
        stores_per_wave = 2  # Process 2 stores per wave for manageable batches
        
        for i in range(0, len(prioritized_stores), stores_per_wave):
            wave_stores = prioritized_stores[i:i + stores_per_wave]
            
            wave = {
                'wave_number': len(waves) + 1,
                'stores': wave_stores,
                'estimated_duration_days': max(store['estimated_migration_time']['estimated_days'] 
                                             for store in wave_stores),
                'total_documents': sum(store['document_count'] for store in wave_stores),
                'complexity_levels': [store['migration_complexity'] for store in wave_stores]
            }
            
            waves.append(wave)
        
        return waves
    
    def _calculate_resource_requirements(self, stores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resource requirements for migration project"""
        
        total_hours = sum(store['estimated_migration_time']['total_hours'] for store in stores)
        max_parallel_workers = max(store['estimated_migration_time']['recommended_parallel_workers'] 
                                 for store in stores)
        
        # Estimate costs
        engineer_hourly_rate = 100  # $100/hour
        gcp_compute_cost_per_hour = 2  # $2/hour for compute resources
        
        engineering_cost = total_hours * engineer_hourly_rate
        gcp_cost = total_hours * gcp_compute_cost_per_hour * max_parallel_workers
        
        return {
            'total_engineering_hours': round(total_hours, 1),
            'recommended_team_size': min(4, max(2, len(stores))),
            'max_parallel_workers': max_parallel_workers,
            'estimated_engineering_cost': engineering_cost,
            'estimated_gcp_compute_cost': gcp_cost,
            'total_estimated_cost': engineering_cost + gcp_cost,
            'peak_memory_gb': max_parallel_workers * 4,  # 4GB per worker
            'storage_requirements_gb': sum(store['total_size_mb'] for store in stores) / 1024 * 2  # 2x for backup
        }

    def _summarize_migration_risks(self, stores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize risks across all stores"""
        
        all_risks = []
        for store in stores:
            all_risks.extend(store.get('migration_risks', []))
        
        risk_counts = {}
        for risk in all_risks:
            risk_type = risk['type']
            severity = risk['severity']
            
            if risk_type not in risk_counts:
                risk_counts[risk_type] = {'high': 0, 'medium': 0, 'low': 0}
            
            risk_counts[risk_type][severity] += 1
        
        return {
            'total_risks': len(all_risks),
            'risk_breakdown': risk_counts,
            'high_severity_count': sum(1 for risk in all_risks if risk['severity'] == 'high'),
            'critical_risks': [risk for risk in all_risks if risk['severity'] == 'high']
        }
    
    def _generate_migration_recommendations(self, stores: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations for the migration project"""
        
        recommendations = []
        
        # General recommendations
        recommendations.append("Start with pilot migration of 1-2 low-complexity stores to validate process")
        recommendations.append("Implement comprehensive backup and rollback procedures before beginning")
        recommendations.append("Schedule migrations during low-usage periods to minimize impact")
        
        # Complexity-based recommendations
        high_complexity_stores = [s for s in stores if s['migration_complexity'] in ['high', 'very_high']]
        if high_complexity_stores:
            recommendations.append(f"Consider additional testing phase for {len(high_complexity_stores)} high-complexity stores")
        
        # Size-based recommendations  
        large_stores = [s for s in stores if s['total_size_mb'] > 5000]
        if large_stores:
            recommendations.append(f"Use streaming migration strategy for {len(large_stores)} large stores (>5GB)")
        
        # Custom schema recommendations
        custom_schema_stores = [s for s in stores if s.get('custom_schema')]
        if custom_schema_stores:
            recommendations.append(f"Develop custom schema mapping for {len(custom_schema_stores)} stores with custom schemas")
        
        recommendations.append("Monitor search quality metrics before and after migration")
        recommendations.append("Implement gradual traffic cutover with rollback capability")
        
        return recommendations

class AutomatedMigrationPipeline:
    """Automated migration pipeline with validation and rollback capabilities"""
    
    def __init__(self, project_id: str, target_dataset: str = "manufacturing_rag_migrated"):
        self.project_id = project_id
        self.target_dataset = target_dataset
        
        # Initialize clients
        try:
            self.discovery_client = discoveryengine.DiscoveryServiceClient()
        except Exception as e:
            logger.error(f"Discovery Engine client initialization failed: {e}")
            self.discovery_client = None
            
        self.target_rag = OptimizedManufacturingRAG(project_id, target_dataset)
        self.storage_client = storage.Client(project=project_id)
        
        # Migration tracking
        self.migration_checkpoints = {}
        self.migration_stats = {
            'total_migrations': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'total_documents_migrated': 0,
            'total_migration_time': 0
        }
    
    def execute_full_migration(self, migration_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete migration plan with validation and monitoring"""
        
        logger.info("🚀 Starting full migration execution...")
        
        migration_results = []
        plan_start_time = time.time()
        
        # Initialize target RAG system
        self.target_rag.setup_optimized_schema()
        
        # Process migration waves
        for wave in migration_plan['migration_waves']:
            logger.info(f"\n📊 Starting Migration Wave {wave['wave_number']}")
            logger.info(f"Stores in wave: {len(wave['stores'])}")
            
            wave_results = self._execute_migration_wave(wave)
            migration_results.extend(wave_results)
            
            # Validation checkpoint after each wave
            if not self._validate_wave_completion(wave, wave_results):
                logger.error(f"Wave {wave['wave_number']} validation failed!")
                # In production, implement rollback here
                break
        
        total_migration_time = time.time() - plan_start_time
        
        # Generate comprehensive migration report
        migration_report = self._generate_migration_report(
            migration_results, 
            migration_plan, 
            total_migration_time
        )
        
        return migration_report
    
    def _execute_migration_wave(self, wave: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute migration for a single wave of stores"""
        
        wave_results = []
        
        for store in wave['stores']:
            logger.info(f"\n🔄 Migrating store: {store['display_name']}")
            
            try:
                # Create migration checkpoint
                checkpoint = self._create_migration_checkpoint(store)
                
                # Select and execute migration strategy
                strategy = MigrationStrategy(store['recommended_strategy'])
                migration_result = self._execute_migration_strategy(store, strategy)
                
                # Post-migration validation
                validation_result = self._post_migration_validation(store, migration_result)
                
                # Compile results
                result = {
                    'store_info': store,
                    'strategy': strategy.value,
                    'migration_result': migration_result,
                    'validation_result': validation_result,
                    'status': 'success' if validation_result['passed'] else 'failed',
                    'checkpoint_id': checkpoint.checkpoint_id
                }
                
                if validation_result['passed']:
                    logger.info(f"✅ Successfully migrated {store['display_name']}")
                    self._finalize_migration(store, migration_result)
                else:
                    logger.error(f"❌ Migration validation failed for {store['display_name']}")
                    self._handle_migration_failure(checkpoint, validation_result)
                
                wave_results.append(result)
                
            except Exception as e:
                logger.error(f"❌ Migration failed for {store['display_name']}: {e}")
                wave_results.append({
                    'store_info': store,
                    'error': str(e),
                    'status': 'error'
                })
        
        return wave_results
    
    def _execute_migration_strategy(self, store: Dict[str, Any], strategy: MigrationStrategy) -> Dict[str, Any]:
        """Execute specific migration strategy"""
        
        if strategy == MigrationStrategy.DIRECT_TRANSFER:
            return self._direct_transfer_migration(store)
        elif strategy == MigrationStrategy.BATCH_REPROCESSING:
            return self._batch_reprocessing_migration(store)
        elif strategy == MigrationStrategy.STREAMING_MIGRATION:
            return self._streaming_migration(store)
        else:
            raise ValueError(f"Unknown migration strategy: {strategy}")
    
    def _batch_reprocessing_migration(self, store: Dict[str, Any]) -> Dict[str, Any]:
        """Batch reprocessing migration with full content optimization"""
        
        logger.info(f"Executing batch reprocessing migration for {store['display_name']}")
        
        start_time = time.time()
        
        # For demo purposes, create synthetic documents based on store metadata
        # In production, this would extract from actual Discovery Engine
        synthetic_documents = self._generate_migration_documents(store)
        
        # Process documents through optimized RAG pipeline
        processing_stats = self.target_rag.process_manufacturing_documents_batch(
            synthetic_documents,
            batch_size=50
        )
        
        migration_time = time.time() - start_time
        
        # Update migration statistics
        self.migration_stats['total_migrations'] += 1
        self.migration_stats['total_documents_migrated'] += processing_stats['processed_chunks']
        self.migration_stats['total_migration_time'] += migration_time
        
        result = {
            'strategy': MigrationStrategy.BATCH_REPROCESSING.value,
            'processing_stats': processing_stats,
            'migration_time_seconds': migration_time,
            'documents_processed': len(synthetic_documents),
            'chunks_created': processing_stats['processed_chunks'],
            'success_rate': (processing_stats['processed_chunks'] / 
                           (processing_stats['processed_chunks'] + processing_stats['failed_documents']))
                           if processing_stats['processed_chunks'] > 0 else 0
        }
        
        return result
    
    def _direct_transfer_migration(self, store: Dict[str, Any]) -> Dict[str, Any]:
        """Direct transfer migration for simple stores"""
        
        logger.info(f"Executing direct transfer migration for {store['display_name']}")
        
        # Simplified direct transfer (placeholder implementation)
        start_time = time.time()
        
        # Generate fewer documents for direct transfer
        documents = self._generate_migration_documents(store, count_multiplier=0.5)
        
        # Direct processing without heavy optimization
        processing_stats = self.target_rag.process_manufacturing_documents_batch(
            documents,
            batch_size=100  # Larger batches for direct transfer
        )
        
        migration_time = time.time() - start_time
        
        return {
            'strategy': MigrationStrategy.DIRECT_TRANSFER.value,
            'processing_stats': processing_stats,
            'migration_time_seconds': migration_time,
            'documents_processed': len(documents),
            'chunks_created': processing_stats['processed_chunks']
        }
    
    def _streaming_migration(self, store: Dict[str, Any]) -> Dict[str, Any]:
        """Streaming migration for large stores"""
        
        logger.info(f"Executing streaming migration for {store['display_name']}")
        
        start_time = time.time()
        
        # Simulate streaming processing with smaller batches
        total_documents = store['document_count']
        stream_batch_size = 20
        total_processed = 0
        
        for batch_start in range(0, min(100, total_documents), stream_batch_size):  # Limit for demo
            batch_docs = self._generate_migration_documents(
                store, 
                count_multiplier=0.1,  # Small batches
                batch_offset=batch_start
            )
            
            batch_stats = self.target_rag.process_manufacturing_documents_batch(
                batch_docs,
                batch_size=stream_batch_size
            )
            
            total_processed += batch_stats['processed_chunks']
            
            # Progress logging
            progress = min(100, (batch_start + stream_batch_size) / total_documents * 100)
            logger.info(f"  Streaming progress: {progress:.1f}%")
        
        migration_time = time.time() - start_time
        
        return {
            'strategy': MigrationStrategy.STREAMING_MIGRATION.value,
            'total_chunks_processed': total_processed,
            'migration_time_seconds': migration_time,
            'streaming_batches': total_documents // stream_batch_size
        }
    
    def _generate_migration_documents(self, store: Dict[str, Any], 
                                    count_multiplier: float = 1.0,
                                    batch_offset: int = 0) -> List[Dict[str, Any]]:
        """Generate representative documents for migration testing"""
        
        # Calculate document count
        base_count = min(50, store['document_count'])  # Limit for demo
        doc_count = int(base_count * count_multiplier)
        
        documents = []
        doc_types = store['document_types']
        
        # Manufacturing content templates based on document types
        content_templates = {
            'maintenance_manual': [
                "Daily maintenance procedure for ion implanter equipment includes checking vacuum levels, cleaning sample chamber, and calibrating beam current. Always follow safety protocols when accessing equipment internals.",
                "Weekly maintenance schedule requires comprehensive cleaning of all surfaces, replacement of consumable parts, and verification of all safety interlocks. Record all maintenance activities in equipment logbook.",
                "Monthly maintenance involves deep cleaning of vacuum chamber, replacement of ion source components, and full system calibration. This procedure requires qualified technician supervision."
            ],
            'procedure': [
                "Standard operating procedure for semiconductor wafer processing includes substrate preparation, photoresist coating, exposure, development, and inspection. Each step must be performed according to specification.",
                "Quality control procedure requires measurement of critical dimensions, defect inspection, and electrical testing. All measurements must be recorded and tracked for process control.",
                "Safety procedure for chemical handling includes proper personal protective equipment, spill response protocols, and emergency shutdown procedures. Training is required before handling chemicals."
            ],
            'safety_guide': [
                "WARNING: High voltage present during operation. Always use lockout/tagout procedures before servicing equipment. Failure to follow safety procedures may result in serious injury or death.",
                "CAUTION: Chemical vapors may be present in process area. Use appropriate respiratory protection and ensure adequate ventilation. Monitor gas detection systems continuously.",
                "Emergency response procedures include immediate evacuation, activation of fire suppression systems, and notification of emergency services. Practice emergency drills quarterly."
            ],
            'quality_manual': [
                "Quality management system requirements include document control, training records, and measurement system analysis. All quality procedures must be followed to maintain certification.",
                "Statistical process control procedures require collection of measurement data, calculation of control limits, and identification of out-of-control conditions. Immediate corrective action is required for excursions.",
                "Inspection procedures include visual examination, dimensional measurement, and functional testing. All inspection results must be documented and reviewed by quality personnel."
            ],
            'specification': [
                "Technical specification for silicon wafer requires 300mm diameter, <111> crystal orientation, and resistivity between 1-10 ohm-cm. Surface roughness must be less than 0.2 nm RMS.",
                "Process specification for photolithography requires exposure dose of 25 mJ/cm², focus offset within ±0.1 μm, and overlay accuracy better than ±10 nm. Environmental controls must maintain temperature within ±0.1°C.",
                "Equipment specification includes minimum pump-down time, ultimate vacuum level, and temperature uniformity requirements. All specifications must be verified during acceptance testing."
            ]
        }
        
        for i in range(doc_count):
            doc_type = doc_types[i % len(doc_types)]
            templates = content_templates.get(doc_type, content_templates['procedure'])
            content = templates[i % len(templates)]
            
            document = {
                'id': f"{store['store_id'].split('/')[-1]}_{batch_offset + i:04d}",
                'title': f"{doc_type.replace('_', ' ').title()} - Document {batch_offset + i + 1}",
                'content': content,
                'doc_type': doc_type,
                'source': 'discovery_engine_migration',
                'facility_code': f"fab_{(i % 3) + 1}",  # Distribute across facilities
                'metadata': {
                    'original_store': store['store_id'],
                    'migration_batch': batch_offset // 20,  # Track migration batches
                    'document_index': batch_offset + i
                }
            }
            
            documents.append(document)
        
        return documents
    
    def _create_migration_checkpoint(self, store: Dict[str, Any]) -> MigrationCheckpoint:
        """Create migration checkpoint for rollback capability"""
        
        checkpoint_id = f"checkpoint_{store['store_id'].split('/')[-1]}_{int(time.time())}"
        
        checkpoint = MigrationCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(timezone.utc),
            store_info=store,
            migration_state={'status': 'starting'},
            backup_location=f"gs://migration-backups/{checkpoint_id}/"
        )
        
        # Store checkpoint
        self.migration_checkpoints[checkpoint_id] = checkpoint
        
        logger.info(f"Created migration checkpoint: {checkpoint_id}")
        return checkpoint
    
    def _post_migration_validation(self, store: Dict[str, Any], 
                                 migration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive post-migration validation"""
        
        logger.info(f"Validating migration for {store['display_name']}...")
        
        validation_result = {
            'passed': True,
            'checks': {},
            'errors': [],
            'warnings': []
        }
        
        # Document count validation
        expected_docs = store['document_count']
        if 'processing_stats' in migration_result:
            actual_chunks = migration_result['processing_stats']['processed_chunks']
            
            # Rough estimation: assume 2-3 chunks per document on average
            estimated_docs = actual_chunks / 2.5
            count_variance = abs(expected_docs - estimated_docs) / expected_docs
            
            validation_result['checks']['document_count'] = {
                'expected_documents': expected_docs,
                'estimated_documents': round(estimated_docs),
                'actual_chunks': actual_chunks,
                'variance_percentage': round(count_variance * 100, 1),
                'passed': count_variance < 0.2  # Allow 20% variance
            }
            
            if count_variance >= 0.2:
                validation_result['errors'].append(
                    f"Document count variance too high: {count_variance*100:.1f}%"
                )
                validation_result['passed'] = False
        
        # Search quality validation
        search_validation = self._validate_search_quality_post_migration(store)
        validation_result['checks']['search_quality'] = search_validation
        
        if not search_validation['passed']:
            validation_result['errors'].extend(search_validation['errors'])
            validation_result['passed'] = False
        
        # Performance validation
        performance_validation = self._validate_performance_post_migration(store, migration_result)
        validation_result['checks']['performance'] = performance_validation
        
        if not performance_validation['passed']:
            validation_result['warnings'].extend(performance_validation['warnings'])
        
        # Data integrity validation
        integrity_validation = self._validate_data_integrity(store, migration_result)
        validation_result['checks']['data_integrity'] = integrity_validation
        
        if not integrity_validation['passed']:
            validation_result['errors'].extend(integrity_validation['errors'])
            validation_result['passed'] = False
        
        logger.info(f"Validation complete for {store['display_name']}: "
                   f"{'PASSED' if validation_result['passed'] else 'FAILED'}")
        
        return validation_result
    
    def _validate_search_quality_post_migration(self, store: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search quality after migration"""
        
        # Generate test queries based on store content
        test_queries = self._generate_test_queries_for_store(store)
        
        search_results = []
        for query in test_queries:
            try:
                results = self.target_rag.search_manufacturing_documents(query, k=3)
                
                search_results.append({
                    'query': query,
                    'result_count': len(results),
                    'top_similarity': results[0]['similarity_score'] if results else 0,
                    'avg_quality': statistics.mean([r['quality_score'] for r in results]) if results else 0
                })
            except Exception as e:
                logger.error(f"Search validation error for query '{query}': {e}")
                return {
                    'passed': False,
                    'errors': [f"Search failed for query: {query}"]
                }
        
        # Evaluate search quality
        if not search_results:
            return {
                'passed': False,
                'errors': ['No search results obtained']
            }
        
        avg_results = statistics.mean([r['result_count'] for r in search_results])
        avg_similarity = statistics.mean([r['top_similarity'] for r in search_results])
        avg_quality = statistics.mean([r['avg_quality'] for r in search_results])
        
        # Quality thresholds
        min_results_threshold = 1
        min_similarity_threshold = 0.6
        min_quality_threshold = 0.7
        
        passed = (avg_results >= min_results_threshold and 
                 avg_similarity >= min_similarity_threshold and
                 avg_quality >= min_quality_threshold)
        
        return {
            'passed': passed,
            'average_results_per_query': round(avg_results, 1),
            'average_similarity_score': round(avg_similarity, 3),
            'average_quality_score': round(avg_quality, 3),
            'test_queries_count': len(test_queries),
            'errors': [] if passed else [
                f"Search quality below threshold: similarity={avg_similarity:.3f}, quality={avg_quality:.3f}"
            ]
        }
    
    def _generate_test_queries_for_store(self, store: Dict[str, Any]) -> List[str]:
        """Generate test queries based on store document types"""
        
        doc_types = store['document_types']
        
        query_templates = {
            'maintenance_manual': [
                "daily maintenance procedure for equipment",
                "weekly maintenance checklist",
                "equipment calibration procedure"
            ],
            'procedure': [
                "standard operating procedure",
                "step by step process guide", 
                "quality control procedure"
            ],
            'safety_guide': [
                "safety procedures and protocols",
                "emergency response procedures",
                "personal protective equipment requirements"
            ],
            'quality_manual': [
                "quality management system",
                "inspection procedures and requirements",
                "statistical process control methods"
            ],
            'specification': [
                "technical specifications and requirements",
                "process parameters and settings",
                "measurement and testing procedures"
            ]
        }
        
        test_queries = []
        for doc_type in doc_types:
            if doc_type in query_templates:
                test_queries.extend(query_templates[doc_type])
        
        # Add general manufacturing queries
        test_queries.extend([
            "equipment maintenance and service",
            "quality control and inspection",
            "safety protocols and procedures"
        ])
        
        return test_queries[:6]  # Limit to 6 test queries
    
    def _validate_performance_post_migration(self, store: Dict[str, Any], 
                                           migration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance characteristics after migration"""
        
        # Test query performance with store-specific queries
        test_queries = self._generate_test_queries_for_store(store)[:3]  # Use 3 queries
        
        query_times = []
        for query in test_queries:
            start_time = time.time()
            results = self.target_rag.search_manufacturing_documents(query, k=5)
            query_time = (time.time() - start_time) * 1000  # Convert to ms
            query_times.append(query_time)
        
        avg_query_time = statistics.mean(query_times) if query_times else 0
        max_query_time = max(query_times) if query_times else 0
        
        # Performance thresholds
        avg_threshold = 1000  # 1 second average
        max_threshold = 2000  # 2 seconds maximum
        
        passed = avg_query_time <= avg_threshold and max_query_time <= max_threshold
        warnings = []
        
        if not passed:
            if avg_query_time > avg_threshold:
                warnings.append(f"Average query time too high: {avg_query_time:.1f}ms")
            if max_query_time > max_threshold:
                warnings.append(f"Maximum query time too high: {max_query_time:.1f}ms")
        
        return {
            'passed': passed,
            'average_query_time_ms': round(avg_query_time, 1),
            'max_query_time_ms': round(max_query_time, 1),
            'queries_tested': len(query_times),
            'warnings': warnings
        }
    
    def _validate_data_integrity(self, store: Dict[str, Any], 
                               migration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data integrity after migration"""
        
        # Get system statistics to verify data integrity
        system_stats = self.target_rag.get_system_statistics()
        
        integrity_checks = []
        
        # Check if documents were actually inserted
        if 'total_chunks' in system_stats and system_stats['total_chunks'] > 0:
            integrity_checks.append({
                'check': 'data_insertion',
                'passed': True,
                'details': f"Found {system_stats['total_chunks']} chunks in system"
            })
        else:
            integrity_checks.append({
                'check': 'data_insertion', 
                'passed': False,
                'details': 'No chunks found in target system'
            })
        
        # Check document type distribution
        if 'document_type_distribution' in system_stats:
            expected_types = set(store['document_types'])
            actual_types = set(system_stats['document_type_distribution'].keys())
            
            type_overlap = len(expected_types.intersection(actual_types))
            type_coverage = type_overlap / len(expected_types) if expected_types else 0
            
            integrity_checks.append({
                'check': 'document_type_coverage',
                'passed': type_coverage >= 0.8,  # 80% coverage threshold
                'details': f"Document type coverage: {type_coverage:.1%}"
            })
        
        # Check average quality score
        if 'avg_quality_score' in system_stats and system_stats['avg_quality_score'] > 0:
            integrity_checks.append({
                'check': 'content_quality',
                'passed': system_stats['avg_quality_score'] >= 0.7,
                'details': f"Average quality score: {system_stats['avg_quality_score']:.2f}"
            })
        
        # Overall integrity assessment
        passed_checks = [check for check in integrity_checks if check['passed']]
        integrity_passed = len(passed_checks) >= len(integrity_checks) * 0.8  # 80% of checks must pass
        
        errors = [check['details'] for check in integrity_checks if not check['passed']]
        
        return {
            'passed': integrity_passed,
            'checks_performed': len(integrity_checks),
            'checks_passed': len(passed_checks),
            'integrity_score': len(passed_checks) / len(integrity_checks) if integrity_checks else 0,
            'detailed_checks': integrity_checks,
            'errors': errors
        }
    
    def _validate_wave_completion(self, wave: Dict[str, Any], 
                                wave_results: List[Dict[str, Any]]) -> bool:
        """Validate that a migration wave completed successfully"""
        
        successful_migrations = [r for r in wave_results if r['status'] == 'success']
        success_rate = len(successful_migrations) / len(wave_results) if wave_results else 0
        
        # Wave passes if 80% of migrations succeed
        wave_passed = success_rate >= 0.8
        
        if wave_passed:
            logger.info(f"✅ Wave {wave['wave_number']} validation passed: "
                       f"{len(successful_migrations)}/{len(wave_results)} migrations successful")
        else:
            logger.error(f"❌ Wave {wave['wave_number']} validation failed: "
                        f"Only {success_rate:.1%} success rate")
        
        return wave_passed
    
    def _finalize_migration(self, store: Dict[str, Any], migration_result: Dict[str, Any]):
        """Finalize successful migration"""
        
        self.migration_stats['successful_migrations'] += 1
        
        # In production, this would:
        # 1. Update routing to direct traffic to new system
        # 2. Mark old Discovery Engine store for decommissioning
        # 3. Send success notifications
        # 4. Update documentation
        
        logger.info(f"✅ Migration finalized for {store['display_name']}")
    
    def _handle_migration_failure(self, checkpoint: MigrationCheckpoint, 
                                validation_result: Dict[str, Any]):
        """Handle migration failure with rollback"""
        
        self.migration_stats['failed_migrations'] += 1
        
        logger.error(f"Handling migration failure for checkpoint {checkpoint.checkpoint_id}")
        logger.error(f"Validation errors: {validation_result.get('errors', [])}")
        
        # In production, implement actual rollback:
        # 1. Restore from checkpoint backup
        # 2. Clean up partial migration data
        # 3. Send failure notifications
        # 4. Generate detailed failure report
    
    def _generate_migration_report(self, migration_results: List[Dict[str, Any]], 
                                 migration_plan: Dict[str, Any], 
                                 total_time: float) -> Dict[str, Any]:
        """Generate comprehensive migration report"""
        
        successful_results = [r for r in migration_results if r['status'] == 'success']
        failed_results = [r for r in migration_results if r['status'] in ['failed', 'error']]
        
        # Calculate totals
        total_documents_processed = sum(
            r.get('migration_result', {}).get('documents_processed', 0) 
            for r in successful_results
        )
        
        total_chunks_created = sum(
            r.get('migration_result', {}).get('chunks_created', 0) 
            for r in successful_results
        )
        
        report = {
            'migration_summary': {
                'total_stores': len(migration_results),
                'successful_stores': len(successful_results),
                'failed_stores': len(failed_results),
                'success_rate': len(successful_results) / len(migration_results) if migration_results else 0,
                'total_migration_time_hours': round(total_time / 3600, 2),
                'total_documents_processed': total_documents_processed,
                'total_chunks_created': total_chunks_created
            },
            'detailed_results': migration_results,
            'performance_metrics': {
                'avg_migration_time_per_store': round(total_time / len(migration_results), 1) if migration_results else 0,
                'documents_per_second': round(total_documents_processed / total_time, 2) if total_time > 0 else 0,
                'chunks_per_second': round(total_chunks_created / total_time, 2) if total_time > 0 else 0
            },
            'validation_summary': self._summarize_validation_results(successful_results),
            'recommendations': self._generate_post_migration_recommendations(migration_results),
            'system_statistics': self.target_rag.get_system_statistics()
        }
        
        return report
    
    def _summarize_validation_results(self, successful_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize validation results across all successful migrations"""
        
        validation_results = [r['validation_result'] for r in successful_results 
                            if 'validation_result' in r]
        
        if not validation_results:
            return {'no_validation_data': True}
        
        # Aggregate search quality metrics
        search_qualities = [
            v['checks'].get('search_quality', {}).get('average_similarity_score', 0) 
            for v in validation_results
            if 'search_quality' in v.get('checks', {})
        ]
        
        performance_metrics = [
            v['checks'].get('performance', {}).get('average_query_time_ms', 0)
            for v in validation_results  
            if 'performance' in v.get('checks', {})
        ]
        
        return {
            'validations_performed': len(validation_results),
            'average_search_quality': round(statistics.mean(search_qualities), 3) if search_qualities else 0,
            'average_query_time_ms': round(statistics.mean(performance_metrics), 1) if performance_metrics else 0,
            'quality_range': {
                'min': min(search_qualities) if search_qualities else 0,
                'max': max(search_qualities) if search_qualities else 0
            }
        }
    
    def _generate_post_migration_recommendations(self, migration_results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on migration results"""
        
        recommendations = []
        
        failed_results = [r for r in migration_results if r['status'] in ['failed', 'error']]
        successful_results = [r for r in migration_results if r['status'] == 'success']
        
        # Success rate recommendations
        success_rate = len(successful_results) / len(migration_results) if migration_results else 0
        
        if success_rate == 1.0:
            recommendations.append("✅ All migrations completed successfully - proceed with full production cutover")
        elif success_rate >= 0.8:
            recommendations.append(f"⚠️ {len(failed_results)} migrations failed - investigate failures before proceeding")
        else:
            recommendations.append(f"🚨 High failure rate ({success_rate:.1%}) - review migration strategy before continuing")
        
        # Performance recommendations
        performance_data = [
            r['validation_result']['checks'].get('performance', {}).get('average_query_time_ms', 0)
            for r in successful_results
            if 'validation_result' in r and 'performance' in r['validation_result']['checks']
        ]
        
        if performance_data:
            avg_performance = statistics.mean(performance_data)
            if avg_performance > 500:
                recommendations.append("🔧 Query performance needs optimization - consider index tuning")
            else:
                recommendations.append("✅ Query performance is acceptable")
        
        # Quality recommendations
        quality_data = [
            r['validation_result']['checks'].get('search_quality', {}).get('average_similarity_score', 0)
            for r in successful_results  
            if 'validation_result' in r and 'search_quality' in r['validation_result']['checks']
        ]
        
        if quality_data:
            avg_quality = statistics.mean(quality_data)
            if avg_quality < 0.7:
                recommendations.append("📈 Search quality below target - consider retuning similarity thresholds")
            else:
                recommendations.append("✅ Search quality meets requirements")
        
        # General recommendations
        recommendations.append("📊 Monitor system performance for 48 hours before full cutover")
        recommendations.append("🔄 Schedule regular backup validation of migrated data")
        
        if failed_results:
            recommendations.append("🔍 Analyze failed migrations for pattern identification")
        
        return recommendations

def main():
    """Main function to demonstrate migration pipeline"""
    
    PROJECT_ID = "your-gcp-project"  # Replace with actual project
    TARGET_DATASET = "manufacturing_rag_migrated"
    
    print("🏗️ Discovery Engine to BigQuery RAG Migration Demo")
    print("=" * 60)
    
    # Step 1: Assessment
    print("\n📋 Step 1: Discovery Engine Assessment")
    assessment = DiscoveryEngineAssessment(PROJECT_ID)
    migration_plan = assessment.inventory_discovery_stores()
    
    print(f"Found {migration_plan['summary']['total_stores']} stores to migrate")
    print(f"Total documents: {migration_plan['summary']['total_documents']:,}")
    print(f"Estimated time: {migration_plan['summary']['estimated_weeks']} weeks")
    
    # Step 2: Migration execution
    print("\n🚀 Step 2: Migration Execution")
    migration_pipeline = AutomatedMigrationPipeline(PROJECT_ID, TARGET_DATASET)
    migration_report = migration_pipeline.execute_full_migration(migration_plan)
    
    # Step 3: Results summary
    print("\n📊 Step 3: Migration Results")
    summary = migration_report['migration_summary']
    print(f"Stores migrated: {summary['successful_stores']}/{summary['total_stores']}")
    print(f"Success rate: {summary['success_rate']:.1%}")
    print(f"Total migration time: {summary['total_migration_time_hours']} hours")
    print(f"Documents processed: {summary['total_documents_processed']:,}")
    print(f"Chunks created: {summary['total_chunks_created']:,}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    for rec in migration_report['recommendations']:
        print(f"   {rec}")
    
    return migration_report

if __name__ == "__main__":
    main()