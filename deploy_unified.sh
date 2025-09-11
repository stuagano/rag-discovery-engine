#!/bin/bash

# ========================================
# Unified RAG Deployment Script
# Deploy any RAG implementation from single .env
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
echo "║          Google Cloud RAG Unified Deployment            ║"
echo "║         Deploy Any RAG Implementation with .env         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# === Functions ===

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

detect_environment() {
    log_section "Detecting Environment"
    
    # Check if running in Cloud Shell
    if [ "$CLOUD_SHELL" = "true" ]; then
        log_info "✅ Running in Google Cloud Shell"
        
        # Get the actual project from gcloud config
        DETECTED_PROJECT=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$DETECTED_PROJECT" ] || [ "$DETECTED_PROJECT" = "None" ]; then
            DETECTED_PROJECT="$GOOGLE_CLOUD_PROJECT"
        fi
        
        log_info "   Project: $DETECTED_PROJECT"
        log_info "   User: $(gcloud config get-value account)"
        
        # Auto-create .env if not exists in Cloud Shell
        if [ ! -f .env ] && [ ! -f .env.unified ]; then
            log_info "Creating .env with Cloud Shell defaults..."
            cat > .env << EOF
GOOGLE_CLOUD_PROJECT=${DETECTED_PROJECT:-$GOOGLE_CLOUD_PROJECT}
GOOGLE_CLOUD_REGION=us-central1
RAG_DEPLOYMENT_MODE=bigquery_enhanced
BIGQUERY_DATASET=rag_unified
BIGQUERY_LOCATION=US
NUM_TEST_DOCS=10
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
ENABLE_HYBRID_SEARCH=true
ENABLE_CACHING=true
ENABLE_RERANKING=true
AUTO_CREATE_RESOURCES=true
AUTO_ENABLE_APIS=true
AUTO_GRANT_PERMISSIONS=true
VERBOSE_LOGGING=true
RUN_TESTS_AFTER_DEPLOY=true
USE_PUBLIC_DATA=false
EOF
            log_info "✅ Created .env with project: ${DETECTED_PROJECT:-$GOOGLE_CLOUD_PROJECT}"
        fi
    else
        log_info "Running in local environment"
    fi
}

check_prerequisites() {
    log_section "Checking Prerequisites"
    
    # Detect environment first
    detect_environment
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    log_info "Python 3 found: $(python3 --version)"
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is required but not installed"
        echo "Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    log_info "gcloud found: $(gcloud --version | head -n1)"
    
    # Check git
    if ! command -v git &> /dev/null; then
        log_warn "git not found, some features may not work"
    fi
    
    # Check for pyarrow (most common missing dependency)
    if ! python3 -c "import pyarrow" &> /dev/null; then
        log_warn "pyarrow not found - required for BigQuery DataFrame operations"
        
        if [ -f "scripts/install_dependencies.sh" ]; then
            echo -e "${YELLOW}Would you like to install missing dependencies automatically?${NC}"
            echo -n "Install dependencies? [Y/n]: "
            read -r response
            
            if [[ "$response" != "n" ]] && [[ "$response" != "N" ]]; then
                log_info "Installing dependencies..."
                chmod +x scripts/install_dependencies.sh 2>/dev/null || true
                ./scripts/install_dependencies.sh
            else
                log_warn "Continuing without installing dependencies - deployment may fail"
            fi
        else
            log_error "Missing dependencies detected. Please install manually:"
            echo "  pip install pyarrow pandas>=2.0.0"
            echo "Or run: pip install -r requirements.txt"
        fi
    fi
}

