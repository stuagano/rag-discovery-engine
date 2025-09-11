#!/bin/bash

# ========================================
# Interactive Unified RAG Deployment Script
# Ensures all values are set before deployment
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       🚀 Interactive RAG Deployment Wizard 🚀           ║"
echo "║         Never fails due to missing configuration        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# === Helper Functions ===

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}━━━ $1 ━━━${NC}"
}

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        echo -n -e "${CYAN}$prompt${NC} [${GREEN}$default${NC}]: "
    else
        echo -n -e "${CYAN}$prompt${NC}: "
    fi
    
    read -r user_input
    
    if [ -z "$user_input" ]; then
        eval "$var_name='$default'"
    else
        eval "$var_name='$user_input'"
    fi
}

# === Detect Environment ===
detect_environment() {
    log_section "Environment Detection"
    
    # Check if running in Cloud Shell
    if [ "$CLOUD_SHELL" = "true" ]; then
        log_info "✅ Running in Google Cloud Shell"
        IN_CLOUD_SHELL=true
        
        # Get actual project from gcloud config, not environment variable
        DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$DEFAULT_PROJECT" ] || [ "$DEFAULT_PROJECT" = "None" ]; then
            DEFAULT_PROJECT="$GOOGLE_CLOUD_PROJECT"
        fi
        
        # If still no project or it's the placeholder, prompt user
        if [ -z "$DEFAULT_PROJECT" ] || [ "$DEFAULT_PROJECT" = "your-project-id" ]; then
            DEFAULT_PROJECT=""
        fi
        
        DEFAULT_REGION="us-central1"
        if [ -n "$DEFAULT_PROJECT" ]; then
            log_info "   Detected project: $DEFAULT_PROJECT"
        else
            log_warn "   No project detected - will prompt for it"
        fi
    else
        log_info "Running in local environment"
        IN_CLOUD_SHELL=false
        
        # Try to get project from gcloud
        DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
        DEFAULT_REGION="us-central1"
        
        if [ -n "$DEFAULT_PROJECT" ] && [ "$DEFAULT_PROJECT" != "None" ]; then
            log_info "   Detected project from gcloud: $DEFAULT_PROJECT"
        fi
    fi
}

# === Load Existing Configuration ===
load_existing_config() {
    log_section "Checking Existing Configuration"
    
    CONFIG_LOADED=false
    
    # Check for existing .env files
    if [ -f .env ]; then
        log_info "Found existing .env file"
        source .env
        CONFIG_LOADED=true
    elif [ -f .env.unified ]; then
        log_info "Found .env.unified file"
        # Source it but handle potential errors
        set +e
        source .env.unified 2>/dev/null
        set -e
        CONFIG_LOADED=true
    elif [ -f .env.example ]; then
        log_info "Found .env.example template"
        cp .env.example .env
        source .env
        CONFIG_LOADED=true
    fi
    
    if [ "$CONFIG_LOADED" = "true" ]; then
        log_info "Loaded existing configuration"
    else
        log_warn "No existing configuration found - will create new"
    fi
}

