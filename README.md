# Google Cloud RAG on BigQuery - One-Command Cloud Shell Deployment ☁️

Deploy a production-ready RAG system using **100% Google Cloud services** (BigQuery + Vertex AI) in under 5 minutes from Cloud Shell.

## 🚀 Quick Start (Cloud Shell)

### Option 1: Automatic Setup Wizard (Recommended)
```bash
# Clone repository
git clone https://github.com/stuagano/rag-discovery-engine.git
cd rag-discovery-engine

# Run the Cloud Shell setup wizard
chmod +x scripts/cloud_shell_setup.sh
./scripts/cloud_shell_setup.sh
```

The wizard will:
- 🎯 Auto-detect or prompt for your GCP project
- ⚡ Enable all required APIs
- 🔧 Configure optimal settings
- 🚀 Deploy your chosen RAG solution

### Option 2: Interactive Configuration
```bash
# For full control over all settings
./deploy_unified_interactive.sh
```

### Option 3: Manual Deployment
```bash
# Edit configuration first
cp .env.example .env
nano .env  # Set your project ID

# Then deploy
./deploy_unified.sh
```

That's it! The script automatically:
- ✅ Detects your Google Cloud Shell environment
- ✅ Creates `.env` with your GCP project settings
- ✅ Installs dependencies
- ✅ Enables BigQuery and Vertex AI APIs
- ✅ Creates optimized BigQuery dataset and tables
- ✅ Generates sample manufacturing documents
- ✅ Processes embeddings with Vertex AI
- ✅ Runs validation tests

## 🏗️ Pure Google Cloud Architecture

```
Cloud Shell
    ↓
Google Cloud Project
    ├── BigQuery (Vector Storage + SQL Search)
    ├── Vertex AI Embeddings (textembedding-gecko)
    └── Vertex AI Gemini (Answer Generation)
```

### **Why This Architecture?**
- **100% Google Cloud**: No external dependencies
- **Serverless**: Zero infrastructure management
- **Integrated**: Native GCP services work seamlessly
- **Cost-effective**: Pay only for what you use
- **Scalable**: Handle millions of documents
- **Secure**: Enterprise-grade Google Cloud security

## 📋 Google Cloud Services Used

### **BigQuery** 
- Vector storage with native SQL
- Partitioned tables for performance
- Clustering for optimized queries
- Built-in cosine similarity function
- Sub-second query performance

### **Vertex AI**
- **Embedding Model**: `gemini-embedding-001` (768 dimensions)
- **Generation Model**: `gemini-1.5-flash` for answer synthesis
- Optional: `gemini-1.5-pro` for enhanced quality

## 💬 Test Your RAG System

```bash
# Quick query test
python -c "
from src.cloud_shell_rag import GoogleCloudRAG
rag = GoogleCloudRAG()
result = rag.query('How to maintain equipment?')
print('Answer:', result['answer'][:200])
print('Sources:', result['num_sources'])
print('Time:', f\"{result['query_time_ms']:.1f}ms\")
"

# Check system status
python src/cloud_shell_rag.py status

# Run validation tests
python src/cloud_shell_rag.py test
```

## 🎯 Manufacturing Sample Queries

```python
from src.cloud_shell_rag import GoogleCloudRAG
rag = GoogleCloudRAG()

# Equipment maintenance
result = rag.query("What are the daily maintenance tasks?")

# Quality control
result = rag.query("What are the wafer thickness specifications?")

# Process parameters
result = rag.query("What is the required chamber pressure?")

# Safety procedures
result = rag.query("What safety equipment is required?")
```

## 📊 Performance Benchmarks

Expected performance on Google Cloud:
- **Query Latency**: <500ms with BigQuery vector search
- **Embedding Generation**: ~100ms per chunk with Vertex AI
- **Answer Generation**: ~1-2s with Gemini
- **Storage Cost**: $0.02/GB in BigQuery
- **Query Cost**: ~$5 per TB scanned

## 🔧 Configuration (.env)

