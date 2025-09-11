#!/bin/bash

# RAG Response Testing Script
# Shows example responses from all RAG implementations

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       RAG Discovery Engine - Response Format Examples          ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Function to format JSON output
format_json() {
    if command -v jq &> /dev/null; then
        jq '.'
    else
        python3 -m json.tool
    fi
}

# Test queries
QUERIES=(
    "What are the maintenance procedures?"
    "How do I perform quality checks?"
    "What safety equipment is required?"
    "What is the temperature range for equipment?"
    "How often should filters be replaced?"
)

echo ""
echo -e "${BLUE}=== Testing RAG Implementation: $RAG_DEPLOYMENT_MODE ===${NC}"
echo ""

# Determine which implementation to test
case "$RAG_DEPLOYMENT_MODE" in
    bigquery_basic)
        echo -e "${GREEN}Testing BigQuery Basic RAG${NC}"
        echo ""
        
        # Show status
        echo -e "${YELLOW}1. Status Command Output:${NC}"
        echo "Command: python3 src/cloud_shell_rag.py status"
        echo "─────────────────────────────────────────"
        python3 src/cloud_shell_rag.py status 2>&1 | head -20
        echo ""
        
        # Show query response format
        echo -e "${YELLOW}2. Query Command Output:${NC}"
        echo "Command: python3 src/cloud_shell_rag.py query \"${QUERIES[0]}\""
        echo "─────────────────────────────────────────"
        python3 src/cloud_shell_rag.py query "${QUERIES[0]}" 2>&1
        echo ""
        
        # Show JSON format if available
        echo -e "${YELLOW}3. Raw JSON Response (if using --json flag):${NC}"
        echo "─────────────────────────────────────────"
        python3 -c "
from src.cloud_shell_rag import GoogleCloudRAG
import json
rag = GoogleCloudRAG()
result = rag.query('${QUERIES[0]}')
print(json.dumps(result, indent=2))
" 2>/dev/null | format_json || echo "JSON output not available for this implementation"
        ;;
        
    bigquery_enhanced)
        echo -e "${GREEN}Testing BigQuery Enhanced RAG${NC}"
        echo ""
        
        # Show status
        echo -e "${YELLOW}1. Status Command Output:${NC}"
        echo "Command: python3 src/bigquery_rag_enhanced.py status"
        echo "─────────────────────────────────────────"
        python3 src/bigquery_rag_enhanced.py status 2>&1 | head -20
        echo ""
        
        # Show query response format
        echo -e "${YELLOW}2. Query Command Output:${NC}"
        echo "Command: python3 src/bigquery_rag_enhanced.py query \"${QUERIES[0]}\""
        echo "─────────────────────────────────────────"
        python3 src/bigquery_rag_enhanced.py query "${QUERIES[0]}" 2>&1
        echo ""
        
        # Show enhanced query with metadata
        echo -e "${YELLOW}3. Enhanced Query with Metadata:${NC}"
        echo "Command: python3 src/bigquery_rag_enhanced.py query-enhanced \"${QUERIES[0]}\""
        echo "─────────────────────────────────────────"
        python3 src/bigquery_rag_enhanced.py query-enhanced "${QUERIES[0]}" 2>&1 | format_json
        echo ""
        
        # Show analytics if available
        echo -e "${YELLOW}4. Analytics Output:${NC}"
        echo "Command: python3 src/bigquery_rag_enhanced.py analytics"
        echo "─────────────────────────────────────────"
        python3 src/bigquery_rag_enhanced.py analytics 2>&1 | head -30
        ;;
        
    rag_engine)
        echo -e "${GREEN}Testing Vertex AI RAG Engine${NC}"
        echo ""
        
        # Show status
        echo -e "${YELLOW}1. Status Command Output:${NC}"
        echo "Command: python3 src/rag_engine_implementation.py status"
        echo "─────────────────────────────────────────"
        python3 src/rag_engine_implementation.py status 2>&1 | format_json
        echo ""
        
        # Show list of files
        echo -e "${YELLOW}2. List Command Output:${NC}"
        echo "Command: python3 src/rag_engine_implementation.py list"
        echo "─────────────────────────────────────────"
        python3 src/rag_engine_implementation.py list 2>&1
        echo ""
        
        # Show query response
        echo -e "${YELLOW}3. Query Command Output:${NC}"
        echo "Command: python3 src/rag_engine_implementation.py query \"${QUERIES[0]}\""
        echo "─────────────────────────────────────────"
        python3 src/rag_engine_implementation.py query "${QUERIES[0]}" 2>&1
        echo ""
        
        # Show raw JSON response
        echo -e "${YELLOW}4. Raw JSON Response Format:${NC}"
        echo "─────────────────────────────────────────"
        python3 -c "
