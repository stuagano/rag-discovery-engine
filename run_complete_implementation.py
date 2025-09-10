#!/usr/bin/env python3
"""
Complete RAG Discovery Engine Implementation Runner
Main executable script for running the complete implementation pipeline
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from execution_coordinator import RAGDiscoveryEngineCoordinator

def setup_environment():
    """Setup environment and dependencies"""
    print("🔧 Setting up environment...")
    
    # Create necessary directories
    directories = [
        'data', 'logs', 'results', 'reports', 'benchmarks'
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
        print(f"   ✅ Created directory: {directory}")
    
    # Check Python dependencies
    required_packages = [
        'google-cloud-bigquery', 
        'google-cloud-aiplatform',
        'google-cloud-storage',
        'pandas',
        'numpy',
        'scikit-learn'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("⚠️ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Environment setup complete")
    return True

def validate_gcp_setup(project_id: str):
    """Validate GCP setup and credentials"""
    print(f"🔍 Validating GCP setup for project: {project_id}")
    
    try:
        from google.cloud import bigquery
        
        # Test BigQuery connection
        client = bigquery.Client(project=project_id)
        
        # Try to list datasets (this will fail if credentials are wrong)
        list(client.list_datasets())
        
        print("✅ GCP credentials and BigQuery access validated")
        return True
        
    except Exception as e:
        print(f"❌ GCP setup validation failed: {e}")
        print("\nPlease ensure:")
        print("1. You have valid GCP credentials configured")
        print("2. Your project ID is correct")
        print("3. BigQuery API is enabled")
        print("4. You have necessary IAM permissions")
        return False

def run_quick_demo(project_id: str):
    """Run a quick demo of core functionality"""
    print("🚀 Running Quick Demo Mode...")
    
    config = {
        'dataset_acquisition': {
            'sources': ['synthetic'],
            'synthetic_count': 10,  # Small count for demo
            'enable_quality_validation': True
        },
        'rag_pipeline': {
            'dataset_id': 'manufacturing_rag_demo',
            'batch_size': 5  # Small batch for demo
        },
        'benchmarking': {
            'comprehensive_suite': False,  # Limited benchmarks for demo
            'accuracy_tests': True,
            'performance_tests': True
        },
        'execution': {
            'continue_on_error': True
        }
    }
    
    # Run limited phases for demo
    demo_phases = [
        'dataset_acquisition',
        'rag_pipeline_setup', 
        'data_ingestion',
        'benchmarking'
    ]
    
    coordinator = RAGDiscoveryEngineCoordinator(project_id, config)
    results = coordinator.execute_complete_pipeline(demo_phases)
    
    return results

def run_full_implementation(project_id: str, custom_config=None):
    """Run full implementation pipeline"""
    print("🚀 Running Full Implementation Pipeline...")
    
    coordinator = RAGDiscoveryEngineCoordinator(project_id, custom_config)
    results = coordinator.execute_complete_pipeline()
    
    return results

def display_usage_examples():
    """Display usage examples"""
    script_name = Path(__file__).name
    
    examples = f"""
Usage Examples:

1. Quick Demo (recommended for first run):
   python {script_name} --project-id your-gcp-project --mode demo

2. Full Implementation:
   python {script_name} --project-id your-gcp-project --mode full

3. Run specific phases only:
   python {script_name} --project-id your-gcp-project --mode custom \\
     --phases dataset_acquisition rag_pipeline_setup benchmarking

4. Validation only (check setup):
   python {script_name} --project-id your-gcp-project --validate-only

Prerequisites:
- GCP project with BigQuery API enabled
- Application Default Credentials configured
- Required Python packages installed (see requirements.txt)

Configuration:
The system uses intelligent defaults, but you can customize behavior by creating
a configuration file and passing it with --config-file parameter.
"""
    print(examples)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Complete RAG Discovery Engine Implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="For detailed usage examples, run with --help-examples"
    )
    
    parser.add_argument(
        '--project-id', 
        required=True,
        help='GCP Project ID'
    )
    
    parser.add_argument(
        '--mode',
        choices=['demo', 'full', 'custom'],
        default='demo',
        help='Execution mode: demo (quick test), full (complete pipeline), or custom (selected phases)'
    )
    
    parser.add_argument(
        '--phases',
        nargs='*',
        choices=[
            'dataset_acquisition', 'rag_pipeline_setup', 'data_ingestion',
            'discovery_assessment', 'migration_execution', 'benchmarking', 
            'report_generation'
        ],
        help='Specific phases to run (only used with --mode custom)'
    )
    
    parser.add_argument(
        '--config-file',
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate setup without running implementation'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip environment and GCP validation'
    )
    
    parser.add_argument(
        '--help-examples',
        action='store_true',
        help='Show detailed usage examples'
    )
    
    args = parser.parse_args()
    
    if args.help_examples:
        display_usage_examples()
        return
    
    print("🎯 RAG Discovery Engine - Complete Implementation")
    print("=" * 60)
    
    # Environment setup
    if not args.skip_validation:
        if not setup_environment():
            print("❌ Environment setup failed")
            sys.exit(1)
        
        # GCP validation
        if not validate_gcp_setup(args.project_id):
            print("❌ GCP validation failed")
            sys.exit(1)
    
    # If validation only, exit here
    if args.validate_only:
        print("✅ Validation completed successfully")
        return
    
    # Load custom configuration if provided
    custom_config = None
    if args.config_file:
        try:
            import json
            with open(args.config_file, 'r') as f:
                custom_config = json.load(f)
            print(f"✅ Loaded configuration from: {args.config_file}")
        except Exception as e:
            print(f"❌ Failed to load configuration file: {e}")
            sys.exit(1)
    
    # Execute based on mode
    try:
        if args.mode == 'demo':
            results = run_quick_demo(args.project_id)
        
        elif args.mode == 'full':
            results = run_full_implementation(args.project_id, custom_config)
        
        elif args.mode == 'custom':
            if not args.phases:
                print("❌ --phases required when using --mode custom")
                sys.exit(1)
            
            coordinator = RAGDiscoveryEngineCoordinator(args.project_id, custom_config)
            results = coordinator.execute_complete_pipeline(args.phases)
        
        # Display final results
        execution_summary = results.get('execution_summary', {})
        overall_status = execution_summary.get('overall_status', 'unknown')
        
        print("\n" + "="*60)
        print("🎉 EXECUTION COMPLETED")
        print("="*60)
        print(f"📊 Overall Status: {overall_status}")
        print(f"⏱️ Total Time: {execution_summary.get('total_execution_time_minutes', 0):.1f} minutes")
        print(f"✅ Successful Phases: {execution_summary.get('successful_phases', 0)}/{execution_summary.get('total_phases', 0)}")
        
        if overall_status == 'success':
            print("🚀 Implementation completed successfully!")
            print("📄 Check the reports/ directory for detailed results")
            sys.exit(0)
        elif overall_status == 'partial_success':
            print("⚠️ Implementation partially successful - review logs for details")
            sys.exit(1)
        else:
            print("❌ Implementation failed - check logs for error details")
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n⚠️ Execution interrupted by user")
        sys.exit(130)
    
    except Exception as e:
        print(f"❌ Unexpected error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()