# 🚀 Google Cloud Shell Quick Start

## ✅ Yes, this works end-to-end in Cloud Shell!

This project is **specifically designed** for Google Cloud Shell deployment. Here's your 2-minute setup:

## 📋 Prerequisites
- Google Cloud Project with billing enabled
- Cloud Shell (already has everything installed!)

## 🎯 One-Command Cloud Shell Deployment

### Step 1: Open Cloud Shell
[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/stuagano/rag-discovery-engine.git)

Or manually:
```bash
# In Cloud Shell terminal
git clone https://github.com/stuagano/rag-discovery-engine.git
cd rag-discovery-engine
```

### Step 2: Quick Deploy (Choose One)

#### Option A: BigQuery RAG (Recommended - $25/month)
```bash
# One command - uses current project automatically
echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" > .env
echo "RAG_DEPLOYMENT_MODE=bigquery_enhanced" >> .env
./deploy_unified.sh
```

#### Option B: RAG Engine ($250/month)
```bash
# One command - uses current project automatically
echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" > .env
echo "RAG_DEPLOYMENT_MODE=rag_engine" >> .env
./deploy_unified.sh
```

#### Option C: Interactive Setup (Recommended for First Time)
```bash
# Run the interactive walkthrough
python interactive_walkthrough.py
```

## 🔧 What Cloud Shell Provides (Already Installed!)

✅ **Pre-installed Tools:**
- Python 3.9+
- gcloud CLI (authenticated)
- git
- All Google Cloud SDKs
- pip/virtualenv

✅ **Auto-configured:**
- `$GOOGLE_CLOUD_PROJECT` environment variable
- Authentication (no need for `gcloud auth login`)
- Project selection
- API enablement permissions

## 📊 What Happens Automatically

The deployment script (`deploy_unified.sh`) will:

1. **Detect Cloud Shell environment** ✓
2. **Use your current project** ✓
3. **Enable required APIs:**
   - Vertex AI API
   - BigQuery API
   - Cloud Storage API
4. **Create virtual environment** ✓
5. **Install dependencies** ✓
6. **Deploy chosen RAG system** ✓
7. **Load sample documents** ✓
8. **Run test queries** ✓
9. **Show cost estimates** ✓

## 🎯 Cloud Shell Specific Features

### Automatic Project Detection
```bash
# The script automatically uses:
PROJECT_ID=$GOOGLE_CLOUD_PROJECT  # Already set in Cloud Shell
REGION=us-central1                 # Default, can override
```

### Pre-authenticated
```bash
# No need for:
# gcloud auth login              # ❌ Not needed
# gcloud auth application-default # ❌ Not needed
```

### Persistent Storage
```bash
# Your files persist in Cloud Shell between sessions
# Located at: ~/rag-discovery-engine/
```

## 💡 Quick Test After Deployment

```bash
# Test BigQuery RAG
python src/bigquery_rag_enhanced.py query "What are the maintenance procedures?"

# Test RAG Engine
python src/rag_engine_implementation.py query "What are the maintenance procedures?"

# Check costs
python src/bigquery_rag_enhanced.py analytics

# Run comparison
python scripts/compare_rag_solutions.py
```

## 🔄 Migration from Discovery Engine

If you have an existing Discovery Engine:

```bash
# Interactive migration wizard
python scripts/migrate_discovery_to_rag.py --wizard

# Or direct migration
python scripts/migrate_discovery_to_rag.py \
  --datastore-id YOUR_DATASTORE_ID \
  --preserve-embeddings
```

## 📁 Cloud Shell File Structure

After cloning, you'll have:
```
~/rag-discovery-engine/
├── deploy_unified.sh          # Master deployment script
├── .env                        # Your configuration (created)
├── src/
│   ├── bigquery_rag_enhanced.py
│   ├── rag_engine_implementation.py
│   └── discovery_to_rag_migrator.py
├── scripts/
│   ├── compare_rag_solutions.py
│   └── migrate_discovery_to_rag.py
├── docs/
│   └── [Complete documentation]
└── interactive_walkthrough.py  # Interactive guide
```

## ⚠️ Cloud Shell Specific Notes

### 1. Session Timeout
Cloud Shell sessions timeout after 20 minutes of inactivity. Your files persist, but long-running processes may be interrupted.

**Solution for long migrations:**
```bash
# Use tmux for persistent sessions
tmux new -s migration
python scripts/migrate_discovery_to_rag.py --incremental
# Ctrl+B, then D to detach
# tmux attach -t migration  # To reattach
```

### 2. Storage Limit
Cloud Shell has 5GB persistent storage. This is plenty for this project.

### 3. Resource Limits
Cloud Shell has modest resources (1 vCPU, 1.7GB RAM). Perfect for deployment and testing, but heavy processing happens in BigQuery/Vertex AI.

## 🚀 Complete Cloud Shell Workflow

```bash
# 1. Clone
git clone https://github.com/stuagano/rag-discovery-engine.git
cd rag-discovery-engine

# 2. Configure (auto-detects project)
echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" > .env
echo "RAG_DEPLOYMENT_MODE=bigquery_enhanced" >> .env

# 3. Deploy
./deploy_unified.sh

# 4. Test
python src/bigquery_rag_enhanced.py query "What are safety procedures?"

# 5. (Optional) Migrate existing Discovery Engine
python scripts/migrate_discovery_to_rag.py --wizard
```

**Total time: ~5 minutes** ⏱️

## ✅ Validation Checklist

After deployment, verify:

```bash
# Check BigQuery dataset created
bq ls -d | grep rag

# Check Vertex AI is enabled
gcloud services list --enabled | grep aiplatform

# List created resources
python -c "
from src.bigquery_rag_enhanced import BigQueryRAGEnhanced
rag = BigQueryRAGEnhanced()
print(f'Documents in BigQuery: {rag.get_document_count()}')
"
```

## 🆘 Troubleshooting in Cloud Shell

### Issue: "API not enabled"
```bash
# The script auto-enables, but you can manually enable:
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com
```

### Issue: "Permission denied"
```bash
# Ensure you have required roles:
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/aiplatform.user"
```

### Issue: "Package not found"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

## 📊 Expected Output

After successful deployment:
```
✅ APIs enabled
✅ BigQuery dataset created: rag_unified
✅ Documents loaded: 10
✅ Embeddings generated: 10
✅ Test query successful
💰 Estimated monthly cost: $25.12
🎉 RAG system ready!

Access at:
- Query: python src/bigquery_rag_enhanced.py query "your question"
- Analytics: python src/bigquery_rag_enhanced.py analytics
```

## 🎯 Next Steps in Cloud Shell

1. **Add your documents:**
```bash
python src/public_data_loader.py  # Load more data
```

2. **Build an API:**
```bash
# FastAPI endpoint (example in src/)
python src/api_server.py
```

3. **Deploy to Cloud Run:**
```bash
gcloud run deploy rag-api --source .
```

## 📞 Support

- **In Cloud Shell:** Everything should work automatically
- **Issues:** Check [GitHub Issues](https://github.com/stuagano/rag-discovery-engine/issues)
- **Docs:** See `/docs` folder for detailed guides

---

**YES, this will work end-to-end in Cloud Shell!** The project is designed specifically for this use case. 🚀