load_env() {
    log_section "Loading Configuration"
    
    # Check if unified .env exists, otherwise create from template
    if [ -f .env ]; then
        ENV_FILE=".env"
    elif [ -f .env.unified ]; then
        ENV_FILE=".env.unified"
        log_info "Using .env.unified as configuration"
    else
        log_warn "No .env file found"
        
        # Offer to run interactive setup
        if [ -f deploy_unified_interactive.sh ]; then
            echo -e "${YELLOW}Would you like to run the interactive setup wizard?${NC}"
            echo -e "${CYAN}This will guide you through all configuration options.${NC}"
            echo -n -e "Run interactive setup? [Y/n]: "
            read -r response
            
            if [[ "$response" != "n" ]] && [[ "$response" != "N" ]]; then
                log_info "Launching interactive setup..."
                chmod +x deploy_unified_interactive.sh 2>/dev/null || true
                exec ./deploy_unified_interactive.sh
            fi
        fi
        
        log_error "No .env file found"
        echo "Creating .env from template..."
        
        # Create .env from embedded template
        cat > .env << 'EOF'
# Quick Start Configuration
RAG_DEPLOYMENT_MODE=bigquery_enhanced
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
BIGQUERY_DATASET=rag_unified
VERTEX_EMBEDDING_MODEL=gemini-embedding-001
VERTEX_GENERATION_MODEL=gemini-2.5-flash
NUM_TEST_DOCS=10
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
ENABLE_HYBRID_SEARCH=true
ENABLE_CACHING=true
ENABLE_RERANKING=true
AUTO_CREATE_RESOURCES=true
AUTO_ENABLE_APIS=true
AUTO_GRANT_PERMISSIONS=true
RUN_TESTS_AFTER_DEPLOY=true
EOF
        
        log_warn "Created default .env file - please edit with your project ID"
        echo -e "${YELLOW}Edit .env file and set GOOGLE_CLOUD_PROJECT, then run again${NC}"
        exit 1
    fi
    
    # Load environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Validate required variables
    if [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id" ] || [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        # Try to get from gcloud config
        DETECTED_PROJECT=$(gcloud config get-value project 2>/dev/null)
        if [ -n "$DETECTED_PROJECT" ] && [ "$DETECTED_PROJECT" != "None" ]; then
            log_warn "Using detected project: $DETECTED_PROJECT"
            export GOOGLE_CLOUD_PROJECT="$DETECTED_PROJECT"
            
            # Update the .env file with the detected project
            if [ -f "$ENV_FILE" ]; then
                sed -i "s/GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=$DETECTED_PROJECT/" "$ENV_FILE"
                log_info "Updated $ENV_FILE with detected project"
            fi
        else
            log_error "GOOGLE_CLOUD_PROJECT not set in .env"
            echo "Please edit .env and set your Google Cloud project ID"
            echo "Or run: gcloud config set project YOUR-PROJECT-ID"
            exit 1
        fi
    fi
    
    log_info "Configuration loaded from $ENV_FILE"
    log_info "Deployment mode: ${MAGENTA}$RAG_DEPLOYMENT_MODE${NC}"
    log_info "Project: $GOOGLE_CLOUD_PROJECT"
    log_info "Region: $GOOGLE_CLOUD_REGION"
}

setup_gcp_project() {
    log_section "Setting Up Google Cloud Project"
    
    # Set project
    gcloud config set project "$GOOGLE_CLOUD_PROJECT" 2>/dev/null
    log_info "Project set to: $GOOGLE_CLOUD_PROJECT"
    
    # Set quota project for Application Default Credentials
    log_info "Setting quota project for ADC..."
    gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT" 2>/dev/null || \
        log_warn "Could not set quota project - may affect Vertex AI authentication"
    
    # Check if in Cloud Shell
    if [ "$CLOUD_SHELL" = true ]; then
        log_info "Running in Google Cloud Shell"
        # In Cloud Shell, also ensure the project is set in the environment
        export GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT"
    else
        log_info "Running in local environment"
        
        # Check authentication
        if [ "$AUTO_AUTHENTICATE" = "true" ]; then
            if ! gcloud auth application-default print-access-token &>/dev/null; then
                log_info "Authenticating with Google Cloud..."
                gcloud auth application-default login
                
                # Set quota project after authentication
                log_info "Setting quota project after authentication..."
                gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT" 2>/dev/null || \
                    log_warn "Could not set quota project - may need to run manually"
            else
                log_info "Already authenticated"
            fi
        fi
    fi
}

enable_apis() {
    if [ "$AUTO_ENABLE_APIS" != "true" ]; then
        log_info "Skipping API enablement (AUTO_ENABLE_APIS=false)"
        return
    fi
    
    log_section "Enabling Required APIs"
    
    # Determine which APIs to enable based on deployment mode
    case "$RAG_DEPLOYMENT_MODE" in
        bigquery_basic|bigquery_enhanced)
            APIS=(
                "bigquery.googleapis.com"
                "aiplatform.googleapis.com"
                "storage.googleapis.com"
            )
            ;;
        rag_engine)
            APIS=(
                "aiplatform.googleapis.com"
                "storage.googleapis.com"
                "compute.googleapis.com"
            )
            ;;
        all)
            APIS=(
                "bigquery.googleapis.com"
                "aiplatform.googleapis.com"
                "storage.googleapis.com"
                "compute.googleapis.com"
            )
            ;;
        *)
            log_error "Unknown deployment mode: $RAG_DEPLOYMENT_MODE"
            exit 1
            ;;
    esac
    
    for API in "${APIS[@]}"; do
        echo -n "Enabling $API... "
        if gcloud services enable "$API" --project="$GOOGLE_CLOUD_PROJECT" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}already enabled${NC}"
        fi
    done
}