# === Interactive Configuration ===
configure_interactively() {
    log_section "Interactive Configuration"
    echo -e "${YELLOW}Let's set up your RAG deployment. Press Enter to use defaults.${NC}\n"
    
    # 1. Google Cloud Project
    if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id" ]; then
        GOOGLE_CLOUD_PROJECT="$DEFAULT_PROJECT"
    fi
    
    # Keep prompting until we get a valid project ID
    while [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id" ]; do
        echo -e "${RED}Google Cloud Project is required!${NC}"
        echo -e "${YELLOW}Tip: You can find your project ID with: gcloud projects list${NC}"
        prompt_with_default "Enter your Google Cloud Project ID" "" GOOGLE_CLOUD_PROJECT
    done
    
    # Verify the project exists and set it in gcloud
    if gcloud projects describe "$GOOGLE_CLOUD_PROJECT" &>/dev/null; then
        log_info "✅ Project verified: $GOOGLE_CLOUD_PROJECT"
        gcloud config set project "$GOOGLE_CLOUD_PROJECT" 2>/dev/null
    else
        log_warn "Could not verify project $GOOGLE_CLOUD_PROJECT - continuing anyway"
    fi
    
    # 2. Region
    if [ -z "$GOOGLE_CLOUD_REGION" ]; then
        GOOGLE_CLOUD_REGION="$DEFAULT_REGION"
    fi
    prompt_with_default "Google Cloud Region" "${GOOGLE_CLOUD_REGION:-us-central1}" GOOGLE_CLOUD_REGION
    
    # 3. Deployment Mode
    echo -e "\n${CYAN}Choose your RAG implementation:${NC}"
    echo "  1) BigQuery RAG Enhanced (💰 $25/month - Recommended)"
    echo "  2) Vertex AI RAG Engine (💰 $250/month - Fully Managed)"
    echo "  3) Both (For comparison)"
    echo "  4) BigQuery Basic (💰 $20/month - Simple)"
    
    if [ -z "$RAG_DEPLOYMENT_MODE" ]; then
        RAG_DEPLOYMENT_MODE="bigquery_enhanced"
    fi
    
    prompt_with_default "Select [1-4]" "1" DEPLOYMENT_CHOICE
    
    case "$DEPLOYMENT_CHOICE" in
        1) RAG_DEPLOYMENT_MODE="bigquery_enhanced" ;;
        2) RAG_DEPLOYMENT_MODE="rag_engine" ;;
        3) RAG_DEPLOYMENT_MODE="all" ;;
        4) RAG_DEPLOYMENT_MODE="bigquery_basic" ;;
        *) RAG_DEPLOYMENT_MODE="bigquery_enhanced" ;;
    esac
    
    log_info "Selected: $RAG_DEPLOYMENT_MODE"
    
    # 4. BigQuery Configuration (if applicable)
    if [[ "$RAG_DEPLOYMENT_MODE" == *"bigquery"* ]] || [[ "$RAG_DEPLOYMENT_MODE" == "all" ]]; then
        echo -e "\n${CYAN}BigQuery Configuration:${NC}"
        prompt_with_default "BigQuery Dataset Name" "${BIGQUERY_DATASET:-rag_unified}" BIGQUERY_DATASET
        prompt_with_default "BigQuery Location" "${BIGQUERY_LOCATION:-US}" BIGQUERY_LOCATION
    fi
    
    # 5. RAG Engine Configuration (if applicable)
    if [[ "$RAG_DEPLOYMENT_MODE" == "rag_engine" ]] || [[ "$RAG_DEPLOYMENT_MODE" == "all" ]]; then
        echo -e "\n${CYAN}RAG Engine Configuration:${NC}"
        prompt_with_default "RAG Corpus Name" "${RAG_CORPUS_NAME:-manufacturing_docs}" RAG_CORPUS_NAME
        prompt_with_default "GCS Bucket Suffix" "${GCS_BUCKET_SUFFIX:-rag-documents}" GCS_BUCKET_SUFFIX
    fi
    
    # 6. Model Selection
    echo -e "\n${CYAN}AI Model Configuration:${NC}"
    echo "Available embedding models:"
    echo "  1) textembedding-gecko@003 (Recommended)"
    echo "  2) textembedding-gecko@002"
    echo "  3) textembedding-gecko-multilingual@001"
    
    prompt_with_default "Select embedding model [1-3]" "1" EMBED_CHOICE
    
    case "$EMBED_CHOICE" in
        1) VERTEX_EMBEDDING_MODEL="textembedding-gecko@003" ;;
        2) VERTEX_EMBEDDING_MODEL="textembedding-gecko@002" ;;
        3) VERTEX_EMBEDDING_MODEL="textembedding-gecko-multilingual@001" ;;
        *) VERTEX_EMBEDDING_MODEL="textembedding-gecko@003" ;;
    esac
    
    echo "Available generation models:"
    echo "  1) gemini-2.5-flash (Latest, Best Performance)"
    echo "  2) gemini-1.5-flash (Stable, Fast)"
    echo "  3) gemini-1.5-pro (Better Quality, Higher Cost)"
    echo "  4) text-bison@002 (Legacy)"
    
    prompt_with_default "Select generation model [1-4]" "1" GEN_CHOICE
    
    case "$GEN_CHOICE" in
        1) VERTEX_GENERATION_MODEL="gemini-2.5-flash" ;;
        2) VERTEX_GENERATION_MODEL="gemini-1.5-flash" ;;
        3) VERTEX_GENERATION_MODEL="gemini-1.5-pro" ;;
        4) VERTEX_GENERATION_MODEL="text-bison@002" ;;
        *) VERTEX_GENERATION_MODEL="gemini-2.5-flash" ;;
    esac
    
    # 7. Advanced Features (BigQuery Enhanced only)
    if [[ "$RAG_DEPLOYMENT_MODE" == "bigquery_enhanced" ]] || [[ "$RAG_DEPLOYMENT_MODE" == "all" ]]; then
        echo -e "\n${CYAN}Advanced Features:${NC}"
        
        prompt_with_default "Enable Hybrid Search (semantic + keyword)? [y/n]" "y" HYBRID_CHOICE
        ENABLE_HYBRID_SEARCH=$([ "$HYBRID_CHOICE" = "y" ] && echo "true" || echo "false")
        
        prompt_with_default "Enable Query Caching (24hr)? [y/n]" "y" CACHE_CHOICE
        ENABLE_CACHING=$([ "$CACHE_CHOICE" = "y" ] && echo "true" || echo "false")
        
        prompt_with_default "Enable Result Reranking with Gemini? [y/n]" "y" RERANK_CHOICE
        ENABLE_RERANKING=$([ "$RERANK_CHOICE" = "y" ] && echo "true" || echo "false")
    fi
    
    # 8. Document Configuration
    echo -e "\n${CYAN}Document Processing:${NC}"
    prompt_with_default "Number of test documents" "${NUM_TEST_DOCS:-10}" NUM_TEST_DOCS
    prompt_with_default "Chunk size (characters)" "${CHUNK_SIZE:-1000}" CHUNK_SIZE
    prompt_with_default "Chunk overlap (characters)" "${CHUNK_OVERLAP:-200}" CHUNK_OVERLAP
    
    # 9. Deployment Options
    echo -e "\n${CYAN}Deployment Options:${NC}"
    
    prompt_with_default "Auto-enable required APIs? [y/n]" "y" AUTO_API
    AUTO_ENABLE_APIS=$([ "$AUTO_API" = "y" ] && echo "true" || echo "false")
    
    prompt_with_default "Run tests after deployment? [y/n]" "y" RUN_TESTS
    RUN_TESTS_AFTER_DEPLOY=$([ "$RUN_TESTS" = "y" ] && echo "true" || echo "false")
    
    prompt_with_default "Use verbose logging? [y/n]" "y" VERBOSE
    VERBOSE_LOGGING=$([ "$VERBOSE" = "y" ] && echo "true" || echo "false")
    
    # 10. Data Sources
    echo -e "\n${CYAN}Data Sources:${NC}"
    echo "  1) Synthetic manufacturing data (default)"
    echo "  2) Load public data (Wikipedia, ArXiv, etc.)"
    echo "  3) Use your own data"
    
    prompt_with_default "Select data source [1-3]" "1" DATA_CHOICE
    
    case "$DATA_CHOICE" in
        1) USE_PUBLIC_DATA="false" ;;
        2) USE_PUBLIC_DATA="true" ;;
        3) USE_PUBLIC_DATA="custom" ;;
        *) USE_PUBLIC_DATA="false" ;;
    esac
}

