#!/usr/bin/env python3
"""
Show Response Format Examples
Displays the exact JSON structure returned by each RAG implementation
"""

import json
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

def print_colored(text, color):
    colors = {
        'green': '\033[0;32m',
        'blue': '\033[0;34m',
        'yellow': '\033[1;33m',
        'cyan': '\033[0;36m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def show_bigquery_basic_format():
    """Show BigQuery Basic response format"""
    print_colored("=== BigQuery Basic RAG Response Format ===", "cyan")
    
    example_response = {
        "query": "What are the maintenance procedures?",
        "answer": "Daily maintenance tasks include checking system pressure (10-15 PSI), monitoring temperature (20-25°C), inspecting safety valves, and recording all readings. Weekly tasks involve cleaning filters, testing emergency systems, calibrating sensors, and updating the maintenance log.",
        "sources": [
            "gs://project-bucket/documents/maintenance_guide_001.txt",
            "gs://project-bucket/documents/daily_procedures_002.txt"
        ],
        "contexts": [
            {
                "content": "Daily Tasks: Check system pressure: 10-15 PSI...",
                "document_id": "doc_001",
                "similarity_score": 0.892
            }
        ],
        "num_contexts": 3,
        "processing_time_ms": 245,
        "model": "gemini-1.5-flash"
    }
    
    print(json.dumps(example_response, indent=2))
    print()

def show_bigquery_enhanced_format():
    """Show BigQuery Enhanced response format"""
    print_colored("=== BigQuery Enhanced RAG Response Format ===", "cyan")
    
    example_response = {
        "query": "What are the maintenance procedures?",
        "answer": "Daily maintenance tasks include checking system pressure (10-15 PSI), monitoring temperature (20-25°C), inspecting safety valves, and recording all readings. Weekly tasks involve cleaning filters, testing emergency systems, calibrating sensors, and updating the maintenance log.",
        "confidence_score": 0.89,
        "sources": [
            {
                "document_id": "doc_001",
                "title": "Equipment Maintenance Guide",
                "similarity_score": 0.892,
                "importance_score": 0.95,
                "chunk_index": 2
            }
        ],
        "metadata": {
            "keywords": ["maintenance", "procedures", "daily", "weekly", "system"],
            "entities": ["pressure", "temperature", "filters", "sensors"],
            "document_types": ["maintenance_guide", "procedures"],
            "confidence_distribution": [0.12, 0.23, 0.65],
            "search_strategy": "hybrid",
            "reranking_applied": True
        },
        "num_contexts": 5,
        "processing_time": {
            "embedding_ms": 45,
            "search_ms": 123,
            "reranking_ms": 34,
            "generation_ms": 156,
            "total_ms": 358
        },
        "cache_hit": False,
        "model": "gemini-2.5-flash",
        "timestamp": "2025-01-11T10:30:45Z"
    }
    
    print(json.dumps(example_response, indent=2))
    print()

def show_rag_engine_format():
    """Show RAG Engine response format"""
    print_colored("=== Vertex AI RAG Engine Response Format ===", "cyan")
    
    example_response = {
        "query": "What are the maintenance procedures?",
        "answer": "Daily maintenance tasks include checking system pressure (10-15 PSI), monitoring temperature (20-25°C), inspecting safety valves, and recording all readings. Weekly tasks involve cleaning filters, testing emergency systems, calibrating sensors, and updating the maintenance log.",
        "contexts": [
            {
                "text": "Daily Tasks: Check system pressure: 10-15 PSI, Monitor temperature: 20-25°C...",
                "score": 0.892,
                "source": "gs://project-bucket/documents/maintenance_guide.txt",
                "metadata": {
                    "document_type": "maintenance",
                    "facility": "FAB-1",
                    "created_date": "2025-01-10T08:00:00Z"
                }
            }
        ],
        "num_contexts": 3,
        "confidence": 0.87,
        "sources": [
            "gs://project-bucket/documents/maintenance_guide.txt",
            "gs://project-bucket/documents/quality_procedures.txt"
        ],
        "timings": {
            "retrieval_ms": 234,
            "generation_ms": 445,
            "total_ms": 679
        },
        "model": "gemini-2.5-flash",
        "corpus": "projects/123456/locations/us-central1/ragCorpora/manufacturing_docs"
    }
    
    print(json.dumps(example_response, indent=2))
    print()

def show_api_endpoints():
    """Show API endpoint examples"""
    print_colored("=== API Integration Examples ===", "yellow")
    
    print("1. Command Line Usage:")
    print("   python3 src/bigquery_rag_enhanced.py query 'Your question here'")
    print("   python3 src/rag_engine_implementation.py query 'Your question here'")
    print()
    
    print("2. Python Integration:")
    python_example = '''
from src.bigquery_rag_enhanced import BigQueryRAGEnhanced

# Initialize
rag = BigQueryRAGEnhanced()

# Query
result = rag.query_enhanced("What are the maintenance procedures?")

# Extract key information
answer = result["answer"]
confidence = result["confidence_score"]
sources = result["sources"]
keywords = result["metadata"]["keywords"]

print(f"Answer: {answer}")
print(f"Confidence: {confidence}")
print(f"Sources: {len(sources)} documents")
print(f"Keywords: {', '.join(keywords)}")
'''
    print(python_example)
    
    print("3. Shell Script Integration:")
    shell_example = '''
#!/bin/bash
QUERY="What are the maintenance procedures?"
RESPONSE=$(python3 src/bigquery_rag_enhanced.py query "$QUERY" --json)

# Parse JSON response
ANSWER=$(echo "$RESPONSE" | jq -r '.answer')
CONFIDENCE=$(echo "$RESPONSE" | jq -r '.confidence_score')
NUM_SOURCES=$(echo "$RESPONSE" | jq '.sources | length')

echo "Answer: $ANSWER"
echo "Confidence: $CONFIDENCE"
echo "Sources: $NUM_SOURCES"
'''
    print(shell_example)

def show_error_formats():
    """Show error response formats"""
    print_colored("=== Error Response Formats ===", "yellow")
    
    error_examples = {
        "no_corpus": {
            "error": "No corpus available. Create or load a corpus first.",
            "error_code": "CORPUS_NOT_FOUND",
            "suggestion": "Please run 'deploy' first to create and populate the corpus"
        },
        "permission_denied": {
            "error": "Permission denied for RAG Engine access",
            "error_code": "PERMISSION_DENIED",
            "suggestion": "Grant roles/aiplatform.user role or use BigQuery Enhanced instead"
        },
        "query_failed": {
            "error": "Query processing failed",
            "error_code": "PROCESSING_ERROR",
            "details": "Context retrieval returned no results",
            "suggestion": "Try a different query or check if documents are properly indexed"
        }
    }
    
    for error_type, error_data in error_examples.items():
        print(f"\n{error_type.upper()}:")
        print(json.dumps(error_data, indent=2))
    print()

def main():
    print_colored("=" * 80, "cyan")
    print_colored("    RAG Discovery Engine - Response Format Examples", "cyan")
    print_colored("=" * 80, "cyan")
    print()
    
    # Show current mode
    current_mode = os.getenv("RAG_DEPLOYMENT_MODE", "not set")
    print_colored(f"Current RAG_DEPLOYMENT_MODE: {current_mode}", "green")
    print()
    
    # Show all formats
    show_bigquery_basic_format()
    show_bigquery_enhanced_format()
    show_rag_engine_format()
    show_api_endpoints()
    show_error_formats()
    
    print_colored("=" * 80, "cyan")
    print_colored("Summary of Key Differences:", "green")
    print_colored("=" * 80, "cyan")
    
    differences = {
        "BigQuery Basic": [
            "Simple response format",
            "Basic similarity scores",
            "Fast processing (~200-400ms)",
            "Cost effective"
        ],
        "BigQuery Enhanced": [
            "Rich metadata and analytics",
            "Confidence scoring",
            "Keyword/entity extraction",
            "Hybrid search capabilities",
            "Reranking support",
            "Detailed timing breakdown"
        ],
        "RAG Engine": [
            "Google managed service",
            "Advanced corpus management",
            "Built-in confidence scoring",
            "Automatic chunking/indexing",
            "Higher cost but enterprise features"
        ]
    }
    
    for impl, features in differences.items():
        print(f"\n{impl}:")
        for feature in features:
            print(f"  • {feature}")
    
    print()
    print_colored("=" * 80, "cyan")
    print_colored("✓ Response format documentation complete!", "green")
    print()
    print("To test with live data, run: ./scripts/test_rag_responses.sh")

if __name__ == "__main__":
    main()