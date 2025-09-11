# RAG on Google Cloud: Complete Implementation Guide

## 🎯 Quick Start: Choose Your Path

### Option 1: BigQuery RAG ($25/month) - RECOMMENDED
```bash
# Deploy in 5 minutes
./deploy_bigquery_enhanced.sh

# Test it
python src/bigquery_rag_enhanced.py query "What are the maintenance procedures?"
```

### Option 2: RAG Engine ($250/month)
```bash
# Deploy managed service
./deploy_rag_engine.sh

# Test it
python src/rag_engine_implementation.py query "What are the maintenance procedures?"
```

## 📊 Implementation Comparison

| Feature | BigQuery RAG Enhanced | RAG Engine |
|---------|---------------------|------------|
| **Monthly Cost** | $25-30 | $200-500 |
| **Setup Time** | 5 minutes | 15 minutes |
| **Maintenance** | DIY | Google-managed |
| **SQL Access** | ✅ Full | ❌ None |
| **Document Parsing** | Basic | Advanced |
| **Data Connectors** | Manual | GCS, Drive, Slack |
| **Hybrid Search** | ✅ Available | ✅ Built-in |
| **Caching** | ✅ Available | ❌ Not native |
| **Reranking** | ✅ Available | ⚠️ Limited |
| **Analytics** | ✅ SQL-based | ⚠️ Basic |

## 🚀 Detailed Implementation Instructions

## 1. BigQuery RAG Enhanced (Recommended)

### Overview
Our enhanced BigQuery implementation provides enterprise-grade RAG at 10% of the cost of managed solutions.

### Features
- **Hybrid Search**: Combines semantic and keyword search
- **Intelligent Caching**: 24-hour query cache for instant responses
- **Result Reranking**: Gemini-powered relevance scoring
- **Advanced Analytics**: SQL-based query insights
- **Importance Scoring**: Automatic chunk prioritization

### Prerequisites
```bash
# Ensure you have:
- Google Cloud Project with billing enabled
- Python 3.8+
- gcloud CLI installed
```

### Step-by-Step Deployment

#### 1. Clone and Setup
```bash
git clone https://github.com/stuagano/rag-discovery-engine.git
cd rag-discovery-engine
```

#### 2. Configure Environment
```bash
# Run the deployment script
./deploy_bigquery_enhanced.sh

# It will prompt you to enable:
# - Hybrid Search (recommended: Yes)
# - Query Caching (recommended: Yes)  
# - Result Reranking (recommended: Yes)
```

#### 3. Verify Deployment
```bash
# Check status
python src/bigquery_rag_enhanced.py analytics

# Output should show:
# - Total documents: 10
# - Total chunks: ~30-50
# - Cache status: Active
```

### Using BigQuery RAG

#### Basic Query
```python
from src.bigquery_rag_enhanced import BigQueryRAGEnhanced

rag = BigQueryRAGEnhanced()
result = rag.query_enhanced("What is the maintenance schedule?")
print(f"Answer: {result['answer']}")
print(f"Time: {result['timings']['total_ms']}ms")
```

#### Advanced Query with Filters
```python
# Filter by facility
result = rag.query_enhanced(
    "What are the safety procedures?",
    filter_sql="JSON_VALUE(metadata, '$.facility') = 'FAB-1'"
)
```

#### Hybrid Search
```python
# Combine semantic and keyword search
result = rag.query_enhanced(
    "vacuum pressure temperature calibration",
    use_hybrid=True,  # Enables keyword matching
    use_reranking=True  # Reranks results by relevance
)
```

### Direct SQL Access
```sql
-- Query embeddings directly in BigQuery
SELECT 
    chunk_text,
    metadata,
    importance_score
FROM `your-project.rag_enhanced.document_embeddings`
WHERE JSON_VALUE(metadata, '$.document_type') = 'maintenance'
ORDER BY importance_score DESC
LIMIT 10
```

### Cost Optimization Tips
1. **Enable Caching**: Reduces query costs by 50%+
2. **Use Clustering**: Improves query performance
3. **Batch Embeddings**: Process documents in batches
4. **Partition by Date**: Reduces scan costs

## 2. RAG Engine Implementation

### Overview
Google's managed RAG service with built-in document processing and connectors.

### When to Use RAG Engine
- Need managed solution with minimal maintenance
- Require advanced document parsing (PDFs with tables/layouts)
- Multiple data sources (Drive, Slack, JIRA)
- Budget allows $250+/month

### Step-by-Step Deployment

#### 1. Setup
```bash
# Ensure you're in a supported region
export GOOGLE_CLOUD_REGION=us-central1  # or us-east4, europe-west3, europe-west4

# Deploy
./deploy_rag_engine.sh
```

#### 2. Create RAG Corpus
```python
from src.rag_engine_implementation import RAGEngineImplementation

rag_engine = RAGEngineImplementation()

# Create corpus
corpus = rag_engine.create_or_get_corpus(
    display_name="manufacturing_docs",
    description="Manufacturing documentation"
)
```

#### 3. Import Documents

##### From Cloud Storage
```python
# Upload to GCS first
rag_engine.create_gcs_bucket()
uploaded_files = rag_engine.upload_documents_to_gcs(documents)

# Import to corpus
rag_engine.import_documents_to_corpus(
    source_uri=f"gs://{bucket_name}/documents/",
    chunk_size=512,
    parse_mode="layout_parser"  # Advanced PDF parsing
)
```

##### From Google Drive
```python
# Import directly from Drive
rag_engine.import_documents_to_corpus(
    source_uri="drive://folder_id",
    chunk_size=512
)
```

### Using RAG Engine

#### Basic Query
```python
result = rag_engine.query(
    "What are the quality control procedures?",
    top_k=10
)
print(f"Answer: {result['answer']}")
```