from src.rag_engine_implementation import RAGEngineImplementation
import json
rag = RAGEngineImplementation()
try:
    rag.create_or_get_corpus()
    result = rag.query('${QUERIES[0]}', top_k=3)
    # Show full structure
    print(json.dumps({
        'query': result.get('query'),
        'answer': result.get('answer')[:200] + '...' if result.get('answer') else None,
        'num_contexts': result.get('num_contexts'),
        'confidence': result.get('confidence'),
        'sources': result.get('sources', [])[:2],
        'timings': result.get('timings'),
        'model': result.get('model'),
        'corpus': result.get('corpus')
    }, indent=2))
except Exception as e:
    print(json.dumps({'error': str(e)}, indent=2))
" 2>/dev/null | format_json
        ;;
        
    *)
        echo -e "${YELLOW}No RAG_DEPLOYMENT_MODE set, showing available modes:${NC}"
        echo "  - bigquery_basic"
        echo "  - bigquery_enhanced"
        echo "  - rag_engine"
        echo ""
        echo "Set RAG_DEPLOYMENT_MODE in .env file"
        ;;
esac

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    Response Format Summary                      ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}All implementations return these common fields:${NC}"
echo "  • query: The original question"
echo "  • answer: The generated response"
echo "  • contexts/sources: Retrieved relevant documents"
echo "  • num_contexts: Number of contexts found"
echo ""

echo -e "${GREEN}BigQuery Enhanced adds:${NC}"
echo "  • metadata: Document metadata (keywords, entities, etc.)"
echo "  • confidence_score: Answer confidence (0-1)"
echo "  • processing_time: Query execution time"
echo "  • search_strategy: Type of search used"
echo ""

echo -e "${GREEN}RAG Engine adds:${NC}"
echo "  • confidence: Model confidence score"
echo "  • timings: Detailed timing breakdown"
echo "  • corpus: Corpus identifier"
echo "  • model: Generation model used"
echo ""

echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    Multiple Query Examples                      ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Show how to run multiple queries
echo -e "${YELLOW}Running Multiple Queries:${NC}"
echo ""

for i in "${!QUERIES[@]}"; do
    echo -e "${BLUE}Query $((i+1)):${NC} ${QUERIES[$i]}"
    
    case "$RAG_DEPLOYMENT_MODE" in
        bigquery_basic)
            python3 src/cloud_shell_rag.py query "${QUERIES[$i]}" 2>&1 | grep -E "Query:|Answer:" | head -2
            ;;
        bigquery_enhanced)
            python3 src/bigquery_rag_enhanced.py query "${QUERIES[$i]}" 2>&1 | grep -E "Query:|Answer:" | head -2
            ;;
        rag_engine)
            python3 src/rag_engine_implementation.py query "${QUERIES[$i]}" 2>&1 | grep -E "Query:|Answer:" | head -2
            ;;
    esac
    echo ""
done

echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                      Programmatic Access                        ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}Python Example:${NC}"
cat << 'PYTHON_EXAMPLE'
```python
# BigQuery Basic
from src.cloud_shell_rag import GoogleCloudRAG
rag = GoogleCloudRAG()
result = rag.query("Your question here")
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")

# BigQuery Enhanced
from src.bigquery_rag_enhanced import BigQueryRAGEnhanced
rag = BigQueryRAGEnhanced()
result = rag.query_enhanced("Your question here")
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence_score']}")
print(f"Metadata: {result['metadata']}")

# RAG Engine
from src.rag_engine_implementation import RAGEngineImplementation
rag = RAGEngineImplementation()
rag.create_or_get_corpus()
result = rag.query("Your question here", top_k=5)
print(f"Answer: {result['answer']}")
print(f"Time: {result['timings']['total_ms']}ms")
```
PYTHON_EXAMPLE

echo ""
echo -e "${GREEN}Shell Script Example:${NC}"
cat << 'SHELL_EXAMPLE'
```bash
#!/bin/bash
# Query and parse JSON response
RESPONSE=$(python3 src/bigquery_rag_enhanced.py query "Your question" --json)
ANSWER=$(echo "$RESPONSE" | jq -r '.answer')
CONFIDENCE=$(echo "$RESPONSE" | jq -r '.confidence_score')
echo "Answer: $ANSWER"
echo "Confidence: $CONFIDENCE"
```
SHELL_EXAMPLE

echo ""
echo -e "${GREEN}cURL API Example (if deployed as service):${NC}"
cat << 'CURL_EXAMPLE'
```bash
# If deployed as a Cloud Run service
curl -X POST https://YOUR-SERVICE-URL/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{
    "query": "Your question here",
    "top_k": 5,
    "generate": true
  }'
```
CURL_EXAMPLE

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Response format testing complete!${NC}"
echo ""
echo "To test a different implementation, change RAG_DEPLOYMENT_MODE in .env"
echo "and run this script again."