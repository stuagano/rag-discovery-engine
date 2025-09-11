# Troubleshooting Guide

## Common Issues and Solutions

### ❌ Error: "Unrecognized name: keywords" in BigQuery

**Problem**: You're getting a BigQuery error about an unrecognized column name `keywords`.

**Cause**: Your BigQuery table was created before the enhanced features were added and is missing required columns.

**Solutions**:

#### Option 1: Automatic Fix (Recommended)
```bash
# Use the built-in fix command
python src/bigquery_rag_enhanced.py fix-schema

# Then redeploy
./deploy_unified.sh
```

#### Option 2: Manual Fix Script
```bash
# Run the dedicated fix script
python scripts/fix_bigquery_schema.py

# Then redeploy
./deploy_unified.sh
```

#### Option 3: Manual BigQuery Console
1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. Navigate to your dataset (usually `rag_unified`)
3. Delete the `document_embeddings` table
4. Re-run deployment: `./deploy_unified.sh`

#### Option 4: Command Line
```bash
# Delete the table manually
bq rm -f YOUR_PROJECT_ID:rag_unified.document_embeddings

# Redeploy
./deploy_unified.sh
```

---

### ❌ Error: "GOOGLE_CLOUD_PROJECT not set"

**Problem**: The deployment script can't find your Google Cloud project.

**Solutions**:

#### For Cloud Shell Users:
```bash
# Use the Cloud Shell setup wizard
./scripts/cloud_shell_setup.sh
```

#### For Local Development:
```bash
# Set your project
gcloud config set project YOUR-PROJECT-ID

# Or export the environment variable
export GOOGLE_CLOUD_PROJECT=YOUR-PROJECT-ID

# Then run deployment
./deploy_unified.sh
```

---

### ❌ Error: API not enabled

**Problem**: Required Google Cloud APIs are not enabled.

**Solution**:
```bash
# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com

# Or use the deployment script with auto-enable
# Set AUTO_ENABLE_APIS=true in .env
./deploy_unified.sh
```

---

### ❌ Error: Permission denied

**Problem**: Your account doesn't have the required permissions.

**Required Roles**:
- BigQuery Admin (or BigQuery Data Editor + BigQuery Job User)
- Vertex AI User
- Storage Admin (if using RAG Engine)

**Solution**:
```bash
# Check your permissions
gcloud auth list
gcloud projects get-iam-policy YOUR-PROJECT-ID

# Contact your Google Cloud administrator to grant required roles
```

---

### ❌ Error: Model not found (gemini-2.5-flash or gemini-embedding-001)

**Problem**: The specified AI models are not available in your region.

**Solution**:
```bash
# Check model availability in your region
# Edit .env and update models:
VERTEX_GENERATION_MODEL=gemini-1.5-flash
VERTEX_EMBEDDING_MODEL=textembedding-gecko@003

# Or change region to us-central1
GOOGLE_CLOUD_REGION=us-central1
```

---

### ❌ Performance Issues

**Problem**: Queries are slow or timing out.

**Solutions**:

1. **Check BigQuery location**:
   ```bash
   # Ensure your dataset is in the same region as your queries
   # Edit .env:
   BIGQUERY_LOCATION=US  # For multi-region
   # or
   BIGQUERY_LOCATION=us-central1  # For specific region
   ```

2. **Optimize chunk size**:
   ```bash
   # Reduce chunk size for faster processing
   # Edit .env:
   CHUNK_SIZE=500
   CHUNK_OVERLAP=100
   ```

3. **Disable features temporarily**:
   ```bash
   # Edit .env to disable heavy features:
   ENABLE_HYBRID_SEARCH=false
   ENABLE_RERANKING=false
   ```

---

### ❌ Out of Memory Errors

**Problem**: Python process runs out of memory during document processing.

**Solutions**:

1. **Reduce batch size**:
   ```bash
   # Edit .env:
   BATCH_SIZE=10  # Down from 100
   NUM_TEST_DOCS=5  # Down from 10
   ```

2. **Process documents in smaller chunks**:
   ```bash
   # Use smaller chunk sizes
   CHUNK_SIZE=500
   MAX_WORKERS=2
   ```

---

### 🔍 Debug Mode

Enable verbose logging to troubleshoot issues:

```bash
# Set in .env:
VERBOSE_LOGGING=true

# Or run with debug:
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.bigquery_rag_enhanced import BigQueryRAGEnhanced
rag = BigQueryRAGEnhanced()
result = rag.query_enhanced('test query')
print(result)
"
```

---

### 🆘 Getting Help

If you're still having issues:

1. **Check the logs**: Look for specific error messages
2. **Verify environment**: Ensure all environment variables are set correctly
3. **Test step by step**: Try individual components (BigQuery, Vertex AI, etc.)
4. **Check quotas**: Ensure you haven't hit API quotas
5. **Try minimal setup**: Start with basic deployment, then add features

**Environment Check Script**:
```bash
# Quick environment verification
python -c "
import os
from google.cloud import bigquery, aiplatform
print('Project:', os.getenv('GOOGLE_CLOUD_PROJECT'))
print('Region:', os.getenv('GOOGLE_CLOUD_REGION'))
try:
    bq = bigquery.Client()
    print('BigQuery: ✓')
except Exception as e:
    print('BigQuery: ❌', str(e))
try:
    aiplatform.init()
    print('Vertex AI: ✓')
except Exception as e:
    print('Vertex AI: ❌', str(e))
"
```