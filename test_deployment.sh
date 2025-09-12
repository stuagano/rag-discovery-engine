#!/bin/bash

echo "🧪 COMPREHENSIVE DEPLOYMENT TEST SUITE"
echo "======================================"

PASSED=0
FAILED=0

# Test 1: Environment Variable Loading
echo "TEST 1: Environment Variable Loading"
set -a
source .env
set +a

if [ "$RAG_DEPLOYMENT_MODE" = "rag_engine" ]; then
    echo "✅ RAG_DEPLOYMENT_MODE loads correctly: $RAG_DEPLOYMENT_MODE"
    ((PASSED++))
else
    echo "❌ RAG_DEPLOYMENT_MODE failed: [$RAG_DEPLOYMENT_MODE]"
    ((FAILED++))
fi

if [ "$AUTO_ENABLE_APIS" = "true" ]; then
    echo "✅ AUTO_ENABLE_APIS loads correctly: $AUTO_ENABLE_APIS"
    ((PASSED++))
else
    echo "❌ AUTO_ENABLE_APIS failed: [$AUTO_ENABLE_APIS]"
    ((FAILED++))
fi

if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "✅ GOOGLE_CLOUD_PROJECT loads correctly: $GOOGLE_CLOUD_PROJECT"
    ((PASSED++))
else
    echo "❌ GOOGLE_CLOUD_PROJECT failed"
    ((FAILED++))
fi

echo

# Test 2: Deployment Mode Validation
echo "TEST 2: Deployment Mode Validation"
case "$RAG_DEPLOYMENT_MODE" in
    bigquery_basic|bigquery_enhanced|rag_engine|all)
        echo "✅ Valid deployment mode: $RAG_DEPLOYMENT_MODE"
        ((PASSED++))
        ;;
    "")
        echo "❌ Deployment mode is empty"
        ((FAILED++))
        ;;
    *)
        echo "❌ Invalid deployment mode: $RAG_DEPLOYMENT_MODE"
        ((FAILED++))
        ;;
esac

echo

# Test 3: Package Detection Logic
echo "TEST 3: Package Detection Logic"
if python3 -c "import sys; print('Python available:', sys.version)" 2>/dev/null; then
    echo "✅ Python 3 available"
    ((PASSED++))
    
    # Test package import simulation
    if python3 -c "import json; print('Basic imports work')" 2>/dev/null; then
        echo "✅ Basic Python imports work"
        ((PASSED++))
    else
        echo "❌ Python imports failed"
        ((FAILED++))
    fi
else
    echo "❌ Python 3 not available"
    ((FAILED++))
fi

echo

# Test 4: Script Configuration Check
echo "TEST 4: Script Configuration Check"
if [ -f "deploy_unified.sh" ]; then
    echo "✅ deploy_unified.sh exists"
    ((PASSED++))
    
    # Check if script has the optimization logic
    if grep -q "Required packages already installed" deploy_unified.sh; then
        echo "✅ Package optimization logic present"
        ((PASSED++))
    else
        echo "❌ Package optimization logic missing"
        ((FAILED++))
    fi
    
    # Check if script handles Cloud Shell
    if grep -q "CLOUD_SHELL" deploy_unified.sh; then
        echo "✅ Cloud Shell detection logic present"
        ((PASSED++))
    else
        echo "❌ Cloud Shell detection logic missing"
        ((FAILED++))
    fi
else
    echo "❌ deploy_unified.sh not found"
    ((FAILED++))
fi

echo

# Test 5: Dry-run Script Execution
echo "TEST 5: Dry-run Script Execution (Loading Only)"
# Extract just the config loading part and test it
CONFIG_TEST=$(bash -c '
set -a
source .env
set +a

# Simulate the script loading process
if [ -z "$RAG_DEPLOYMENT_MODE" ]; then
    echo "INVALID_MODE"
    exit 1
fi

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "MISSING_PROJECT"  
    exit 1
fi

echo "CONFIG_LOADED"
' 2>/dev/null)

if [ "$CONFIG_TEST" = "CONFIG_LOADED" ]; then
    echo "✅ Configuration loading simulation successful"
    ((PASSED++))
else
    echo "❌ Configuration loading failed: $CONFIG_TEST"
    ((FAILED++))
fi

echo

# Summary
echo "📊 TEST RESULTS SUMMARY"
echo "======================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo "Total: $((PASSED + FAILED))"

if [ $FAILED -eq 0 ]; then
    echo
    echo "🎉 ALL TESTS PASSED! Deployment should work correctly."
    exit 0
else
    echo
    echo "⚠️  Some tests failed. Please review the issues above."
    exit 1
fi