```bash
# Google Cloud Project (auto-detected in Cloud Shell)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1

# BigQuery
BIGQUERY_DATASET=rag_poc

# Vertex AI Models
VERTEX_EMBEDDING_MODEL=gemini-embedding-001
VERTEX_GENERATION_MODEL=gemini-1.5-flash

# Document Processing
NUM_TEST_DOCS=10
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## 🔒 Security Features

- **Cloud Shell Authentication**: Automatic service account setup
- **IAM Roles**: Minimal required permissions
  - BigQuery Data Editor
  - Vertex AI User
- **Row-level Security**: Optional BigQuery policies
- **Audit Logging**: All queries logged in Cloud Audit Logs
- **No Data Export**: Everything stays in your GCP project

## 📈 Cost Optimization

For 10,000 manufacturing documents:
- **BigQuery Storage**: ~$0.40/month (20GB)
- **BigQuery Queries**: ~$5-10/month (typical usage)
- **Vertex AI Embeddings**: ~$1-2 (one-time indexing)
- **Gemini Generation**: ~$5-10/month
- **Total**: ~$15-25/month

Compare to:
- Managed vector DBs: $100-500/month
- Discovery Engine: $500-2000/month

## 🛠️ Advanced Usage

### Add Your Own PDFs
```python
from src.cloud_shell_rag import GoogleCloudRAG
import PyPDF2

rag = GoogleCloudRAG()

# Read PDF
with open('manual.pdf', 'rb') as file:
    pdf = PyPDF2.PdfReader(file)
    text = ''.join([page.extract_text() for page in pdf.pages])

# Process and upload
documents = [{
    'document_id': 'manual_001',
    'title': 'Equipment Manual',
    'content': text,
    'document_type': 'maintenance',
    'facility': 'FAB-1'
}]

chunks = rag.process_documents(documents)
rag.upload_to_bigquery(chunks)
```

### Query with Metadata Filtering
```python
# Build custom BigQuery query with filters
sql = f"""
SELECT * FROM `{project}.{dataset}.document_embeddings`
WHERE JSON_VALUE(metadata, '$.facility') = 'FAB-1'
  AND JSON_VALUE(metadata, '$.document_type') = 'maintenance'
"""
```

## 🚀 Production Deployment

### Prerequisites
- Google Cloud Project with billing enabled
- Cloud Shell or local gcloud CLI
- Required APIs (auto-enabled by script):
  - BigQuery API
  - Vertex AI API

### Step-by-Step
1. **Open Cloud Shell** in your GCP Console
2. **Clone this repository**
3. **Run `./deploy.sh`**
4. **Test with sample queries**
5. **Add your documents**

## 📊 BigQuery Schema

```sql
CREATE TABLE document_embeddings (
    document_id STRING REQUIRED,
    chunk_id STRING REQUIRED,
    chunk_text STRING,
    chunk_index INTEGER,
    embedding ARRAY<FLOAT64>,
    embedding_model STRING,
    metadata JSON,
    created_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY document_id, chunk_index;
```

## 🔍 Vector Search Implementation

```sql
-- Cosine similarity function in BigQuery
CREATE FUNCTION cosine_similarity(v1 ARRAY<FLOAT64>, v2 ARRAY<FLOAT64>)
AS (
    (SELECT SUM(a * b) / (SQRT(SUM(a * a)) * SQRT(SUM(b * b)))
     FROM UNNEST(v1) a WITH OFFSET pos1
     JOIN UNNEST(v2) b WITH OFFSET pos2 ON pos1 = pos2)
);
```

## 🎯 Why Choose This Solution?

### vs. Discovery Engine
- **75% lower cost**
- **More control** over indexing and search
- **SQL-native** queries
- **No vendor lock-in**

### vs. Vector Databases
- **No infrastructure** to manage
- **Native GCP** integration
- **SQL familiarity**
- **Lower operational overhead**

### vs. Custom Solutions
- **5-minute deployment**
- **Production-ready**
- **Google-maintained services**
- **Enterprise security**

## 📞 Troubleshooting

### Common Issues

**APIs not enabled?**
```bash
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

**Authentication issues?**
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Quota exceeded?**
- Check Vertex AI quotas in Console
- Reduce batch size in .env
- Use `gemini-1.5-flash` instead of `pro`

## 📚 Documentation

- [Technical Proof Roadmap](docs/TECHNICAL_PROOF_ROADMAP.md)
- [Real Dataset Implementation](docs/REAL_DATASET_IMPLEMENTATION.md)
- [Google Cloud Pricing](https://cloud.google.com/pricing)
- [Vertex AI Models](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
- [BigQuery ML](https://cloud.google.com/bigquery-ml/docs)

## 🌟 Features Summary

✅ **100% Google Cloud** - BigQuery + Vertex AI only  
✅ **One-command deployment** from Cloud Shell  
✅ **Manufacturing sample data** included  
✅ **Production-ready** with error handling  
✅ **Cost-optimized** serverless architecture  
✅ **Sub-second queries** with BigQuery  
✅ **Enterprise security** with IAM  
✅ **Scalable** to millions of documents  

---

**Deploy now and have a working RAG system on Google Cloud in 5 minutes!** 🚀

*Built with ❤️ using Google Cloud Platform services*