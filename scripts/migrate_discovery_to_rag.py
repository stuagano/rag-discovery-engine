#!/usr/bin/env python3
"""
Simple Discovery Engine to RAG Engine Migration Script
Preserves embeddings to avoid re-computation costs
"""

import os
import sys
import argparse
import json
from datetime import datetime
import logging
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.discovery_to_rag_migrator import DiscoveryToRAGMigrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load configuration from .env file"""
    
    config = {}
    
    # Try to load from .env.unified first
    env_files = ['.env.unified', '.env']
    
    for env_file in env_files:
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            break
    
    # Use environment variables as override
    config['GOOGLE_CLOUD_PROJECT'] = os.getenv('GOOGLE_CLOUD_PROJECT', config.get('GOOGLE_CLOUD_PROJECT'))
    config['GOOGLE_CLOUD_REGION'] = os.getenv('GOOGLE_CLOUD_REGION', config.get('GOOGLE_CLOUD_REGION', 'us-central1'))
    
    return config


def migration_wizard():
    """Interactive migration wizard"""
    
    print("\n" + "="*60)
    print("🔄 DISCOVERY ENGINE → RAG ENGINE MIGRATION WIZARD")
    print("="*60)
    print("\nThis tool migrates your Discovery Engine data to RAG Engine")
    print("while PRESERVING existing embeddings to save costs.")
    print("\n✨ Key Benefits:")
    print("  • No need to regenerate embeddings ($0.0001/embedding saved)")
    print("  • Incremental migration support")
    print("  • Validation to ensure quality")
    print("  • Rollback capability")
    
    # Get user inputs
    print("\n" + "-"*60)
    datastore_id = input("Enter Discovery Engine Datastore ID: ").strip()
    
    print("\n📊 Migration Options:")
    print("1. RAG Engine (Recommended - Managed solution)")
    print("2. BigQuery (Custom solution with more control)")
    
    choice = input("\nSelect target [1/2]: ").strip()
    
    preserve = input("\n🔐 Preserve existing embeddings? [Y/n]: ").strip().lower()
    preserve_embeddings = preserve != 'n'
    
    validate = input("\n✅ Run validation after migration? [Y/n]: ").strip().lower()
    run_validation = validate != 'n'
    
    incremental = input("\n📈 Enable incremental migration? [Y/n]: ").strip().lower()
    use_incremental = incremental != 'n'
    
    print("\n" + "-"*60)
    print("📋 Migration Summary:")
    print(f"  • Source: Discovery Engine ({datastore_id})")
    print(f"  • Target: {'RAG Engine' if choice == '1' else 'BigQuery'}")
    print(f"  • Preserve Embeddings: {'Yes' if preserve_embeddings else 'No'}")
    print(f"  • Validation: {'Yes' if run_validation else 'No'}")
    print(f"  • Incremental: {'Yes' if use_incremental else 'No'}")
    print("-"*60)
    
    confirm = input("\n🚀 Start migration? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Migration cancelled.")
        return
    
    return {
        'datastore_id': datastore_id,
        'target': 'rag_engine' if choice == '1' else 'bigquery',
        'preserve_embeddings': preserve_embeddings,
        'run_validation': run_validation,
        'use_incremental': use_incremental
    }


def estimate_costs(num_documents: int, preserve_embeddings: bool) -> Dict[str, float]:
    """Estimate migration costs"""
    
    costs = {
        'embedding_generation': 0.0 if preserve_embeddings else num_documents * 0.0001,
        'rag_engine_storage': num_documents * 0.00001,  # ~$0.10/GB
        'bigquery_storage': num_documents * 0.000002,   # ~$0.02/GB
        'processing': num_documents * 0.00001
    }
    
    costs['total_rag'] = costs['embedding_generation'] + costs['rag_engine_storage'] + costs['processing']
    costs['total_bigquery'] = costs['embedding_generation'] + costs['bigquery_storage'] + costs['processing']
    
    return costs


def main():
    parser = argparse.ArgumentParser(description='Migrate Discovery Engine to RAG Engine')
    parser.add_argument('--datastore-id', help='Discovery Engine Datastore ID')
    parser.add_argument('--target', choices=['rag_engine', 'bigquery'], default='rag_engine')
    parser.add_argument('--preserve-embeddings', action='store_true', default=True)
    parser.add_argument('--no-preserve-embeddings', dest='preserve_embeddings', action='store_false')
    parser.add_argument('--validate', action='store_true', default=True)
    parser.add_argument('--incremental', action='store_true', default=False)
    parser.add_argument('--wizard', action='store_true', help='Run interactive wizard')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without executing')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if not config.get('GOOGLE_CLOUD_PROJECT'):
        print("❌ Error: GOOGLE_CLOUD_PROJECT not set")
        print("Please set it in .env file or environment variable")
        return 1
    
    # Run wizard if requested
    if args.wizard or not args.datastore_id:
        wizard_config = migration_wizard()
        if not wizard_config:
            return 0
        
        args.datastore_id = wizard_config['datastore_id']
        args.target = wizard_config['target']
        args.preserve_embeddings = wizard_config['preserve_embeddings']
        args.validate = wizard_config['run_validation']
        args.incremental = wizard_config['use_incremental']
    
    # Initialize migrator
    print(f"\n🔧 Initializing migrator for project: {config['GOOGLE_CLOUD_PROJECT']}")
    migrator = DiscoveryToRAGMigrator(
        project_id=config['GOOGLE_CLOUD_PROJECT'],
        location=config['GOOGLE_CLOUD_REGION']
    )
    
    try:
        # Step 1: Extract documents
        print("\n📥 Step 1/4: Extracting from Discovery Engine...")
        documents = migrator.extract_from_discovery_engine(
            datastore_id=args.datastore_id,
            save_embeddings=args.preserve_embeddings
        )
        
        if not documents:
            print("❌ No documents found in Discovery Engine")
            return 1
        
        print(f"✅ Found {len(documents)} documents")
        
        # Estimate costs
        costs = estimate_costs(len(documents), args.preserve_embeddings)
        print(f"\n💰 Cost Estimate:")
        print(f"  • Embedding Generation: ${costs['embedding_generation']:.4f}")
        if args.target == 'rag_engine':
            print(f"  • RAG Engine Storage: ${costs['rag_engine_storage']:.4f}")
            print(f"  • Total: ${costs['total_rag']:.4f}")
        else:
            print(f"  • BigQuery Storage: ${costs['bigquery_storage']:.4f}")
            print(f"  • Total: ${costs['total_bigquery']:.4f}")
        
        if args.preserve_embeddings:
            saved = len(documents) * 0.0001
            print(f"  • 💚 Savings from preserved embeddings: ${saved:.4f}")
        
        if args.dry_run:
            print("\n🔍 DRY RUN - No actual migration performed")
            return 0
        
        # Step 2: Check compatibility
        print("\n🔬 Step 2/4: Checking embedding compatibility...")
        if documents[0].get('embedding'):
            compat = migrator.check_embedding_compatibility(
                documents[0].get('content', '')[:100],
                documents[0].get('embedding')
            )
            print(f"  • {compat['recommendation']}")
        
        # Step 3: Migrate
        print(f"\n🚀 Step 3/4: Migrating to {args.target.replace('_', ' ').title()}...")
        
        if args.incremental:
            # Incremental migration
            result = migrator.incremental_migration(
                source_datastore_id=args.datastore_id,
                target_corpus=f"migrated_{args.datastore_id}",
                checkpoint_file=f"migration_{args.datastore_id}_checkpoint.json"
            )
            print(f"✅ Incremental migration: {result['migrated']} new documents")
        else:
            # Full migration
            if args.target == 'rag_engine':
                corpus_name = migrator.migrate_to_rag_engine(
                    documents=documents,
                    corpus_name=f"migrated_{args.datastore_id}_{datetime.now().strftime('%Y%m%d')}",
                    preserve_embeddings=args.preserve_embeddings
                )
                print(f"✅ Created RAG corpus: {corpus_name}")
            else:
                table_name = migrator.migrate_to_bigquery(
                    documents=documents,
                    dataset_id="rag_migration",
                    table_id=f"migrated_{args.datastore_id}"
                )
                print(f"✅ Created BigQuery table: {table_name}")
        
        # Step 4: Validate
        if args.validate:
            print("\n✅ Step 4/4: Validating migration...")
            validation = migrator.validate_migration(
                source_datastore_id=args.datastore_id,
                target_corpus=corpus_name if args.target == 'rag_engine' else None
            )
            
            print(f"  • Average similarity: {validation['average_similarity']:.1%}")
            if validation['issues']:
                print("  ⚠️ Issues found:")
                for issue in validation['issues']:
                    print(f"    - {issue}")
            if validation['recommendations']:
                print("  💡 Recommendations:")
                for rec in validation['recommendations']:
                    print(f"    - {rec}")
        
        # Generate report
        print("\n📄 Generating migration report...")
        report = migrator.generate_migration_report("migration_report.json")
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"📊 Summary:")
        print(f"  • Documents migrated: {report['migration_stats']['migrated_documents']}")
        print(f"  • Embeddings reused: {report['migration_stats']['embeddings_reused']}")
        print(f"  • Embeddings generated: {report['migration_stats']['embeddings_generated']}")
        print(f"  • Cost saved: ${report['cost_analysis']['estimated_savings']:.4f}")
        print(f"  • Report saved: migration_report.json")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("  1. Check that APIs are enabled:")
        print("     gcloud services enable aiplatform.googleapis.com discoveryengine.googleapis.com")
        print("  2. Verify authentication:")
        print("     gcloud auth application-default login")
        print("  3. Check Discovery Engine datastore ID is correct")
        print("  4. Ensure you have necessary IAM permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())