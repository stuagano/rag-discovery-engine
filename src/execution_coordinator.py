"""
Execution Coordinator for Complete RAG Discovery Engine Implementation
Orchestrates the entire pipeline from dataset acquisition to benchmarking
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import argparse
import sys
import os

from dataset_acquisition import ManufacturingDatasetAcquisitor
from bigquery_rag_pipeline import OptimizedManufacturingRAG
from migration_pipeline import DiscoveryEngineAssessment, AutomatedMigrationPipeline
from benchmark_framework import ManufacturingRAGBenchmarkSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/Users/stuartgano/Desktop/Micron/Genie/people-projects/Paul/rag-discovery-engine-swarm/logs/execution.log')
    ]
)
logger = logging.getLogger(__name__)

class RAGDiscoveryEngineCoordinator:
    """Main coordinator for the complete RAG Discovery Engine implementation"""
    
    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        self.project_id = project_id
        self.config = config or self._load_default_config()
        
        # Initialize execution tracking
        self.execution_id = f"rag_exec_{int(time.time())}"
        self.execution_start_time = time.time()
        self.execution_results = {
            'execution_id': self.execution_id,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'config': self.config,
            'phases': {}
        }
        
        # Create logs directory
        os.makedirs(os.path.dirname('/Users/stuartgano/Desktop/Micron/Genie/people-projects/Paul/rag-discovery-engine-swarm/logs/execution.log'), exist_ok=True)
        
        logger.info(f"🚀 Initialized RAG Discovery Engine Coordinator")
        logger.info(f"   Execution ID: {self.execution_id}")
        logger.info(f"   Project ID: {project_id}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for execution"""
        return {
            'dataset_acquisition': {
                'sources': ['ragbench', 'synthetic', 'scraped'],
                'synthetic_count': 100,
                'enable_quality_validation': True
            },
            'rag_pipeline': {
                'dataset_id': 'manufacturing_rag_production',
                'embedding_model': 'gemini-embedding-001',
                'chunk_size': 1000,
                'chunk_overlap': 200,
                'batch_size': 50
            },
            'migration': {
                'enable_assessment': True,
                'migration_strategy': 'auto',  # auto, batch_reprocessing, streaming
                'validation_enabled': True,
                'backup_enabled': True
            },
            'benchmarking': {
                'comprehensive_suite': True,
                'accuracy_tests': True,
                'performance_tests': True,
                'scalability_tests': True,
                'domain_specific_tests': True,
                'cost_analysis': True
            },
            'execution': {
                'save_intermediate_results': True,
                'continue_on_error': True,
                'generate_report': True
            }
        }
    
    def execute_complete_pipeline(self, phases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute the complete RAG Discovery Engine pipeline"""
        
        logger.info("🎯 STARTING COMPLETE RAG DISCOVERY ENGINE PIPELINE")
        logger.info("=" * 70)
        
        # Default phases if not specified
        if phases is None:
            phases = [
                'dataset_acquisition',
                'rag_pipeline_setup', 
                'data_ingestion',
                'discovery_assessment',
                'migration_execution',
                'benchmarking',
                'report_generation'
            ]
        
        try:
            for phase in phases:
                logger.info(f"\n📋 PHASE: {phase.upper()}")
                logger.info("-" * 50)
                
                phase_start_time = time.time()
                
                if phase == 'dataset_acquisition':
                    result = self._execute_dataset_acquisition()
                elif phase == 'rag_pipeline_setup':
                    result = self._execute_rag_pipeline_setup()
                elif phase == 'data_ingestion':
                    result = self._execute_data_ingestion()
                elif phase == 'discovery_assessment':
                    result = self._execute_discovery_assessment()
                elif phase == 'migration_execution':
                    result = self._execute_migration()
                elif phase == 'benchmarking':
                    result = self._execute_benchmarking()
                elif phase == 'report_generation':
                    result = self._execute_report_generation()
                else:
                    logger.warning(f"Unknown phase: {phase}")
                    result = {'status': 'skipped', 'reason': 'unknown_phase'}
                
                phase_time = time.time() - phase_start_time
                
                # Record phase results
                self.execution_results['phases'][phase] = {
                    'result': result,
                    'execution_time_seconds': round(phase_time, 2),
                    'status': result.get('status', 'unknown'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(f"✅ Phase {phase} completed in {phase_time/60:.1f} minutes")
                
                # Save intermediate results if enabled
                if self.config['execution']['save_intermediate_results']:
                    self._save_intermediate_results()
                
                # Check if we should continue on error
                if (result.get('status') == 'error' and 
                    not self.config['execution']['continue_on_error']):
                    logger.error(f"Pipeline stopped due to error in phase: {phase}")
                    break
        
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            self.execution_results['error'] = str(e)
        
        # Finalize execution results
        self._finalize_execution_results()
        
        # Generate and save final report
        if self.config['execution']['generate_report']:
            self._generate_final_report()
        
        logger.info(f"\n🎉 PIPELINE EXECUTION COMPLETED")
        total_time = time.time() - self.execution_start_time
        logger.info(f"Total execution time: {total_time/60:.1f} minutes")
        
        return self.execution_results
    
    def _execute_dataset_acquisition(self) -> Dict[str, Any]:
        """Execute dataset acquisition phase"""
        
        logger.info("Acquiring manufacturing PDF datasets...")
        
        try:
            # Initialize dataset acquisitor
            acquisitor = ManufacturingDatasetAcquisitor(
                self.project_id, 
                storage_bucket=f"{self.project_id}-rag-data"
            )
            
            # Acquire datasets
            datasets = acquisitor.acquire_all_datasets()
            
            # Validate dataset quality
            all_documents = []
            for source_docs in datasets.values():
                all_documents.extend(source_docs)
            
            validation_results = acquisitor.validate_dataset_quality(all_documents)
            
            logger.info(f"Acquired {len(all_documents)} documents from {len(datasets)} sources")
            
            return {
                'status': 'success',
                'datasets_acquired': datasets,
                'total_documents': len(all_documents),
                'sources': list(datasets.keys()),
                'validation_results': validation_results
            }
            
        except Exception as e:
            logger.error(f"Dataset acquisition failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _execute_rag_pipeline_setup(self) -> Dict[str, Any]:
        """Execute RAG pipeline setup phase"""
        
        logger.info("Setting up optimized RAG pipeline...")
        
        try:
            # Initialize RAG pipeline
            rag_pipeline = OptimizedManufacturingRAG(
                self.project_id,
                dataset_id=self.config['rag_pipeline']['dataset_id']
            )
            
            # Setup optimized schema
            table = rag_pipeline.setup_optimized_schema()
            
            # Store pipeline reference for later phases
            self.rag_pipeline = rag_pipeline
            
            logger.info("RAG pipeline setup completed successfully")
            
            return {
                'status': 'success',
                'dataset_id': self.config['rag_pipeline']['dataset_id'],
                'table_created': str(table.table_id) if table else None,
                'embedding_model': self.config['rag_pipeline']['embedding_model']
            }
            
        except Exception as e:
            logger.error(f"RAG pipeline setup failed: {e}")
            return {
                'status': 'error', 
                'error': str(e)
            }
    
    def _execute_data_ingestion(self) -> Dict[str, Any]:
        """Execute data ingestion phase"""
        
        logger.info("Ingesting documents into RAG pipeline...")
        
        try:
            # Get documents from previous phase
            dataset_results = self.execution_results['phases'].get('dataset_acquisition', {})
            datasets = dataset_results.get('result', {}).get('datasets_acquired', {})
            
            if not datasets:
                logger.warning("No datasets found from acquisition phase, creating sample data")
                # Create sample documents for demo
                sample_documents = self._create_sample_documents()
                all_documents = sample_documents
            else:
                # Flatten all documents from all sources
                all_documents = []
                for source_docs in datasets.values():
                    all_documents.extend(source_docs)
            
            # Process documents through RAG pipeline
            if hasattr(self, 'rag_pipeline'):
                processing_stats = self.rag_pipeline.process_manufacturing_documents_batch(
                    all_documents,
                    batch_size=self.config['rag_pipeline']['batch_size']
                )
                
                # Get system statistics after ingestion
                system_stats = self.rag_pipeline.get_system_statistics()
                
                logger.info(f"Processed {processing_stats['processed_chunks']} chunks "
                           f"from {len(all_documents)} documents")
                
                return {
                    'status': 'success',
                    'processing_stats': processing_stats,
                    'system_statistics': system_stats,
                    'documents_processed': len(all_documents)
                }
            else:
                return {
                    'status': 'error',
                    'error': 'RAG pipeline not initialized'
                }
                
        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _create_sample_documents(self) -> List[Dict[str, Any]]:
        """Create sample documents for demonstration"""
        
        sample_docs = [
            {
                'id': 'sample_001',
                'title': 'Ion Implanter Maintenance Procedure',
                'content': 'Daily maintenance procedure for ion implanter equipment includes checking vacuum levels, cleaning sample chamber, calibrating beam current, and verifying safety interlocks. Always follow lockout tagout procedures before accessing equipment internals.',
                'doc_type': 'maintenance_manual',
                'source': 'sample_data',
                'facility_code': 'fab_01',
                'metadata': {'category': 'equipment_maintenance', 'safety_level': 'high'}
            },
            {
                'id': 'sample_002',
                'title': 'Semiconductor Quality Control Checklist',
                'content': 'Quality control procedure for semiconductor wafer inspection includes visual examination, dimensional measurement, electrical testing, and defect classification. All measurements must be recorded in the quality management system and reviewed by certified personnel.',
                'doc_type': 'quality_manual',
                'source': 'sample_data',
                'facility_code': 'fab_02',
                'metadata': {'category': 'quality_control', 'safety_level': 'medium'}
            },
            {
                'id': 'sample_003',
                'title': 'Photolithography Safety Protocols',
                'content': 'WARNING: Photolithography process involves hazardous chemicals including photoresist and developers. Personal protective equipment including chemical-resistant gloves, safety glasses, and lab coats must be worn. Emergency shower and eyewash stations must be easily accessible.',
                'doc_type': 'safety_guide',
                'source': 'sample_data',
                'facility_code': 'fab_01',
                'metadata': {'category': 'safety_procedures', 'safety_level': 'high'}
            }
        ]
        
        return sample_docs
    
    def _execute_discovery_assessment(self) -> Dict[str, Any]:
        """Execute Discovery Engine assessment phase"""
        
        logger.info("Assessing existing Discovery Engine stores...")
        
        try:
            if self.config['migration']['enable_assessment']:
                # Initialize assessment
                assessment = DiscoveryEngineAssessment(self.project_id)
                
                # Perform comprehensive inventory
                migration_plan = assessment.inventory_discovery_stores()
                
                logger.info(f"Assessed {migration_plan['summary']['total_stores']} Discovery Engine stores")
                logger.info(f"Total documents to migrate: {migration_plan['summary']['total_documents']}")
                
                return {
                    'status': 'success',
                    'migration_plan': migration_plan,
                    'stores_assessed': migration_plan['summary']['total_stores'],
                    'estimated_migration_time': migration_plan['summary']['estimated_weeks']
                }
            else:
                logger.info("Discovery Engine assessment skipped per configuration")
                return {
                    'status': 'skipped',
                    'reason': 'assessment_disabled'
                }
                
        except Exception as e:
            logger.error(f"Discovery Engine assessment failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _execute_migration(self) -> Dict[str, Any]:
        """Execute migration phase"""
        
        logger.info("Executing Discovery Engine migration...")
        
        try:
            # Get migration plan from assessment phase
            assessment_results = self.execution_results['phases'].get('discovery_assessment', {})
            migration_plan = assessment_results.get('result', {}).get('migration_plan')
            
            if not migration_plan:
                logger.warning("No migration plan found, creating demo migration plan")
                # Create minimal migration plan for demo
                migration_plan = {
                    'summary': {'total_stores': 1, 'total_documents': 100},
                    'migration_waves': [{
                        'wave_number': 1,
                        'stores': [{
                            'store_id': 'demo-store',
                            'display_name': 'Demo Manufacturing Store',
                            'document_count': 100,
                            'migration_complexity': 'low',
                            'recommended_strategy': 'batch_reprocessing'
                        }]
                    }]
                }
            
            # Initialize migration pipeline
            migration_pipeline = AutomatedMigrationPipeline(
                self.project_id,
                target_dataset=self.config['rag_pipeline']['dataset_id']
            )
            
            # Execute migration
            migration_report = migration_pipeline.execute_full_migration(migration_plan)
            
            logger.info(f"Migration completed: {migration_report['migration_summary']['success_rate']:.1%} success rate")
            
            return {
                'status': 'success',
                'migration_report': migration_report,
                'success_rate': migration_report['migration_summary']['success_rate'],
                'stores_migrated': migration_report['migration_summary']['successful_stores']
            }
            
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _execute_benchmarking(self) -> Dict[str, Any]:
        """Execute comprehensive benchmarking phase"""
        
        logger.info("Executing comprehensive benchmarking...")
        
        try:
            if not hasattr(self, 'rag_pipeline'):
                # Initialize RAG pipeline if not already done
                self.rag_pipeline = OptimizedManufacturingRAG(
                    self.project_id,
                    dataset_id=self.config['rag_pipeline']['dataset_id']
                )
            
            # Initialize benchmark suite
            benchmark_suite = ManufacturingRAGBenchmarkSuite(
                self.rag_pipeline,
                self.project_id
            )
            
            # Run comprehensive benchmarks
            benchmark_results = benchmark_suite.run_comprehensive_benchmark()
            
            logger.info(f"Benchmarking completed with grade: {benchmark_results.get('performance_grade', 'N/A')}")
            
            return {
                'status': 'success',
                'benchmark_results': benchmark_results,
                'performance_grade': benchmark_results.get('performance_grade'),
                'key_metrics': benchmark_results.get('key_metrics', {})
            }
            
        except Exception as e:
            logger.error(f"Benchmarking failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _execute_report_generation(self) -> Dict[str, Any]:
        """Execute final report generation phase"""
        
        logger.info("Generating comprehensive execution report...")
        
        try:
            # Compile comprehensive report
            report = self._compile_comprehensive_report()
            
            # Save report to file
            report_path = self._save_execution_report(report)
            
            logger.info(f"Comprehensive report generated: {report_path}")
            
            return {
                'status': 'success',
                'report_path': report_path,
                'report_summary': report.get('executive_summary', {})
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _finalize_execution_results(self):
        """Finalize execution results with summary metrics"""
        
        total_time = time.time() - self.execution_start_time
        
        # Calculate phase statistics
        successful_phases = sum(1 for phase_result in self.execution_results['phases'].values() 
                               if phase_result.get('result', {}).get('status') == 'success')
        total_phases = len(self.execution_results['phases'])
        
        # Add execution summary
        self.execution_results['execution_summary'] = {
            'total_execution_time_minutes': round(total_time / 60, 2),
            'end_time': datetime.now(timezone.utc).isoformat(),
            'successful_phases': successful_phases,
            'total_phases': total_phases,
            'success_rate': (successful_phases / total_phases) * 100 if total_phases > 0 else 0,
            'overall_status': 'success' if successful_phases == total_phases else 'partial_success' if successful_phases > 0 else 'failed'
        }
    
    def _save_intermediate_results(self):
        """Save intermediate execution results"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f'/Users/stuartgano/Desktop/Micron/Genie/people-projects/Paul/rag-discovery-engine-swarm/results/intermediate_{self.execution_id}_{timestamp}.json'
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.execution_results, f, indent=2, default=str)
    
    def _compile_comprehensive_report(self) -> Dict[str, Any]:
        """Compile comprehensive execution report"""
        
        report = {
            'execution_metadata': {
                'execution_id': self.execution_id,
                'project_id': self.project_id,
                'execution_time': self.execution_results.get('execution_summary', {}),
                'configuration': self.config
            },
            'executive_summary': self._generate_executive_summary(),
            'phase_results': self.execution_results['phases'],
            'key_achievements': self._extract_key_achievements(),
            'performance_metrics': self._extract_performance_metrics(),
            'recommendations': self._generate_final_recommendations(),
            'next_steps': self._generate_next_steps()
        }
        
        return report
    
    def _generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary of execution results"""
        
        summary = {
            'project_overview': 'Complete migration from Discovery Engine to BigQuery-based RAG system for manufacturing documentation',
            'execution_status': self.execution_results.get('execution_summary', {}).get('overall_status', 'unknown'),
            'key_metrics': {}
        }
        
        # Extract key metrics from phases
        phases = self.execution_results.get('phases', {})
        
        # Dataset metrics
        if 'dataset_acquisition' in phases:
            dataset_result = phases['dataset_acquisition']['result']
            if dataset_result.get('status') == 'success':
                summary['key_metrics']['documents_acquired'] = dataset_result.get('total_documents', 0)
        
        # Migration metrics
        if 'migration_execution' in phases:
            migration_result = phases['migration_execution']['result']
            if migration_result.get('status') == 'success':
                migration_report = migration_result.get('migration_report', {})
                summary['key_metrics']['migration_success_rate'] = migration_report.get('migration_summary', {}).get('success_rate', 0)
        
        # Benchmark metrics
        if 'benchmarking' in phases:
            benchmark_result = phases['benchmarking']['result']
            if benchmark_result.get('status') == 'success':
                summary['key_metrics']['performance_grade'] = benchmark_result.get('performance_grade', 'N/A')
                key_metrics = benchmark_result.get('key_metrics', {})
                if 'cost' in key_metrics:
                    summary['key_metrics']['cost_savings_percentage'] = key_metrics['cost']['savings_percentage']
        
        return summary
    
    def _extract_key_achievements(self) -> List[str]:
        """Extract key achievements from execution"""
        
        achievements = []
        phases = self.execution_results.get('phases', {})
        
        # Dataset acquisition achievements
        if phases.get('dataset_acquisition', {}).get('result', {}).get('status') == 'success':
            total_docs = phases['dataset_acquisition']['result'].get('total_documents', 0)
            achievements.append(f"✅ Successfully acquired {total_docs} manufacturing documents from multiple sources")
        
        # RAG pipeline achievements
        if phases.get('rag_pipeline_setup', {}).get('result', {}).get('status') == 'success':
            achievements.append("✅ Deployed optimized BigQuery RAG pipeline with advanced schema")
        
        # Data ingestion achievements
        if phases.get('data_ingestion', {}).get('result', {}).get('status') == 'success':
            processing_stats = phases['data_ingestion']['result'].get('processing_stats', {})
            chunks = processing_stats.get('processed_chunks', 0)
            achievements.append(f"✅ Successfully ingested and processed {chunks} document chunks")
        
        # Migration achievements
        if phases.get('migration_execution', {}).get('result', {}).get('status') == 'success':
            success_rate = phases['migration_execution']['result'].get('success_rate', 0)
            achievements.append(f"✅ Completed Discovery Engine migration with {success_rate:.1%} success rate")
        
        # Benchmarking achievements
        if phases.get('benchmarking', {}).get('result', {}).get('status') == 'success':
            grade = phases['benchmarking']['result'].get('performance_grade', 'N/A')
            achievements.append(f"✅ Achieved performance grade {grade} in comprehensive benchmarks")
        
        return achievements
    
    def _extract_performance_metrics(self) -> Dict[str, Any]:
        """Extract performance metrics from execution"""
        
        metrics = {}
        phases = self.execution_results.get('phases', {})
        
        # Benchmarking metrics
        if 'benchmarking' in phases and phases['benchmarking']['result'].get('status') == 'success':
            benchmark_result = phases['benchmarking']['result']
            key_metrics = benchmark_result.get('key_metrics', {})
            
            if 'accuracy' in key_metrics:
                metrics['accuracy'] = key_metrics['accuracy']
            
            if 'performance' in key_metrics:
                metrics['performance'] = key_metrics['performance']
            
            if 'cost' in key_metrics:
                metrics['cost'] = key_metrics['cost']
        
        # System statistics
        if 'data_ingestion' in phases and phases['data_ingestion']['result'].get('status') == 'success':
            system_stats = phases['data_ingestion']['result'].get('system_statistics', {})
            metrics['system'] = {
                'total_chunks': system_stats.get('total_chunks', 0),
                'total_documents': system_stats.get('total_documents', 0),
                'avg_quality_score': system_stats.get('avg_quality_score', 0)
            }
        
        return metrics
    
    def _generate_final_recommendations(self) -> List[str]:
        """Generate final recommendations based on execution results"""
        
        recommendations = []
        phases = self.execution_results.get('phases', {})
        
        # General recommendations
        overall_status = self.execution_results.get('execution_summary', {}).get('overall_status')
        
        if overall_status == 'success':
            recommendations.append("🎯 All phases completed successfully - proceed with production deployment")
        elif overall_status == 'partial_success':
            recommendations.append("⚠️ Some phases had issues - review failed phases before production deployment")
        else:
            recommendations.append("🚨 Multiple phases failed - comprehensive review required before proceeding")
        
        # Benchmark-based recommendations
        if 'benchmarking' in phases and phases['benchmarking']['result'].get('status') == 'success':
            benchmark_recommendations = phases['benchmarking']['result'].get('benchmark_results', {}).get('recommendations', [])
            recommendations.extend(benchmark_recommendations[:3])  # Top 3 recommendations
        
        # Migration-based recommendations
        if 'migration_execution' in phases and phases['migration_execution']['result'].get('status') == 'success':
            migration_report = phases['migration_execution']['result'].get('migration_report', {})
            migration_recommendations = migration_report.get('recommendations', [])
            recommendations.extend(migration_recommendations[:2])  # Top 2 recommendations
        
        return recommendations
    
    def _generate_next_steps(self) -> List[str]:
        """Generate next steps based on execution results"""
        
        next_steps = []
        phases = self.execution_results.get('phases', {})
        overall_status = self.execution_results.get('execution_summary', {}).get('overall_status')
        
        if overall_status == 'success':
            next_steps.extend([
                "1. Review comprehensive benchmark results and validate performance meets requirements",
                "2. Conduct user acceptance testing with manufacturing domain experts",
                "3. Plan production cutover strategy with gradual traffic migration",
                "4. Set up monitoring and alerting for the new RAG system",
                "5. Schedule training sessions for end users on new system capabilities"
            ])
        else:
            next_steps.extend([
                "1. Analyze failed phases and identify root causes",
                "2. Implement fixes for identified issues",
                "3. Re-run failed phases with updated configuration",
                "4. Conduct additional validation testing before proceeding"
            ])
        
        # Add monitoring recommendations
        next_steps.append("6. Implement continuous monitoring of query performance and accuracy")
        next_steps.append("7. Establish regular benchmark execution schedule for ongoing optimization")
        
        return next_steps
    
    def _save_execution_report(self, report: Dict[str, Any]) -> str:
        """Save execution report to file"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'rag_discovery_engine_execution_report_{self.execution_id}_{timestamp}.json'
        filepath = f'/Users/stuartgano/Desktop/Micron/Genie/people-projects/Paul/rag-discovery-engine-swarm/reports/{filename}'
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filepath
    
    def _generate_final_report(self):
        """Generate and save final report"""
        
        # Generate comprehensive report
        report = self._compile_comprehensive_report()
        
        # Save to file
        report_path = self._save_execution_report(report)
        
        # Display summary
        logger.info("\n" + "="*70)
        logger.info("🎯 EXECUTION SUMMARY REPORT")
        logger.info("="*70)
        
        exec_summary = report.get('executive_summary', {})
        logger.info(f"📊 Project: {exec_summary.get('project_overview', 'N/A')}")
        logger.info(f"📈 Status: {exec_summary.get('execution_status', 'N/A')}")
        
        # Key metrics
        key_metrics = exec_summary.get('key_metrics', {})
        if key_metrics:
            logger.info("\n📋 Key Metrics:")
            for metric, value in key_metrics.items():
                logger.info(f"   {metric}: {value}")
        
        # Achievements
        achievements = report.get('key_achievements', [])
        if achievements:
            logger.info("\n🏆 Key Achievements:")
            for achievement in achievements:
                logger.info(f"   {achievement}")
        
        # Recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            logger.info("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):  # Top 5
                logger.info(f"   {i}. {rec}")
        
        logger.info(f"\n📄 Full report saved to: {report_path}")

def main():
    """Main function with command-line interface"""
    
    parser = argparse.ArgumentParser(description='RAG Discovery Engine Implementation Coordinator')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--phases', nargs='*', help='Specific phases to run', 
                       choices=['dataset_acquisition', 'rag_pipeline_setup', 'data_ingestion', 
                               'discovery_assessment', 'migration_execution', 'benchmarking', 
                               'report_generation'])
    parser.add_argument('--config-file', help='Path to configuration file')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Load configuration
    config = None
    if args.config_file:
        try:
            with open(args.config_file, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)
    
    # Initialize coordinator
    coordinator = RAGDiscoveryEngineCoordinator(args.project_id, config)
    
    # Execute pipeline
    results = coordinator.execute_complete_pipeline(args.phases)
    
    # Return exit code based on results
    overall_status = results.get('execution_summary', {}).get('overall_status', 'failed')
    if overall_status == 'success':
        sys.exit(0)
    elif overall_status == 'partial_success':
        sys.exit(1)
    else:
        sys.exit(2)

if __name__ == "__main__":
    main()