# === Save Configuration ===
save_configuration() {
    log_section "Saving Configuration"
    
    # Create .env file with all settings
    cat > .env << EOF
# ========================================
# RAG Configuration - Generated $(date)
# ========================================

# === GOOGLE CLOUD CONFIGURATION ===
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION

# === DEPLOYMENT SELECTION ===
RAG_DEPLOYMENT_MODE=$RAG_DEPLOYMENT_MODE

# === BIGQUERY CONFIGURATION ===
BIGQUERY_DATASET=${BIGQUERY_DATASET:-rag_unified}
BIGQUERY_LOCATION=${BIGQUERY_LOCATION:-US}

# === RAG ENGINE CONFIGURATION ===
RAG_CORPUS_NAME=${RAG_CORPUS_NAME:-manufacturing_docs}
RAG_CORPUS_DESCRIPTION="Manufacturing documentation RAG corpus"
GCS_BUCKET_SUFFIX=${GCS_BUCKET_SUFFIX:-rag-documents}

# === VERTEX AI MODELS ===
VERTEX_EMBEDDING_MODEL=$VERTEX_EMBEDDING_MODEL
VERTEX_GENERATION_MODEL=$VERTEX_GENERATION_MODEL

# === DOCUMENT PROCESSING ===
NUM_TEST_DOCS=$NUM_TEST_DOCS
CHUNK_SIZE=$CHUNK_SIZE
CHUNK_OVERLAP=$CHUNK_OVERLAP
SPLIT_STRATEGY=recursive

# === PERFORMANCE SETTINGS ===
BATCH_SIZE=${BATCH_SIZE:-100}
MAX_WORKERS=${MAX_WORKERS:-4}

# === ENHANCED FEATURES ===
ENABLE_HYBRID_SEARCH=${ENABLE_HYBRID_SEARCH:-true}
ENABLE_CACHING=${ENABLE_CACHING:-true}
ENABLE_RERANKING=${ENABLE_RERANKING:-true}
CACHE_TTL_HOURS=${CACHE_TTL_HOURS:-24}

# === DEPLOYMENT OPTIONS ===
AUTO_CREATE_RESOURCES=true
AUTO_ENABLE_APIS=$AUTO_ENABLE_APIS
AUTO_AUTHENTICATE=true
VERBOSE_LOGGING=$VERBOSE_LOGGING
RUN_TESTS_AFTER_DEPLOY=$RUN_TESTS_AFTER_DEPLOY

# === DATA SOURCES ===
USE_PUBLIC_DATA=$USE_PUBLIC_DATA
DATA_SOURCE=${DATA_SOURCE:-synthetic}
PUBLIC_DATA_SOURCES=${PUBLIC_DATA_SOURCES:-wikipedia,arxiv,patents,nist}
MAX_DOCS_PER_SOURCE=${MAX_DOCS_PER_SOURCE:-5}

# === COST LIMITS (Optional) ===
MONTHLY_BUDGET_USD=${MONTHLY_BUDGET_USD:-50}

# === FEATURE FLAGS ===
ENABLE_ANALYTICS=${ENABLE_ANALYTICS:-true}
ENABLE_MONITORING=${ENABLE_MONITORING:-true}
EOF
    
    log_info "✅ Configuration saved to .env"
}

