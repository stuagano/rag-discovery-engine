# BigQuery RAG - One-Command Cloud Shell Deployment ☁️

Deploy a production-ready RAG system on BigQuery in **under 5 minutes** from Google Cloud Shell.

## 🚀 Quick Start (Cloud Shell)

```bash
# 1. Clone and enter directory
git clone <your-repo-url>
cd rag-discovery-engine-swarm

# 2. One-command deployment
./deploy.sh
```

That's it! The script automatically:
- ✅ Detects your Cloud Shell environment
- ✅ Creates `.env` with your project settings
- ✅ Installs Python dependencies
- ✅ Enables required GCP APIs
- ✅ Creates BigQuery dataset and tables
- ✅ Deploys RAG system with sample data
- ✅ Runs validation tests

## 📋 What You Get

### **Multiple Embedding Models** 🧠
Choose your embedding model in `.env`:
```bash
# Options: vertex, openai, sentence_transformers, huggingface
EMBEDDING_MODEL=vertex
EMBEDDING_MODEL_NAME=textembedding-gecko@003

# Or use OpenAI
EMBEDDING_MODEL=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=text-embedding-3-small

# Or use local Sentence Transformers
EMBEDDING_MODEL=sentence_transformers
HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### **Manufacturing Sample Data** 🏭
Automatically generates 50 sample manufacturing documents:
- Ion implanter maintenance manuals
- Wafer quality inspection reports
- Photolithography process specifications

### **Production-Ready Features** ⚡
- **Chunked embeddings** with overlap for better retrieval
- **Partitioned BigQuery tables** for performance
- **Cosine similarity search** with optimized SQL
- **Batch processing** for efficient embedding generation
- **Error handling** with retry logic

## 💬 Test Your RAG System

```bash
# Quick query test
python -c "
from src.cloud_shell_rag import CloudShellRAG
rag = CloudShellRAG()
result = rag.query('How to maintain ion implanter equipment?')
print('Answer:', result['answer'][:200] + '...')
print('Sources found:', result['num_sources'])
print('Query time:', f\"{result['query_time_ms']:.1f}ms\")
"

# Check system status
python src/cloud_shell_rag.py status

# Run comprehensive tests
python src/cloud_shell_rag.py test
```

## 🎯 Example Queries

Try these manufacturing-specific queries:

```python
from src.cloud_shell_rag import CloudShellRAG
rag = CloudShellRAG()

# Equipment maintenance
result = rag.query("preventive maintenance schedule for photolithography equipment")

# Quality control
result = rag.query("wafer thickness measurement specifications and tolerances") 

# Troubleshooting
result = rag.query("how to troubleshoot particle contamination issues")

# Process parameters
result = rag.query("critical control points for semiconductor manufacturing")
```

## 📊 Performance Benchmarks

Expected performance on Cloud Shell:
- **Query Latency**: <500ms for similarity search
- **Embedding Generation**: ~100ms per document chunk
- **Storage**: ~$0.02/GB in BigQuery
- **Compute**: Minimal - only pay for queries

## 🔧 Configuration Options

Edit `.env` to customize:

```bash
# Dataset size
NUM_TEST_DOCS=50              # Number of sample documents
CHUNK_SIZE=1000               # Text chunk size
CHUNK_OVERLAP=200             # Overlap between chunks

# Performance
BATCH_SIZE=100                # Embedding batch size
MAX_CONCURRENT_EMBEDDINGS=10  # Concurrent processing

# BigQuery
BIGQUERY_DATASET=rag_poc      # Dataset name
GOOGLE_CLOUD_REGION=us-central1

# Features
AUTO_CREATE_RESOURCES=true    # Auto-create BQ resources
SKIP_EXISTING_DATA=true       # Don't overwrite existing data
VERBOSE_LOGGING=true          # Detailed logging
```

## 🏗️ Architecture

```
Cloud Shell
    ↓
Your GCP Project
    ↓
BigQuery (Storage + Vector Search)
    ↓
Vertex AI / OpenAI / HuggingFace (Embeddings)
    ↓
Manufacturing RAG System
```

### **Why BigQuery for RAG?**
- **Serverless**: No infrastructure management
- **Scalable**: Handle millions of documents
- **Cost-effective**: Only pay for queries
- **SQL-native**: Use familiar SQL for vector search
- **Integrated**: Works with existing GCP data

## 📈 Cost Estimates

For 10,000 manufacturing documents:
- **BigQuery Storage**: $0.40/month (20GB)
- **BigQuery Queries**: $5-10/month (typical usage)
- **Vertex AI Embeddings**: $0.50-2.00 (one-time indexing)
- **Total**: **~$6-12/month**

Compare to managed vector DBs: $50-200/month

## 🔒 Security Features

- **Service account authentication** (auto-configured in Cloud Shell)
- **Row-level security** with BigQuery policies
- **Audit logging** for all queries
- **No data export** - everything stays in your GCP project

## 🛠️ Advanced Usage

### Add Your Own PDFs
```python
from src.cloud_shell_rag import CloudShellRAG
rag = CloudShellRAG()

# Add your PDF documents
import PyPDF2
with open('your_manual.pdf', 'rb') as file:
    pdf = PyPDF2.PdfReader(file)
    text = ''.join([page.extract_text() for page in pdf.pages])

# Process and upload
chunks = rag.process_documents([{
    'document_id': 'manual_001',
    'title': 'Equipment Manual',
    'content': text,
    'document_type': 'maintenance_manual',
    'facility': 'FAB-1'
}])
rag.upload_to_bigquery(chunks)
```

### Custom Embeddings
```python
# Use your own embedding model
from src.cloud_shell_rag import EmbeddingModelManager

# Local Sentence Transformers
embeddings = EmbeddingModelManager(
    model_type="sentence_transformers",
    model_name="all-mpnet-base-v2"
)

# OpenAI with custom model
embeddings = EmbeddingModelManager(
    model_type="openai", 
    model_name="text-embedding-3-large"
)
```

## 🚀 Migration from Discovery Engine

Ready to migrate? See detailed migration guide:
- [Technical Proof Roadmap](docs/TECHNICAL_PROOF_ROADMAP.md)
- [Real Dataset Implementation](docs/REAL_DATASET_IMPLEMENTATION.md)

## 📞 Support

Having issues? Check:
1. **Cloud Shell active?** Ensure you're in Google Cloud Shell
2. **Project permissions?** Need BigQuery Admin and Vertex AI User roles
3. **APIs enabled?** The script enables them automatically
4. **Billing active?** BigQuery requires billing enabled

**Common fixes:**
```bash
# Reset everything and start fresh
./deploy.sh

# Manual API enabling
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Check project ID
echo $GOOGLE_CLOUD_PROJECT
```

---

## ⭐ Features Summary

✅ **One-command deployment** from Cloud Shell  
✅ **Multiple embedding models** (Vertex AI, OpenAI, HuggingFace)  
✅ **Manufacturing sample data** included  
✅ **Production-ready** with error handling  
✅ **Cost-optimized** BigQuery storage  
✅ **Fast queries** with SQL vector search  
✅ **Secure** with GCP authentication  
✅ **Scalable** to millions of documents  

**Deploy now and have a working RAG system in 5 minutes!** 🚀