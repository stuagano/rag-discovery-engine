#!/bin/bash

# ========================================
# RAG Engine Deployment Script
# Deploy Google's managed RAG Engine service
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting RAG Engine Deployment...${NC}"

# === Step 1: Environment Check ===
echo -e "${BLUE}\n=== Step 1: Environment Check ===${NC}"

# Check if in Cloud Shell
if [ "$CLOUD_SHELL" = true ]; then
    echo -e "${GREEN}[INFO]${NC} Running in Google Cloud Shell"
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
else
    echo -e "${YELLOW}[WARN]${NC} Not in Cloud Shell - using local environment"
    # Get project from gcloud
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}[ERROR]${NC} No Google Cloud project found"
    echo "Please set your project: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Using project: $PROJECT_ID"

# === Step 2: Enable Required APIs ===
echo -e "${BLUE}\n=== Step 2: Enabling Required APIs ===${NC}"

APIS=(
    "aiplatform.googleapis.com"
    "storage.googleapis.com"
    "compute.googleapis.com"
)

for API in "${APIS[@]}"; do
    echo -n "Enabling $API... "
    if gcloud services enable $API --project=$PROJECT_ID 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}already enabled${NC}"
    fi
done

# === Step 3: Check Region Support ===
echo -e "${BLUE}\n=== Step 3: Region Configuration ===${NC}"

# RAG Engine supported regions (as of 2024)
SUPPORTED_REGIONS=("us-central1" "us-east4" "europe-west3" "europe-west4")
DEFAULT_REGION="us-central1"

# Check if .env exists and get region
if [ -f .env ]; then
    source .env
    REGION=${GOOGLE_CLOUD_REGION:-$DEFAULT_REGION}
else
    REGION=$DEFAULT_REGION
fi

# Verify region is supported
if [[ " ${SUPPORTED_REGIONS[@]} " =~ " ${REGION} " ]]; then
    echo -e "${GREEN}[INFO]${NC} Using region: $REGION (RAG Engine supported)"
else
    echo -e "${YELLOW}[WARN]${NC} Region $REGION not supported for RAG Engine"
    echo "Switching to default region: $DEFAULT_REGION"
    REGION=$DEFAULT_REGION
fi

# === Step 4: Create .env File ===
echo -e "${BLUE}\n=== Step 4: Environment Configuration ===${NC}"

if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_REGION=$REGION

# RAG Engine Configuration
RAG_CORPUS_NAME=manufacturing_docs
GCS_BUCKET=${PROJECT_ID}-rag-documents

# Vertex AI Models
VERTEX_EMBEDDING_MODEL=textembedding-gecko@003
VERTEX_GENERATION_MODEL=gemini-1.5-flash

# Document Processing
NUM_TEST_DOCS=10
CHUNK_SIZE=512
CHUNK_OVERLAP=100

# Performance Settings
BATCH_SIZE=100
EOF
    echo -e "${GREEN}[INFO]${NC} Created .env file"
else
    echo -e "${GREEN}[INFO]${NC} Using existing .env file"
fi

# === Step 5: Install Python Dependencies ===
echo -e "${BLUE}\n=== Step 5: Installing Dependencies ===${NC}"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install requirements
echo "Installing Python packages..."
pip install -r requirements.txt --quiet

echo -e "${GREEN}[INFO]${NC} Dependencies installed"

# === Step 6: Authenticate ===
echo -e "${BLUE}\n=== Step 6: Authentication ===${NC}"

if [ "$CLOUD_SHELL" = true ]; then
    echo -e "${GREEN}[INFO]${NC} Using Cloud Shell authentication"
else
    # Check if already authenticated
    if ! gcloud auth application-default print-access-token &>/dev/null; then
        echo "Please authenticate with Google Cloud..."
        gcloud auth application-default login
    else
        echo -e "${GREEN}[INFO]${NC} Already authenticated"
    fi
fi

# === Step 7: Deploy RAG Engine ===
echo -e "${BLUE}\n=== Step 7: Deploying RAG Engine ===${NC}"

echo "Running RAG Engine deployment..."
python3 src/rag_engine_implementation.py deploy

# === Step 8: Verification ===
echo -e "${BLUE}\n=== Step 8: Verification ===${NC}"

echo "Testing RAG Engine query..."
python3 src/rag_engine_implementation.py query "What are the maintenance procedures?"

# === Step 9: Show Status ===
echo -e "${BLUE}\n=== Step 9: RAG Engine Status ===${NC}"

python3 src/rag_engine_implementation.py status

# === Completion ===
echo -e "${GREEN}\n✅ RAG Engine Deployment Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Test queries: python3 src/rag_engine_implementation.py query 'your question'"
echo "2. Check status: python3 src/rag_engine_implementation.py status"
echo "3. List files: python3 src/rag_engine_implementation.py list"
echo ""
echo "RAG Engine Corpus: projects/$PROJECT_ID/locations/$REGION/ragCorpora/manufacturing_docs"
echo "GCS Bucket: gs://${PROJECT_ID}-rag-documents"
echo ""
echo -e "${YELLOW}Note: RAG Engine charges apply (~$200-500/month for typical usage)${NC}"