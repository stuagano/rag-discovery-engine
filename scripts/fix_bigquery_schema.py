#!/usr/bin/env python3
"""
BigQuery Schema Fix Script
Fixes BigQuery tables that are missing the 'keywords' column and other enhanced features.
Run this if you're getting "Unrecognized name: keywords" errors.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from bigquery_rag_enhanced import BigQueryRAGEnhanced
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Fix BigQuery schema for enhanced RAG features"""
    
    # Load environment variables
    load_dotenv()
    
    print("🔧 BigQuery Schema Fix Tool")
    print("=" * 50)
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set in environment")
        print("Please set your project ID:")
        print("  export GOOGLE_CLOUD_PROJECT=your-project-id")
        return 1
    
    print(f"Project: {project_id}")
    print(f"Dataset: {os.getenv('BIGQUERY_DATASET', 'rag_unified')}")
    print()
    
    try:
        # Initialize BigQuery RAG Enhanced
        rag = BigQueryRAGEnhanced()
        
        # Check and fix table schema
        print("🔍 Checking table schema...")
        schema_fixed = rag.fix_table_schema()
        
        if schema_fixed:
            print("✅ Table schema fixed! The table has been recreated with all required columns.")
            print("⚠️  Note: All existing data has been removed. You'll need to re-run deployment to populate data.")
            print()
            print("Next steps:")
            print("1. Run deployment: ./deploy_unified.sh")
            print("2. Or process your documents again")
        else:
            print("✅ Table schema is already correct!")
            print("The 'keywords' column and other enhanced features are available.")
        
        print()
        print("🏁 Schema fix completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error fixing schema: {str(e)}")
        print()
        print("Manual fix options:")
        print("1. Delete the table manually in BigQuery console")
        print("2. Re-run deployment script")
        print("3. Or use this command:")
        print(f"   bq rm -f {project_id}:{os.getenv('BIGQUERY_DATASET', 'rag_unified')}.document_embeddings")
        return 1

if __name__ == "__main__":
    exit(main())