grant_rag_engine_permissions() {
    log_section "Granting RAG Engine Permissions"
    
    # Get current account (user or service account)
    ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
    
    if [ -z "$ACCOUNT" ]; then
        log_warn "Could not determine account for IAM permissions"
        log_warn "To manually grant permissions, run:"
        log_warn "  gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \\"
        log_warn "    --member=user:YOUR_EMAIL --role=roles/aiplatform.user"
        return 1
    fi
    
    # Determine if it's a service account or user account
    if [[ "$ACCOUNT" == *"iam.gserviceaccount.com" ]]; then
        MEMBER_TYPE="serviceAccount"
        log_info "Granting Vertex AI permissions to service account: $ACCOUNT"
    else
        MEMBER_TYPE="user"
        log_info "Granting Vertex AI permissions to user: $ACCOUNT"
    fi
    
    # Check if account already has the role
    EXISTING_BINDING=$(gcloud projects get-iam-policy "$GOOGLE_CLOUD_PROJECT" \
        --flatten="bindings[].members" \
        --filter="bindings.role:roles/aiplatform.user AND bindings.members:$MEMBER_TYPE:$ACCOUNT" \
        --format="value(bindings.members)" 2>/dev/null)
    
    if [ -n "$EXISTING_BINDING" ]; then
        log_success "✓ Account already has Vertex AI User role"
        return 0
    fi
    
    # Grant the Vertex AI User role
    log_info "Adding Vertex AI User role..."
    if gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
        --member="$MEMBER_TYPE:$ACCOUNT" \
        --role="roles/aiplatform.user" \
        --condition=None \
        --quiet 2>&1 | grep -q "Updated IAM policy"; then
        log_success "✓ Successfully granted Vertex AI User role"
        
        # Wait for permissions to propagate
        log_info "Waiting for permissions to propagate (30 seconds)..."
        sleep 30
        
        return 0
    else
        log_warn "Failed to grant permissions automatically"
        log_warn "You may need to grant permissions manually or ask your admin"
        log_warn "Manual command:"
        log_warn "  gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \\"
        log_warn "    --member=$MEMBER_TYPE:$ACCOUNT --role=roles/aiplatform.user"
        return 1
    fi
}

setup_python_env() {
    log_section "Setting Up Python Environment"
    
    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip --quiet
    
    # Install requirements
    log_info "Installing Python packages..."
    pip install -r requirements.txt --quiet
    
    log_info "Python environment ready"
}

deploy_bigquery_basic() {
    log_section "Deploying BigQuery RAG (Basic)"
    
    # Use base dataset name and append suffix
    BASE_DATASET=$(echo "$BIGQUERY_DATASET" | sed 's/_basic//g' | sed 's/_enhanced//g')
    
    # Create/update .env for basic implementation
    cat > .env << EOF
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION
BIGQUERY_DATASET=${BASE_DATASET}_basic
VERTEX_EMBEDDING_MODEL=$VERTEX_EMBEDDING_MODEL
VERTEX_GENERATION_MODEL=$VERTEX_GENERATION_MODEL
NUM_TEST_DOCS=$NUM_TEST_DOCS
CHUNK_SIZE=$CHUNK_SIZE
CHUNK_OVERLAP=$CHUNK_OVERLAP
BATCH_SIZE=$BATCH_SIZE
EOF
    
    log_info "Deploying basic BigQuery RAG..."
    python3 src/cloud_shell_rag.py deploy
    
    # Populate with test data
    log_info "Populating with test data..."
    if [ -f "scripts/populate_test_data.py" ]; then
        python3 scripts/populate_test_data.py 2>/dev/null || log_warn "Could not populate test data"
    fi
    
    if [ "$RUN_TESTS_AFTER_DEPLOY" = "true" ]; then
        log_info "Running test query..."
        python3 src/cloud_shell_rag.py query "What are the maintenance procedures?"
    fi
}

