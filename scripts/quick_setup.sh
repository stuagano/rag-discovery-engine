#!/bin/bash

# Quick Setup Script for RAG Discovery Engine Implementation
# This script sets up the environment and validates prerequisites

set -e  # Exit on any error

echo "🚀 RAG Discovery Engine - Quick Setup"
echo "======================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    print_status "Python $python_version is compatible"
else
    print_error "Python 3.8+ required, found: $python_version"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📈 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python packages..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_status "Python packages installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

# Create necessary directories
echo "📁 Creating project directories..."
directories=("data" "logs" "results" "reports" "benchmarks" "config")

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    else
        print_status "Directory exists: $dir"
    fi
done

# Check Google Cloud CLI
echo "🌩️ Checking Google Cloud CLI..."
if command -v gcloud &> /dev/null; then
    gcloud_version=$(gcloud --version | head -n1 | awk '{print $4}')
    print_status "Google Cloud CLI $gcloud_version found"
    
    # Check authentication
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
        active_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
        print_status "Authenticated as: $active_account"
    else
        print_warning "No active authentication found"
        echo "Run: gcloud auth login"
        echo "Or: gcloud auth application-default login"
    fi
else
    print_warning "Google Cloud CLI not found"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
fi

# Validate project structure
echo "📋 Validating project structure..."
required_files=("run_complete_implementation.py" "src/execution_coordinator.py" "src/dataset_acquisition.py" "src/bigquery_rag_pipeline.py" "src/migration_pipeline.py" "src/benchmark_framework.py")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "Found: $file"
    else
        print_error "Missing: $file"
    fi
done

# Environment variables check
echo "🔐 Checking environment variables..."
if [ ! -z "$GOOGLE_CLOUD_PROJECT" ]; then
    print_status "GOOGLE_CLOUD_PROJECT: $GOOGLE_CLOUD_PROJECT"
else
    print_warning "GOOGLE_CLOUD_PROJECT not set"
    echo "Consider setting: export GOOGLE_CLOUD_PROJECT=your-project-id"
fi

if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    print_status "GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
else
    print_warning "GOOGLE_APPLICATION_CREDENTIALS not set"
    echo "For service account auth, set: export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json"
fi

# Display next steps
echo ""
echo "🎯 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Set your GCP project ID:"
echo "   export GOOGLE_CLOUD_PROJECT=your-project-id"
echo ""
echo "2. Run a quick demo:"
echo "   python run_complete_implementation.py --project-id your-project-id --mode demo"
echo ""
echo "3. Or validate your setup:"
echo "   python run_complete_implementation.py --project-id your-project-id --validate-only"
echo ""
echo "4. For full implementation:"
echo "   python run_complete_implementation.py --project-id your-project-id --mode full"
echo ""
echo "📚 For more options:"
echo "   python run_complete_implementation.py --help-examples"
echo ""

print_status "Setup script completed successfully!"