# === Display Configuration Summary ===
display_summary() {
    log_section "Configuration Summary"
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Project:${NC} $GOOGLE_CLOUD_PROJECT"
    echo -e "${CYAN}Region:${NC} $GOOGLE_CLOUD_REGION"
    echo -e "${CYAN}Deployment:${NC} $RAG_DEPLOYMENT_MODE"
    echo -e "${CYAN}Embedding Model:${NC} $VERTEX_EMBEDDING_MODEL"
    echo -e "${CYAN}Generation Model:${NC} $VERTEX_GENERATION_MODEL"
    
    if [[ "$RAG_DEPLOYMENT_MODE" == *"bigquery"* ]]; then
        echo -e "${CYAN}BigQuery Dataset:${NC} $BIGQUERY_DATASET"
    fi
    
    if [[ "$RAG_DEPLOYMENT_MODE" == "rag_engine" ]] || [[ "$RAG_DEPLOYMENT_MODE" == "all" ]]; then
        echo -e "${CYAN}RAG Corpus:${NC} $RAG_CORPUS_NAME"
    fi
    
    # Cost estimate
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${YELLOW}💰 Estimated Monthly Costs:${NC}"
    
    case "$RAG_DEPLOYMENT_MODE" in
        bigquery_basic)
            echo "  • Storage: \$0.02"
            echo "  • Queries: \$0.10"
            echo "  • Embeddings: \$10.00"
            echo -e "  ${GREEN}• TOTAL: ~\$10-20/month${NC}"
            ;;
        bigquery_enhanced)
            echo "  • Storage: \$0.02"
            echo "  • Queries: \$0.10"
            echo "  • Embeddings: \$10.00"
            echo "  • Caching: Saves 50%+"
            echo -e "  ${GREEN}• TOTAL: ~\$20-30/month${NC}"
            ;;
        rag_engine)
            echo "  • RAG Corpus: \$10.00"
            echo "  • Queries: \$0.20"
            echo "  • API Calls: \$15.00"
            echo -e "  ${GREEN}• TOTAL: ~\$200-300/month${NC}"
            ;;
        all)
            echo "  • BigQuery: ~\$25/month"
            echo "  • RAG Engine: ~\$250/month"
            echo -e "  ${GREEN}• TOTAL: ~\$275/month${NC}"
            ;;
    esac
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# === Confirm Deployment ===
confirm_deployment() {
    echo -e "\n${YELLOW}Ready to deploy with the above configuration.${NC}"
    echo -n -e "${CYAN}Proceed with deployment? [Y/n]:${NC} "
    read -r CONFIRM
    
    if [[ "$CONFIRM" == "n" ]] || [[ "$CONFIRM" == "N" ]]; then
        log_warn "Deployment cancelled. Configuration saved to .env"
        log_info "Run './deploy_unified.sh' when ready to deploy"
        exit 0
    fi
}

# === Main Execution ===
main() {
    # Step 1: Detect environment
    detect_environment
    
    # Step 2: Load existing config if available
    load_existing_config
    
    # Step 3: Interactive configuration
    configure_interactively
    
    # Step 4: Save configuration
    save_configuration
    
    # Step 5: Display summary
    display_summary
    
    # Step 6: Confirm deployment
    confirm_deployment
    
    # Step 7: Execute deployment
    log_section "Starting Deployment"
    log_info "Launching deployment with saved configuration..."
    
    # Make sure deploy_unified.sh is executable
    chmod +x deploy_unified.sh 2>/dev/null || true
    
    # Run the main deployment script
    ./deploy_unified.sh
}

# === Script Entry Point ===
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Interactive RAG Deployment Wizard"
    echo ""
    echo "This script guides you through configuring and deploying a RAG system."
    echo "It ensures all required values are set before deployment."
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "The script will:"
    echo "  1. Detect your environment (Cloud Shell or local)"
    echo "  2. Load any existing configuration"
    echo "  3. Interactively prompt for all settings"
    echo "  4. Save configuration to .env"
    echo "  5. Deploy your chosen RAG implementation"
    exit 0
fi

# Check for required commands
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI is required but not installed"
    log_info "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Run main function
main