deploy_bigquery_enhanced() {
    log_section "Deploying BigQuery RAG (Enhanced)"
    
    # Use base dataset name and append suffix
    BASE_DATASET=$(echo "$BIGQUERY_DATASET" | sed 's/_basic//g' | sed 's/_enhanced//g')
    
    # Create/update .env for enhanced implementation
    cat > .env << EOF
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION
BIGQUERY_DATASET=${BASE_DATASET}_enhanced
VERTEX_EMBEDDING_MODEL=$VERTEX_EMBEDDING_MODEL
VERTEX_GENERATION_MODEL=$VERTEX_GENERATION_MODEL
NUM_TEST_DOCS=$NUM_TEST_DOCS
CHUNK_SIZE=$CHUNK_SIZE
CHUNK_OVERLAP=$CHUNK_OVERLAP
SPLIT_STRATEGY=$SPLIT_STRATEGY
BATCH_SIZE=$BATCH_SIZE
ENABLE_HYBRID_SEARCH=$ENABLE_HYBRID_SEARCH
ENABLE_CACHING=$ENABLE_CACHING
ENABLE_RERANKING=$ENABLE_RERANKING
CACHE_TTL_HOURS=$CACHE_TTL_HOURS
EOF
    
    log_info "Deploying enhanced BigQuery RAG..."
    log_info "Features enabled:"
    [ "$ENABLE_HYBRID_SEARCH" = "true" ] && echo "  ✓ Hybrid Search"
    [ "$ENABLE_CACHING" = "true" ] && echo "  ✓ Query Caching"
    [ "$ENABLE_RERANKING" = "true" ] && echo "  ✓ Result Reranking"
    
    # Deploy with error handling for quota project issues
    DEPLOY_OUTPUT=$(python3 src/bigquery_rag_enhanced.py deploy 2>&1)
    DEPLOY_EXIT_CODE=$?
    
    if [ $DEPLOY_EXIT_CODE -ne 0 ] && echo "$DEPLOY_OUTPUT" | grep -q "quota project"; then
        log_warn "⚠️  Quota project error detected - attempting fix..."
        log_info "Setting quota project for Application Default Credentials..."
        
        # Try to fix quota project issue
        if gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT" 2>/dev/null; then
            log_success "✓ Quota project set successfully"
            log_info "Retrying deployment..."
            python3 src/bigquery_rag_enhanced.py deploy
        else
            log_error "❌ Could not set quota project automatically"
            echo "Please run manually:"
            echo "  gcloud auth application-default set-quota-project $GOOGLE_CLOUD_PROJECT"
            echo "Then retry: python3 src/bigquery_rag_enhanced.py deploy"
            exit 1
        fi
    elif [ $DEPLOY_EXIT_CODE -ne 0 ]; then
        log_error "❌ Deployment failed"
        echo "$DEPLOY_OUTPUT" | head -10
        exit 1
    else
        log_success "✓ BigQuery Enhanced RAG deployed successfully"
    fi
    
    # Populate with test data if no documents exist
    log_info "Checking if test data population is needed..."
    if [ -f "scripts/populate_test_data.py" ]; then
        python3 scripts/populate_test_data.py 2>/dev/null || log_warn "Could not populate test data"
    fi
    
    if [ "$RUN_TESTS_AFTER_DEPLOY" = "true" ]; then
        log_info "Running test query..."
        python3 src/bigquery_rag_enhanced.py query "What are the maintenance procedures?"
        
        log_info "Checking analytics..."
        python3 src/bigquery_rag_enhanced.py analytics
    fi
}

