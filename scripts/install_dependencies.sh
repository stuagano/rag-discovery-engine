#!/bin/bash

# ========================================
# Install Dependencies for Cloud Shell
# Fixes missing pyarrow and other deps
# ========================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${GREEN}"
echo "╔══════════════════════════════════════╗"
echo "║      🔧 Installing Dependencies     ║"
echo "╚══════════════════════════════════════╝"
echo -e "${NC}"

# Check if we're in a virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    log_info "Virtual environment detected: $VIRTUAL_ENV"
    PYTHON_CMD="pip"
elif [ -f "venv/bin/activate" ]; then
    log_info "Activating project virtual environment..."
    source venv/bin/activate
    PYTHON_CMD="pip"
elif [ -f "../venv/bin/activate" ]; then
    log_info "Activating parent virtual environment..."
    source ../venv/bin/activate
    PYTHON_CMD="pip"
else
    # Try pip3 with --user flag for system install
    log_warn "No virtual environment found, installing with --user flag"
    PYTHON_CMD="pip3 install --user"
fi

# Install pyarrow specifically (most common missing dependency)
log_info "Installing pyarrow (required for BigQuery DataFrame uploads)..."
if $PYTHON_CMD install pyarrow>=12.0.0; then
    log_info "✅ pyarrow installed successfully"
else
    log_error "Failed to install pyarrow"
    exit 1
fi

# Install other potentially missing dependencies
log_info "Installing other common missing dependencies..."

DEPS=(
    "google-cloud-bigquery>=3.11.0"
    "google-cloud-aiplatform>=1.35.0" 
    "google-cloud-storage>=2.10.0"
    "pandas>=2.0.0"
    "numpy>=1.24.0"
    "tqdm>=4.65.0"
    "python-dotenv>=1.0.0"
)

for dep in "${DEPS[@]}"; do
    log_info "Installing $dep..."
    if $PYTHON_CMD install "$dep" --quiet; then
        echo "  ✓ $dep"
    else
        log_warn "  ⚠ Failed to install $dep (may already be installed)"
    fi
done

# Verify key packages
log_info "Verifying key packages..."

# Test pyarrow
if python3 -c "import pyarrow; print(f'pyarrow {pyarrow.__version__}')" 2>/dev/null; then
    echo "  ✅ pyarrow working"
else
    log_error "  ❌ pyarrow not working"
fi

# Test BigQuery
if python3 -c "from google.cloud import bigquery; print('BigQuery client available')" 2>/dev/null; then
    echo "  ✅ BigQuery client working"
else
    log_warn "  ⚠ BigQuery client may have issues (check gcloud auth)"
fi

# Test pandas
if python3 -c "import pandas as pd; print(f'pandas {pd.__version__}')" 2>/dev/null; then
    echo "  ✅ pandas working"
else
    log_error "  ❌ pandas not working"
fi

echo ""
log_info "✅ Dependency installation complete!"
log_info "You can now run the deployment script:"
echo -e "${YELLOW}  ./deploy_unified.sh${NC}"