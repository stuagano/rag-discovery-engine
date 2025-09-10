#!/bin/bash

# BigQuery RAG Deployment Script for Cloud Shell
# One-command deployment: ./deploy.sh

set -e  # Exit on any error

echo "🚀 Starting BigQuery RAG Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Check if we're in Cloud Shell
if [[ -n "$CLOUD_SHELL" ]]; then
    print_status "Running in Google Cloud Shell ✓"
else
    print_warning "Not detected in Cloud Shell - manual auth may be required"
fi

# Step 1: Environment Setup
print_header "\n=== Step 1: Environment Setup ==="

# Check if .env exists
if [[ ! -f .env ]]; then
    print_warning ".env file not found"
    
    # Get project ID automatically if in Cloud Shell
    if [[ -n "$GOOGLE_CLOUD_PROJECT" ]]; then
        PROJECT_ID="$GOOGLE_CLOUD_PROJECT"
        print_status "Using Cloud Shell project: $PROJECT_ID"
    else
        echo "Enter your Google Cloud Project ID:"
        read -r PROJECT_ID
    fi
    
    # Create .env from template
    cp .env.example .env
    
    # Update project ID in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-project-id/$PROJECT_ID/g" .env
    else
        # Linux (Cloud Shell)
        sed -i "s/your-project-id/$PROJECT_ID/g" .env
    fi
    
    print_status "Created .env file with project: $PROJECT_ID"
else
    print_status ".env file found ✓"
fi

# Load environment variables
source .env

# Step 2: Install Python Dependencies
print_header "\n=== Step 2: Installing Dependencies ==="

if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PIP_CMD=pip3
else
    PYTHON_CMD=python
    PIP_CMD=pip
fi

print_status "Installing Python dependencies..."
$PIP_CMD install -r requirements.txt --quiet --user
print_status "Dependencies installed ✓"

# Step 3: Enable Required APIs
print_header "\n=== Step 3: Enabling GCP APIs ==="

print_status "Enabling required Google Cloud APIs..."

# List of required APIs
apis=(
    "bigquery.googleapis.com"
    "aiplatform.googleapis.com" 
    "storage.googleapis.com"
)

for api in "${apis[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        print_status "$api already enabled ✓"
    else
        print_status "Enabling $api..."
        gcloud services enable "$api"
        print_status "$api enabled ✓"
    fi
done

# Step 4: Set up BigQuery Dataset
print_header "\n=== Step 4: Creating BigQuery Resources ==="

print_status "Creating BigQuery dataset: $BIGQUERY_DATASET"

# Check if dataset exists
if bq ls "$GOOGLE_CLOUD_PROJECT:$BIGQUERY_DATASET" &>/dev/null; then
    print_warning "Dataset $BIGQUERY_DATASET already exists, skipping creation"
else
    bq mk --location="$GOOGLE_CLOUD_REGION" --dataset "$GOOGLE_CLOUD_PROJECT:$BIGQUERY_DATASET"
    print_status "BigQuery dataset created ✓"
fi

# Step 5: Deploy RAG System
print_header "\n=== Step 5: Deploying RAG System ==="

print_status "Starting RAG deployment..."

# Run the main deployment script
$PYTHON_CMD -c "
import os
import sys
sys.path.append('.')
from src.cloud_shell_rag import CloudShellRAG

# Initialize and deploy
rag = CloudShellRAG()
result = rag.deploy()

if result['success']:
    print('✅ RAG deployment successful!')
    print(f'Documents processed: {result[\"documents_processed\"]}')
    print(f'Embeddings generated: {result[\"embeddings_generated\"]}')
    print(f'Query endpoint: {result[\"endpoint\"]}')
else:
    print('❌ Deployment failed:', result['error'])
    sys.exit(1)
"

# Step 6: Run Tests
print_header "\n=== Step 6: Running Tests ==="

print_status "Running validation tests..."

$PYTHON_CMD -c "
import sys
sys.path.append('.')
from src.cloud_shell_rag import CloudShellRAG

rag = CloudShellRAG()
test_results = rag.run_tests()

print('Test Results:')
for test, result in test_results.items():
    status = '✅' if result['passed'] else '❌'
    print(f'{status} {test}: {result[\"message\"]}')

if all(r['passed'] for r in test_results.values()):
    print('\n🎉 All tests passed! RAG system is ready.')
else:
    print('\n⚠️  Some tests failed. Check logs above.')
"

# Step 7: Display Usage Instructions
print_header "\n=== Step 7: Usage Instructions ==="

cat << 'EOF'

🎉 RAG System Deployed Successfully!

Quick Test Commands:
──────────────────────

# Test a query
python -c "
from src.cloud_shell_rag import CloudShellRAG
rag = CloudShellRAG()
result = rag.query('How to maintain ion implanter equipment?')
print('Answer:', result['answer'])
print('Sources:', len(result['sources']))
"

# View system status
python -c "
from src.cloud_shell_rag import CloudShellRAG
rag = CloudShellRAG()
status = rag.get_status()
print('Status:', status)
"

# Run benchmarks
python src/benchmarks.py

Configuration:
─────────────
• Project ID: {PROJECT_ID}
• Dataset: {BIGQUERY_DATASET}
• Region: {GOOGLE_CLOUD_REGION}
• Embedding Model: {EMBEDDING_MODEL}

Next Steps:
──────────
1. Test queries with your manufacturing documents
2. Run benchmarks against Discovery Engine
3. Scale up with your production data

Documentation: docs/REAL_DATASET_IMPLEMENTATION.md

EOF

print_status "Deployment completed successfully! 🚀"