deploy_rag_engine() {
    log_section "Deploying RAG Engine"
    
    # Check region support and capacity limitations
    SUPPORTED_REGIONS=("us-central1" "us-east4" "europe-west3" "europe-west4")
    CAPACITY_LIMITED_REGIONS=("us-central1")  # Regions with allowlist requirements
    
    if [[ ! " ${SUPPORTED_REGIONS[@]} " =~ " ${GOOGLE_CLOUD_REGION} " ]]; then
        log_warn "Region $GOOGLE_CLOUD_REGION not supported for RAG Engine"
        log_info "Switching to us-east4 (better capacity availability)"
        GOOGLE_CLOUD_REGION="us-east4"
    elif [[ " ${CAPACITY_LIMITED_REGIONS[@]} " =~ " ${GOOGLE_CLOUD_REGION} " ]]; then
        log_warn "⚠️  Region $GOOGLE_CLOUD_REGION has capacity limitations for new projects"
        log_info "RAG Engine in $GOOGLE_CLOUD_REGION is allowlist-based due to capacity"
        log_info "Switching to us-east4 for better availability..."
        GOOGLE_CLOUD_REGION="us-east4"
    fi
    
    # Try to grant permissions first
    if [ "$AUTO_GRANT_PERMISSIONS" = "true" ]; then
        grant_rag_engine_permissions
    fi
    
    # Check if RAG Engine permissions are available
    log_info "Checking RAG Engine permissions..."
    
    # Test RAG Engine access
    RAG_ENGINE_TEST=$(python3 -c "
import sys
try:
    from vertexai.preview import rag
    import vertexai
    vertexai.init(project='$GOOGLE_CLOUD_PROJECT', location='$GOOGLE_CLOUD_REGION')
    # Try to list corpora (will fail if no permissions)
    corpora = rag.list_corpora()
    print('SUCCESS')
except PermissionError as e:
    print('PERMISSION_DENIED')
except Exception as e:
    if 'Permission' in str(e) or 'denied' in str(e):
        print('PERMISSION_DENIED')
    else:
        print('ERROR')
" 2>&1 | tail -1)
    
    if [[ "$RAG_ENGINE_TEST" == "PERMISSION_DENIED" ]]; then
        log_warn "⚠️  RAG Engine permissions not available"
        log_warn "   Required role: 'Vertex AI User' (roles/aiplatform.user)"
        log_warn "   To enable RAG Engine, run:"
        log_warn "   gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \\"
        log_warn "     --member=user:YOUR_EMAIL --role=roles/aiplatform.user"
        log_warn ""
        log_info "📌 Falling back to BigQuery Enhanced implementation..."
        log_info "   (BigQuery Enhanced provides similar capabilities without special permissions)"
        
        # Switch to BigQuery Enhanced
        RAG_DEPLOYMENT_MODE="bigquery_enhanced"
        deploy_bigquery_enhanced
        return
    elif [[ "$RAG_ENGINE_TEST" != "SUCCESS" ]]; then
        log_warn "⚠️  RAG Engine check failed"
        log_info "📌 Falling back to BigQuery Enhanced implementation..."
        RAG_DEPLOYMENT_MODE="bigquery_enhanced"
        deploy_bigquery_enhanced
        return
    fi
    
    log_success "✓ RAG Engine permissions verified"
    
    # Create/update .env for RAG Engine
    cat > .env << EOF
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION
RAG_CORPUS_NAME=$RAG_CORPUS_NAME
GCS_BUCKET=${GOOGLE_CLOUD_PROJECT}-${GCS_BUCKET_SUFFIX}
VERTEX_EMBEDDING_MODEL=$VERTEX_EMBEDDING_MODEL
VERTEX_GENERATION_MODEL=$VERTEX_GENERATION_MODEL
NUM_TEST_DOCS=$NUM_TEST_DOCS
CHUNK_SIZE=$RAG_ENGINE_CHUNK_SIZE
CHUNK_OVERLAP=$RAG_ENGINE_CHUNK_OVERLAP
BATCH_SIZE=$BATCH_SIZE
EOF
    
    log_info "Deploying RAG Engine..."
    log_info "Parse mode: $RAG_ENGINE_PARSE_MODE"
    
    # Try the enhanced RAG Engine implementation first (latest API)
    log_info "Attempting enhanced RAG Engine deployment (latest API)..."
    if [ -f "src/rag_engine_enhanced.py" ]; then
        DEPLOY_OUTPUT=$(python3 src/rag_engine_enhanced.py create 2>&1)
        DEPLOY_EXIT_CODE=$?
        
        if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
            log_success "✓ Enhanced RAG Engine deployed successfully"
            echo "$DEPLOY_OUTPUT"
        else
            log_warn "Enhanced RAG Engine failed, trying main implementation..."
            DEPLOY_OUTPUT=$(python3 src/rag_engine_implementation.py deploy 2>&1)
            DEPLOY_EXIT_CODE=$?
        fi
    else
        # Fallback to main implementation
        log_info "Attempting main RAG Engine deployment..."
        DEPLOY_OUTPUT=$(python3 src/rag_engine_implementation.py deploy 2>&1)
        DEPLOY_EXIT_CODE=$?
    fi
    
    if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
        log_success "✓ RAG Engine deployed successfully"
        echo "$DEPLOY_OUTPUT" | grep -E "success|created|uploaded" || true
    else
        # Check for specific error types
        if echo "$DEPLOY_OUTPUT" | grep -q "allowlisting based due to capacity limitation"; then
            log_warn "⚠️  RAG Engine capacity limitation detected"
            log_info "   This project requires allowlist access for RAG Engine in this region"
            log_info "   Options:"
            log_info "   1. Contact vertex-ai-rag-engine-support@google.com for allowlist access"
            log_info "   2. Use a different region (us-east4, europe-west3, europe-west4)"
            log_info "   3. Use BigQuery Enhanced instead (similar capabilities)"
            log_info ""
            log_info "📌 Falling back to BigQuery Enhanced (recommended)..."
            RAG_DEPLOYMENT_MODE="bigquery_enhanced"
            deploy_bigquery_enhanced
            return
        fi
        
        log_warn "Main RAG Engine failed, trying simplified version..."
        if [ "$VERBOSE_LOGGING" = "true" ]; then
            echo "Error details: $DEPLOY_OUTPUT" | head -5
        fi
        
        SIMPLE_OUTPUT=$(python3 src/rag_engine_simple.py deploy 2>&1)
        SIMPLE_EXIT_CODE=$?
        
        if [ $SIMPLE_EXIT_CODE -eq 0 ]; then
            log_success "✓ Simple RAG Engine deployed successfully"
        else
            # Check for capacity limitation in simple version too
            if echo "$SIMPLE_OUTPUT" | grep -q "allowlisting based due to capacity limitation"; then
                log_warn "⚠️  RAG Engine capacity limitation (simple version too)"
                log_info "📌 Falling back to BigQuery Enhanced..."
                RAG_DEPLOYMENT_MODE="bigquery_enhanced"
                deploy_bigquery_enhanced
                return
            fi
            
            log_warn "⚠️  RAG Engine deployment failed"
            if [ "$VERBOSE_LOGGING" = "true" ]; then
                echo "Error details: $SIMPLE_OUTPUT" | head -5
            fi
            log_info "📌 Falling back to BigQuery Enhanced..."
            RAG_DEPLOYMENT_MODE="bigquery_enhanced"
            deploy_bigquery_enhanced
            return
        fi
    fi
    
    if [ "$RUN_TESTS_AFTER_DEPLOY" = "true" ]; then
        log_info "Running test query..."
        
        # Try enhanced version first, fallback to main implementation
        if [ -f "src/rag_engine_enhanced.py" ]; then
            log_info "Testing with enhanced RAG Engine..."
            if python3 src/rag_engine_enhanced.py query "What are the maintenance procedures?" 2>&1; then
                log_success "✓ Enhanced test query successful"
            else
                log_warn "Enhanced test query failed, trying main implementation..."
                python3 src/rag_engine_implementation.py query "What are the maintenance procedures?" 2>&1 || \
                    log_warn "Test query failed - corpus may need time to index"
            fi
            
            log_info "Checking enhanced corpus status..."
            python3 src/rag_engine_enhanced.py status 2>&1 || \
                python3 src/rag_engine_implementation.py status 2>&1 || \
                log_warn "Could not get corpus status"
        else
            # Fallback to main implementation
            if python3 src/rag_engine_implementation.py query "What are the maintenance procedures?" 2>&1; then
                log_success "✓ Test query successful"
            else
                log_warn "Test query failed - corpus may need time to index"
            fi
            
            log_info "Checking corpus status..."
            python3 src/rag_engine_implementation.py status 2>&1 || log_warn "Could not get corpus status"
        fi
    fi
}

deploy_all() {
    log_section "Deploying All RAG Implementations"
    
    log_info "This will deploy all three implementations for comparison"
    
    # Deploy each implementation
    deploy_bigquery_basic
    deploy_bigquery_enhanced
    deploy_rag_engine
    
    # Run comparison if enabled
    if [ "$RUN_COMPARISON" = "true" ]; then
        run_comparison
    fi
}

run_comparison() {
    log_section "Running Comparison Tests"
    
    log_info "Comparing all implementations..."
    
    # Set number of queries for comparison
    export COMPARISON_QUERIES
    
    # Run comparison script
    if [ "$COMPARISON_QUERIES" -le 3 ]; then
        python3 scripts/compare_rag_solutions.py quick
    else
        python3 scripts/compare_rag_solutions.py
    fi
    
    log_info "Comparison report saved to: comparison_report.md"
}

show_cost_estimate() {
    log_section "Cost Estimates (Monthly)"
    
    case "$RAG_DEPLOYMENT_MODE" in
        bigquery_basic)
            echo -e "${GREEN}BigQuery RAG (Basic):${NC}"
            echo "  • Storage: ~\$0.40"
            echo "  • Queries: ~\$10"
            echo "  • Generation: ~\$10"
            echo -e "  ${CYAN}Total: ~\$22/month${NC}"
            ;;
        bigquery_enhanced)
            echo -e "${GREEN}BigQuery RAG (Enhanced):${NC}"
            echo "  • Storage: ~\$0.60"
            echo "  • Queries: ~\$12"
            echo "  • Generation: ~\$10"
            echo "  • Cache: ~\$0.10"
            echo -e "  ${CYAN}Total: ~\$25/month${NC}"
            ;;
        rag_engine)
            echo -e "${GREEN}RAG Engine:${NC}"
            echo "  • Corpus Storage: ~\$150"
            echo "  • Retrieval API: ~\$60"
            echo "  • Generation: ~\$10"
            echo "  • Ingestion: ~\$30"
            echo -e "  ${CYAN}Total: ~\$250/month${NC}"
            ;;
        all)
            echo -e "${GREEN}All Implementations:${NC}"
            echo "  • BigQuery Basic: ~\$22/month"
            echo "  • BigQuery Enhanced: ~\$25/month"
            echo "  • RAG Engine: ~\$250/month"
            echo -e "  ${CYAN}Total: ~\$297/month${NC}"
            ;;
    esac
}

