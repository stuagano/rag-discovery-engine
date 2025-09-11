#!/usr/bin/env python3
"""
Clean up problematic BigQuery datasets with duplicated names
This script helps resolve issues like 'rag_unified_basic_enhanced_basic_enhanced'
"""

import os
import sys
from typing import List
from google.cloud import bigquery
from dotenv import load_dotenv

def load_config():
    """Load configuration from .env file"""
    load_dotenv()
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        # Try to get from gcloud config
        import subprocess
        try:
            result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                                  capture_output=True, text=True)
            project_id = result.stdout.strip()
        except:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set or gcloud must be configured")
    
    return project_id

def find_rag_datasets(client: bigquery.Client, project_id: str) -> List[str]:
    """Find all RAG-related datasets with potential naming issues"""
    
    print("🔍 Scanning for RAG datasets...")
    
    datasets = []
    try:
        for dataset in client.list_datasets(project=project_id):
            dataset_name = dataset.dataset_id
            
            # Look for datasets with our naming patterns
            if 'rag' in dataset_name.lower():
                datasets.append(dataset_name)
                
                # Check for problematic naming patterns
                if '_basic_enhanced' in dataset_name or '_enhanced_basic' in dataset_name:
                    print(f"  ⚠️  Found problematic dataset: {dataset_name}")
                elif dataset_name.count('_basic') > 1 or dataset_name.count('_enhanced') > 1:
                    print(f"  ⚠️  Found duplicated suffix: {dataset_name}")
                else:
                    print(f"  ✓ Found normal dataset: {dataset_name}")
    
    except Exception as e:
        print(f"❌ Error listing datasets: {str(e)}")
        return []
    
    return datasets

def cleanup_dataset(client: bigquery.Client, project_id: str, dataset_name: str):
    """Clean up a specific dataset"""
    
    dataset_id = f"{project_id}.{dataset_name}"
    
    try:
        # Get dataset info
        dataset = client.get_dataset(dataset_id)
        
        # List tables
        tables = list(client.list_tables(dataset))
        print(f"   📊 Dataset contains {len(tables)} tables")
        
        # Ask for confirmation
        response = input(f"   Delete dataset '{dataset_name}' and all its tables? [y/N]: ")
        
        if response.lower() == 'y':
            # Delete dataset and all tables
            client.delete_dataset(dataset_id, delete_contents=True)
            print(f"   ✅ Deleted dataset: {dataset_name}")
            return True
        else:
            print(f"   ⏭️  Skipped dataset: {dataset_name}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error cleaning dataset {dataset_name}: {str(e)}")
        return False

def suggest_cleanup_plan(datasets: List[str]):
    """Suggest which datasets to clean up"""
    
    if not datasets:
        print("✅ No RAG datasets found")
        return []
    
    print(f"\n📋 Found {len(datasets)} RAG datasets:")
    
    problematic = []
    clean = []
    
    for dataset in datasets:
        if ('_basic_enhanced' in dataset or 
            '_enhanced_basic' in dataset or 
            dataset.count('_basic') > 1 or 
            dataset.count('_enhanced') > 1):
            problematic.append(dataset)
            print(f"  ❌ {dataset} (problematic naming)")
        else:
            clean.append(dataset)
            print(f"  ✅ {dataset} (normal)")
    
    if problematic:
        print(f"\n⚠️  Recommended action: Clean up {len(problematic)} problematic datasets")
        print("   These likely have naming issues from previous deployment runs")
        return problematic
    else:
        print(f"\n✅ All {len(datasets)} datasets have normal naming")
        return []

def main():
    """Main cleanup script"""
    
    print("🧹 BigQuery Dataset Cleanup Tool")
    print("=" * 50)
    
    try:
        # Load configuration
        project_id = load_config()
        print(f"📡 Project: {project_id}")
        
        # Initialize BigQuery client
        client = bigquery.Client(project=project_id)
        
        # Find RAG datasets
        datasets = find_rag_datasets(client, project_id)
        
        # Suggest cleanup plan
        problematic = suggest_cleanup_plan(datasets)
        
        if not problematic:
            print("\n🎉 No cleanup needed!")
            return
        
        print(f"\n🎯 Cleanup Plan:")
        for dataset in problematic:
            print(f"  • {dataset}")
        
        print("\n" + "=" * 50)
        response = input("Proceed with cleanup? [y/N]: ")
        
        if response.lower() != 'y':
            print("❌ Cleanup cancelled")
            return
        
        # Perform cleanup
        print("\n🚀 Starting cleanup...")
        
        cleaned = 0
        for dataset in problematic:
            print(f"\n🗑️  Processing: {dataset}")
            if cleanup_dataset(client, project_id, dataset):
                cleaned += 1
        
        print(f"\n✅ Cleanup complete! Removed {cleaned} of {len(problematic)} datasets")
        print("\n💡 You can now run deployment without naming conflicts:")
        print("   ./deploy_unified.sh")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
BigQuery Dataset Cleanup Tool

This script helps clean up problematic RAG datasets with duplicated names like:
- rag_unified_basic_enhanced_basic_enhanced_basic
- rag_poc_enhanced_basic_enhanced

Usage:
  python scripts/cleanup_datasets.py

The script will:
1. Scan for RAG-related datasets
2. Identify problematic naming patterns  
3. Suggest which datasets to clean up
4. Allow you to confirm before deletion

⚠️  Warning: This will permanently delete datasets and all their data!
""")
    else:
        main()