#### With Metadata Filtering
```python
contexts = rag_engine.retrieve_context(
    query="maintenance schedule",
    filter_metadata={"facility": "FAB-1", "document_type": "maintenance"}
)
```

### Managing the Corpus

#### List Files
```python
files = rag_engine.list_corpus_files()
for file in files:
    print(f"{file['display_name']} - {file['size_bytes']/1024:.1f}KB")
```

#### Update Documents
```python
# RAG Engine requires delete and re-import
rag_engine.update_corpus_file(
    file_name="doc_0001",
    new_content="Updated content..."
)
```

#### Monitor Usage
```python
stats = rag_engine.get_corpus_statistics()
print(f"Total files: {stats['total_files']}")
print(f"Storage used: {stats['total_size_mb']}MB")
```

## 🔄 Migration Strategies

### From RAG Engine to BigQuery
```python
# Export from RAG Engine
contexts = rag_engine.retrieve_context("", similarity_top_k=10000)

# Import to BigQuery
bigquery_rag = BigQueryRAGEnhanced()
for context in contexts:
    # Process and insert to BigQuery
    bigquery_rag.process_documents_enhanced([context])
```

### From BigQuery to RAG Engine
```python
# Export from BigQuery
query = "SELECT * FROM `project.dataset.document_embeddings`"
df = bigquery_rag.bq_client.query(query).to_dataframe()

# Convert and upload to RAG Engine
documents = df.to_dict('records')
rag_engine.upload_documents_to_gcs(documents)
rag_engine.import_documents_to_corpus(source_uri="gs://bucket/export/")
```

## 📈 Performance Tuning

### BigQuery Optimization
1. **Clustering**: Order by document_id, chunk_index
2. **Partitioning**: Use DATE(created_at) for time-based queries
3. **Caching**: Enable 24-hour cache for common queries
4. **Batch Size**: Process 100 chunks at a time

### RAG Engine Optimization
1. **Chunk Size**: 512 tokens optimal for most use cases
2. **Parser Selection**: Use layout_parser for complex PDFs
3. **Vector DB**: Consider Pinecone/Weaviate for specific needs
4. **Batch Imports**: Process multiple files together

## 🧪 Testing & Comparison

### Run Comparison Suite
```bash
# Compare all implementations
python scripts/compare_rag_solutions.py

# Quick test (3 queries)
python scripts/compare_rag_solutions.py quick
```

### Expected Results
| Metric | BigQuery Basic | BigQuery Enhanced | RAG Engine |
|--------|---------------|-------------------|------------|
| Avg Response | 300ms | 250ms | 200ms |
| Monthly Cost | $22 | $25 | $250 |
| Quality Score | 75% | 85% | 90% |

## 🔍 Monitoring & Analytics

### BigQuery Analytics
```sql
-- Query performance over time
SELECT 
    DATE(created_at) as query_date,
    COUNT(*) as total_queries,
    AVG(response_time_ms) as avg_response_ms,
    PERCENTILE_CONT(response_time_ms, 0.95) OVER() as p95_response_ms
FROM `project.rag_enhanced.query_analytics`
GROUP BY query_date
ORDER BY query_date DESC
```

### Cache Effectiveness
```python
# Check cache hit rate
analytics = bigquery_rag.get_analytics_summary()
hit_rate = analytics['cache_statistics']['avg_cache_hits']
print(f"Cache hit rate: {hit_rate:.1%}")
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```bash
# Fix: Re-authenticate
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

#### 2. API Not Enabled
```bash
# Fix: Enable required APIs
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

#### 3. Region Not Supported (RAG Engine)
```bash
# Fix: Use supported region
export GOOGLE_CLOUD_REGION=us-central1
```

#### 4. Quota Exceeded
```python
# Fix: Reduce batch size
os.environ['BATCH_SIZE'] = '50'  # Default is 100
```

## 📚 Best Practices

### Document Preparation
1. **Clean Text**: Remove special characters and formatting
2. **Metadata**: Add facility, type, date metadata
3. **Chunking**: Use recursive strategy for best results
4. **Overlap**: 20% overlap prevents context loss

### Query Optimization
1. **Be Specific**: More detailed queries get better results
2. **Use Filters**: Reduce search space with metadata
3. **Enable Cache**: For repeated queries
4. **Hybrid Search**: For keyword-heavy queries

### Cost Management
1. **Monitor Usage**: Check BigQuery and Vertex AI quotas
2. **Set Budgets**: Use GCP billing alerts
3. **Optimize Queries**: Use clustering and partitioning
4. **Cache Aggressively**: 24-hour TTL reduces costs

## 🎯 Recommendations by Use Case

### POC/MVP Development
**Use: BigQuery RAG Basic**
- Lowest cost ($22/month)
- Quick setup
- Full control

### Production with Budget Constraints
**Use: BigQuery RAG Enhanced**
- Advanced features ($25/month)
- Hybrid search and caching
- SQL analytics

### Enterprise with Complex Needs
**Use: RAG Engine**
- Managed service ($250/month)
- Advanced parsing
- Multiple data sources

### High-Volume Analytics
**Use: BigQuery RAG Enhanced**
- SQL access for analysis
- Cost-effective at scale
- Custom dashboards possible

## 🔗 Additional Resources

- [BigQuery ML Documentation](https://cloud.google.com/bigquery-ml/docs)
- [Vertex AI Embeddings](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
- [RAG Engine API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/rag-api)
- [Gemini Models](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review error logs: `cat *.log`
3. Open issue on GitHub: https://github.com/stuagano/rag-discovery-engine/issues

---

**Remember**: BigQuery RAG offers 10x cost savings with comparable performance. Start there unless you specifically need RAG Engine's managed features.