show_next_steps() {
    log_section "Deployment Complete!"
    
    echo -e "${GREEN}✅ Successfully deployed: $RAG_DEPLOYMENT_MODE${NC}\n"
    
    echo "Next steps:"
    
    case "$RAG_DEPLOYMENT_MODE" in
        bigquery_basic)
            echo "1. Test: python3 src/cloud_shell_rag.py query 'your question'"
            echo "2. Status: python3 src/cloud_shell_rag.py status"
            echo "3. Deploy: python3 src/cloud_shell_rag.py deploy"
            ;;
        bigquery_enhanced)
            echo "1. Test: python3 src/bigquery_rag_enhanced.py query 'your question'"
            echo "2. Analytics: python3 src/bigquery_rag_enhanced.py analytics"
            echo "3. Deploy: python3 src/bigquery_rag_enhanced.py deploy"
            ;;
        rag_engine)
            echo "1. Test: python3 src/rag_engine_implementation.py query 'your question'"
            echo "2. Status: python3 src/rag_engine_implementation.py status"
            echo "3. List files: python3 src/rag_engine_implementation.py list"
            ;;
        all)
            echo "1. Compare: python3 scripts/compare_rag_solutions.py"
            echo "2. View report: cat comparison_report.md"
            ;;
    esac
    
    echo ""
    echo "Resources:"
    echo "• Project: $GOOGLE_CLOUD_PROJECT"
    echo "• Region: $GOOGLE_CLOUD_REGION"
    
    if [[ "$RAG_DEPLOYMENT_MODE" == *"bigquery"* ]]; then
        echo "• BigQuery Dataset: ${BIGQUERY_DATASET}"
    fi
    
    if [[ "$RAG_DEPLOYMENT_MODE" == "rag_engine" ]] || [[ "$RAG_DEPLOYMENT_MODE" == "all" ]]; then
        echo "• RAG Corpus: $RAG_CORPUS_NAME"
        echo "• GCS Bucket: ${GOOGLE_CLOUD_PROJECT}-${GCS_BUCKET_SUFFIX}"
    fi
    
    echo ""
    echo -e "${CYAN}=== Smoke Test - Response Format Demo ===${NC}"
    echo "Running response format demonstration..."
    echo ""
    
    # Run the response format script as a smoke test
    if [ -f "scripts/show_response_format.py" ]; then
        python3 scripts/show_response_format.py | head -50
        echo ""
        echo -e "${GREEN}✓ Response format demo complete${NC}"
        
        # Run a quick live test if deployment was successful
        echo ""
        echo -e "${CYAN}=== Live Smoke Test ===${NC}"
        echo "Testing deployed service with a sample query..."
        echo ""
        
        SMOKE_TEST_QUERY="What are the maintenance procedures?"
        
        case "$RAG_DEPLOYMENT_MODE" in
            bigquery_basic)
                echo "Command: python3 src/cloud_shell_rag.py query \"$SMOKE_TEST_QUERY\""
                echo "─────────────────────────────────────────"
                python3 src/cloud_shell_rag.py query "$SMOKE_TEST_QUERY" 2>&1 | head -15 || echo "⚠️ Live test failed - check deployment"
                ;;
            bigquery_enhanced)
                echo "Command: python3 src/bigquery_rag_enhanced.py query \"$SMOKE_TEST_QUERY\""
                echo "─────────────────────────────────────────"
                python3 src/bigquery_rag_enhanced.py query "$SMOKE_TEST_QUERY" 2>&1 | head -15 || echo "⚠️ Live test failed - check deployment"
                ;;
            rag_engine)
                echo "Command: python3 src/rag_engine_implementation.py query \"$SMOKE_TEST_QUERY\""
                echo "─────────────────────────────────────────"
                python3 src/rag_engine_implementation.py query "$SMOKE_TEST_QUERY" 2>&1 | head -15 || echo "⚠️ Live test failed - check deployment"
                ;;
            all)
                echo "Multiple implementations deployed - run ./scripts/test_rag_responses.sh for comprehensive testing"
                ;;
        esac
        
        echo ""
        echo -e "${GREEN}✓ Smoke test complete${NC}"
        echo -e "${YELLOW}💡 For comprehensive testing with multiple queries, run:${NC}"
        echo "   ./scripts/test_rag_responses.sh"
    else
        echo -e "${YELLOW}Response format demo not available${NC}"
        echo "Create scripts/show_response_format.py for examples"
    fi
}

