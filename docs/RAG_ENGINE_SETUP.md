# RAG Engine Setup Guide

## Regional Capacity Issue Resolution

### Problem
RAG Engine deployment fails in `us-central1` with error:
```
InvalidArgument('For new project, RAG Engine in us-central1 is allowlisting based due to capacity limitation. Please use other regions...')
```

### Solution
Use `us-east4` region which has better capacity availability for new projects.

## Required .env Configuration

Update your `.env` file with these settings for RAG Engine:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-east4  # Use us-east4 instead of us-central1

# Deployment Settings (NO export needed - script uses set -a)
RAG_DEPLOYMENT_MODE=rag_engine
AUTO_CREATE_RESOURCES=true
AUTO_ENABLE_APIS=true
AUTO_GRANT_PERMISSIONS=true
VERBOSE_LOGGING=true

# Vertex AI Models
VERTEX_EMBEDDING_MODEL=textembedding-gecko@003
VERTEX_GENERATION_MODEL=gemini-1.5-flash
```

## Troubleshooting

### "Invalid RAG_DEPLOYMENT_MODE:" Error
If you see deployment mode as blank, ensure:
1. NO `export` statements in .env file (deployment script handles exporting)
2. Use command line override: `./deploy_unified.sh --mode rag_engine`
3. Check .env file format with `cat .env | grep RAG_DEPLOYMENT_MODE`

## Deployment Commands

### Deploy RAG Engine
```bash
./deploy_unified.sh --mode rag_engine
```

### Alternative Regions (if us-east4 has issues)
- `us-east4` (recommended)
- `europe-west3` 
- `europe-west4`

Avoid `us-central1` for new projects due to capacity limitations.

## Expected Costs
- RAG Engine: ~$250/month
- Includes corpus storage, retrieval API, and document processing
- Higher cost than BigQuery implementations but provides enterprise features

## Test Queries After Deployment
- "What are the maintenance procedures?"
- "What safety equipment is required?"
- "How do I perform quality checks?"
- "What are the training requirements?"
- "What is the startup procedure?"