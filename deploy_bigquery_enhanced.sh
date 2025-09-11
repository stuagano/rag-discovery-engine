#!/bin/bash

# ========================================
# Enhanced BigQuery RAG Deployment Script
# Deploy cost-effective RAG with advanced features
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Enhanced BigQuery RAG Deployment...${NC}"

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
    "bigquery.googleapis.com"
    "aiplatform.googleapis.com"
    "storage.googleapis.com"
)

for API in "${APIS[@]}"; do
    echo -n "Enabling $API... "
    if gcloud services enable $API --project=$PROJECT_ID 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}already enabled${NC}"
    fi
done

# === Step 3: Configure Enhanced Features ===
echo -e "${BLUE}\n=== Step 3: Enhanced Features Configuration ===${NC}"

echo "Select features to enable:"
echo ""

# Hybrid Search
read -p "Enable Hybrid Search (semantic + keyword)? [Y/n]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    ENABLE_HYBRID_SEARCH="false"
    echo -e "${YELLOW}[INFO]${NC} Hybrid search disabled"
else
    ENABLE_HYBRID_SEARCH="true"
    echo -e "${GREEN}[INFO]${NC} Hybrid search enabled"
fi

# Query Caching
read -p "Enable Query Caching? [Y/n]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    ENABLE_CACHING="false"
    echo -e "${YELLOW}[INFO]${NC} Query caching disabled"
else
    ENABLE_CACHING="true"
    echo -e "${GREEN}[INFO]${NC} Query caching enabled"
fi

# Reranking
read -p "Enable Result Reranking (uses Gemini)? [Y/n]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    ENABLE_RERANKING="false"
    echo -e "${YELLOW}[INFO]${NC} Result reranking disabled"
else
    ENABLE_RERANKING="true"
    echo -e "${GREEN}[INFO]${NC} Result reranking enabled"
fi

# === Step 4: Create .env File ===
echo -e "${BLUE}\n=== Step 4: Environment Configuration ===${NC}"

cat > .env << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_REGION=us-central1

# BigQuery Configuration
BIGQUERY_DATASET=rag_enhanced

# Vertex AI Models
VERTEX_EMBEDDING_MODEL=textembedding-gecko@003
VERTEX_GENERATION_MODEL=gemini-1.5-flash

# Document Processing
NUM_TEST_DOCS=10
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
SPLIT_STRATEGY=recursive

# Performance Settings
BATCH_SIZE=100

# Enhanced Features
ENABLE_HYBRID_SEARCH=$ENABLE_HYBRID_SEARCH
ENABLE_CACHING=$ENABLE_CACHING
ENABLE_RERANKING=$ENABLE_RERANKING
CACHE_TTL_HOURS=24

# Deployment Settings
AUTO_CREATE_RESOURCES=true
VERBOSE_LOGGING=true
EOF

echo -e "${GREEN}[INFO]${NC} Created .env file with enhanced settings"

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

# === Step 7: Deploy Enhanced BigQuery RAG ===
echo -e "${BLUE}\n=== Step 7: Deploying Enhanced BigQuery RAG ===${NC}"

echo "Running enhanced deployment..."
python3 src/bigquery_rag_enhanced.py deploy

# === Step 8: Verification ===
echo -e "${BLUE}\n=== Step 8: Verification ===${NC}"

echo "Testing enhanced query..."
python3 src/bigquery_rag_enhanced.py query "What are the maintenance procedures?"

# === Step 9: Show Analytics ===
echo -e "${BLUE}\n=== Step 9: Analytics Summary ===${NC}"

python3 src/bigquery_rag_enhanced.py analytics

# === Step 10: Cost Estimate ===
echo -e "${BLUE}\n=== Step 10: Cost Estimate ===${NC}"

echo -e "${GREEN}Estimated Monthly Costs:${NC}"
echo "• BigQuery Storage: ~\$0.60 (30GB with metadata)"
echo "• BigQuery Queries: ~\$10-15 (1K queries/day)"
echo "• Vertex AI Embeddings: ~\$2 (one-time for 10K docs)"
echo "• Gemini Generation: ~\$10 (1K queries/day)"
if [ "$ENABLE_CACHING" = "true" ]; then
    echo "• Cache Storage: ~\$0.10"
fi
if [ "$ENABLE_RERANKING" = "true" ]; then
    echo "• Reranking (Gemini): ~\$2"
fi
echo -e "${YELLOW}Total: ~\$25-30/month${NC}"

# === Completion ===
echo -e "${GREEN}\n✅ Enhanced BigQuery RAG Deployment Complete!${NC}"
echo ""
echo "Features Enabled:"
[ "$ENABLE_HYBRID_SEARCH" = "true" ] && echo "  ✓ Hybrid Search (semantic + keyword)"
[ "$ENABLE_CACHING" = "true" ] && echo "  ✓ Query Caching (24-hour TTL)"
[ "$ENABLE_RERANKING" = "true" ] && echo "  ✓ Result Reranking (Gemini-powered)"
echo ""
echo "Next steps:"
echo "1. Test queries: python3 src/bigquery_rag_enhanced.py query 'your question'"
echo "2. View analytics: python3 src/bigquery_rag_enhanced.py analytics"
echo "3. Compare implementations: python3 scripts/compare_rag_solutions.py"
echo ""
echo "BigQuery Dataset: $PROJECT_ID.rag_enhanced"
echo ""
echo -e "${GREEN}💰 Cost: ~\$25-30/month (10x cheaper than RAG Engine)${NC}"