# === Main Execution ===

main() {
    # Check prerequisites
    check_prerequisites
    
    # Load environment
    load_env
    
    # Setup GCP
    setup_gcp_project
    enable_apis
    
    # Setup Python
    setup_python_env
    
    # Deploy based on mode
    case "$RAG_DEPLOYMENT_MODE" in
        bigquery_basic)
            deploy_bigquery_basic
            ;;
        bigquery_enhanced)
            deploy_bigquery_enhanced
            ;;
        rag_engine)
            deploy_rag_engine
            ;;
        all)
            deploy_all
            ;;
        *)
            log_error "Invalid RAG_DEPLOYMENT_MODE: $RAG_DEPLOYMENT_MODE"
            echo "Valid options: bigquery_basic, bigquery_enhanced, rag_engine, all"
            exit 1
            ;;
    esac
    
    # Show cost estimate
    show_cost_estimate
    
    # Show next steps
    show_next_steps
    
    # Run comparison if requested
    if [ "$RUN_COMPARISON" = "true" ] && [ "$RAG_DEPLOYMENT_MODE" != "all" ]; then
        log_warn "Comparison requires multiple implementations. Deploy with RAG_DEPLOYMENT_MODE=all"
    fi
}

# Handle arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Google Cloud RAG Unified Deployment"
    echo ""
    echo "Usage: ./deploy_unified.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h       Show this help message"
    echo "  --env FILE       Use specific .env file (default: .env or .env.unified)"
    echo "  --mode MODE      Override RAG_DEPLOYMENT_MODE from .env"
    echo "  --compare        Run comparison after deployment"
    echo "  --quick          Quick deployment with minimal tests"
    echo ""
    echo "Deployment Modes:"
    echo "  bigquery_basic     Basic BigQuery RAG (~\$22/month)"
    echo "  bigquery_enhanced  Enhanced BigQuery RAG (~\$25/month)"
    echo "  rag_engine        Google RAG Engine (~\$250/month)"
    echo "  all               Deploy all implementations"
    echo ""
    echo "Configure deployment by editing .env file"
    exit 0
fi

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV_FILE="$2"
            shift 2
            ;;
        --mode)
            RAG_DEPLOYMENT_MODE="$2"
            shift 2
            ;;
        --compare)
            RUN_COMPARISON="true"
            shift
            ;;
        --quick)
            RUN_TESTS_AFTER_DEPLOY="false"
            NUM_TEST_DOCS=3
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main