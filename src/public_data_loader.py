"""
Public Data Loader for RAG Implementations
Load real public datasets for testing and demonstration
"""

import os
import json
import requests
from typing import List, Dict, Any
import PyPDF2
import pdfplumber
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PublicDataLoader:
    """Load various public datasets for RAG testing"""
    
    def __init__(self):
        self.data_sources = {
            "wikipedia": {
                "description": "Wikipedia articles on manufacturing topics",
                "type": "api",
                "topics": [
                    "Semiconductor_manufacturing",
                    "Quality_control",
                    "Predictive_maintenance",
                    "Six_Sigma",
                    "Lean_manufacturing",
                    "Industry_4.0",
                    "Total_quality_management",
                    "Statistical_process_control",
                    "Failure_mode_and_effects_analysis",
                    "Root_cause_analysis"
                ]
            },
            "arxiv": {
                "description": "ArXiv papers on manufacturing and ML",
                "type": "api",
                "categories": [
                    "cs.AI",  # Artificial Intelligence
                    "cs.LG",  # Machine Learning
                    "stat.ML", # Machine Learning
                    "cs.SY"   # Systems and Control
                ],
                "queries": [
                    "manufacturing optimization",
                    "predictive maintenance",
                    "quality control automation",
                    "industrial IoT"
                ]
            },
            "government": {
                "description": "US Government manufacturing standards and guides",
                "type": "pdf",
                "sources": [
                    {
                        "name": "NIST Manufacturing Guide",
                        "url": "https://www.nist.gov/system/files/documents/2017/05/09/manufacturing-extension-partnership-mep-overview.pdf"
                    },
                    {
                        "name": "EPA Lean Manufacturing",
                        "url": "https://www.epa.gov/sustainability/lean-manufacturing-and-environment-toolkit"
                    }
                ]
            },
            "patents": {
                "description": "USPTO patent abstracts for manufacturing",
                "type": "api",
                "queries": [
                    "semiconductor manufacturing process",
                    "quality control system",
                    "predictive maintenance method",
                    "automated inspection"
                ]
            },
            "synthetic": {
                "description": "Generated manufacturing documentation",
                "type": "generated",
                "templates": "default"
            }
        }
    
    def load_wikipedia_articles(self, topics: List[str] = None, max_articles: int = 10) -> List[Dict[str, Any]]:
        """Load Wikipedia articles on manufacturing topics"""
        
        if topics is None:
            topics = self.data_sources["wikipedia"]["topics"][:max_articles]
        
        documents = []
        base_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
        
        logger.info(f"Loading {len(topics)} Wikipedia articles...")
        
        for topic in tqdm(topics, desc="Loading Wikipedia"):
            try:
                response = requests.get(base_url + topic)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Get full content
                    content_url = f"https://en.wikipedia.org/api/rest_v1/page/html/{topic}"
                    content_response = requests.get(content_url)
                    
                    # Clean HTML to text (basic cleaning)
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content_response.text, 'html.parser')
                    full_text = soup.get_text()[:5000]  # Limit size
                    
                    documents.append({
                        "document_id": f"wiki_{topic.lower()}",
                        "title": data.get("title", topic),
                        "content": data.get("extract", "") + "\n\n" + full_text,
                        "document_type": "encyclopedia",
                        "source": "wikipedia",
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "created_date": data.get("timestamp", "")
                    })
            except Exception as e:
                logger.warning(f"Failed to load {topic}: {e}")
        
        logger.info(f"✅ Loaded {len(documents)} Wikipedia articles")
        return documents
    
    def load_arxiv_papers(self, max_papers: int = 10) -> List[Dict[str, Any]]:
        """Load ArXiv paper abstracts on manufacturing topics"""
        
        documents = []
        base_url = "http://export.arxiv.org/api/query"
        
        queries = [
            "manufacturing AND (optimization OR automation)",
            "predictive maintenance industrial",
            "quality control manufacturing",
            "industry 4.0"
        ]
        
        logger.info(f"Loading ArXiv papers...")
        
        for query in queries[:max_papers//len(queries)]:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(5, max_papers)
            }
            
            try:
                response = requests.get(base_url, params=params)
                if response.status_code == 200:
                    # Parse XML response
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)
                    
                    # Extract entries
                    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                        title = entry.find('{http://www.w3.org/2005/Atom}title').text
                        summary = entry.find('{http://www.w3.org/2005/Atom}summary').text
                        paper_id = entry.find('{http://www.w3.org/2005/Atom}id').text.split('/')[-1]
                        
                        documents.append({
                            "document_id": f"arxiv_{paper_id}",
                            "title": title.replace('\n', ' '),
                            "content": summary.replace('\n', ' '),
                            "document_type": "research_paper",
                            "source": "arxiv",
                            "url": f"https://arxiv.org/abs/{paper_id}",
                            "created_date": entry.find('{http://www.w3.org/2005/Atom}published').text
                        })
            except Exception as e:
                logger.warning(f"Failed to load ArXiv papers for query '{query}': {e}")
        
        logger.info(f"✅ Loaded {len(documents)} ArXiv papers")
        return documents
    
    def load_patents(self, max_patents: int = 10) -> List[Dict[str, Any]]:
        """Load USPTO patent abstracts (simplified - would need API key for production)"""
        
        # For demo, return synthetic patent-like documents
        documents = []
        
        patent_templates = [
            {
                "title": "Method and System for Predictive Maintenance in Manufacturing",
                "abstract": """A computer-implemented method for predictive maintenance comprising:
                collecting sensor data from manufacturing equipment; analyzing patterns using machine learning;
                predicting failure probability; and scheduling maintenance activities. The system reduces
                downtime by 40% and extends equipment life by detecting anomalies before critical failures."""
            },
            {
                "title": "Automated Quality Control System Using Computer Vision",
                "abstract": """An automated inspection system utilizing high-resolution cameras and deep learning
                algorithms to detect defects in manufactured products. The system processes images in real-time,
                identifies defects with 99.5% accuracy, and automatically sorts products based on quality grades."""
            },
            {
                "title": "Smart Manufacturing Process Optimization Platform",
                "abstract": """A platform for optimizing manufacturing processes using IoT sensors, edge computing,
                and cloud analytics. The system continuously monitors production parameters, identifies bottlenecks,
                and automatically adjusts process variables to maximize throughput while maintaining quality standards."""
            }
        ]
        
        for i, template in enumerate(patent_templates[:max_patents]):
            documents.append({
                "document_id": f"patent_us{10000000 + i}",
                "title": template["title"],
                "content": template["abstract"],
                "document_type": "patent",
                "source": "uspto",
                "patent_number": f"US{10000000 + i}",
                "created_date": "2024-01-01"
            })
        
        logger.info(f"✅ Loaded {len(documents)} patent documents")
        return documents
    
    def load_nist_standards(self) -> List[Dict[str, Any]]:
        """Load NIST manufacturing standards and best practices"""
        
        documents = []
        
        # NIST best practices (simplified text versions)
        nist_docs = [
            {
                "title": "NIST Framework for Smart Manufacturing Systems",
                "content": """The NIST Smart Manufacturing Systems framework provides guidelines for:
                1. Data Collection and Management: Establishing robust data pipelines from sensors and equipment
                2. Interoperability Standards: Ensuring systems can communicate effectively
                3. Cybersecurity Measures: Protecting manufacturing systems from threats
                4. Performance Metrics: KPIs for measuring manufacturing efficiency
                5. Continuous Improvement: Methodologies for ongoing optimization
                
                Key Performance Indicators:
                - Overall Equipment Effectiveness (OEE): Target > 85%
                - First Pass Yield: Target > 98%
                - Cycle Time Reduction: 20% year-over-year
                - Defect Rate: < 100 ppm
                """
            },
            {
                "title": "NIST Guide to Industrial Control Systems Security",
                "content": """Security guidelines for manufacturing control systems:
                1. Network Segmentation: Isolate critical systems from corporate networks
                2. Access Control: Implement role-based access with multi-factor authentication
                3. Monitoring: Continuous monitoring of system behavior and anomaly detection
                4. Incident Response: Established procedures for security incidents
                5. Recovery Planning: Backup and disaster recovery strategies
                
                Implementation requires regular security assessments, employee training,
                and coordination with IT security teams."""
            }
        ]
        
        for i, doc in enumerate(nist_docs):
            documents.append({
                "document_id": f"nist_guide_{i+1:03d}",
                "title": doc["title"],
                "content": doc["content"],
                "document_type": "standard",
                "source": "nist",
                "created_date": "2024-01-01"
            })
        
        logger.info(f"✅ Loaded {len(documents)} NIST standards")
        return documents
    
    def load_synthetic_manufacturing_docs(self, num_docs: int = 10) -> List[Dict[str, Any]]:
        """Generate synthetic manufacturing documentation"""
        
        from src.cloud_shell_rag import GoogleCloudRAG
        
        # Use existing synthetic data generator
        rag = GoogleCloudRAG()
        documents = rag.generate_sample_documents(num_docs)
        
        # Mark as synthetic
        for doc in documents:
            doc["source"] = "synthetic"
            doc["public"] = True
        
        logger.info(f"✅ Generated {len(documents)} synthetic documents")
        return documents
    
    def load_all_public_data(self, 
                            include_wikipedia: bool = True,
                            include_arxiv: bool = True,
                            include_patents: bool = True,
                            include_nist: bool = True,
                            include_synthetic: bool = True,
                            max_docs_per_source: int = 5) -> List[Dict[str, Any]]:
        """Load all public data sources"""
        
        all_documents = []
        
        if include_wikipedia:
            all_documents.extend(self.load_wikipedia_articles(max_articles=max_docs_per_source))
        
        if include_arxiv:
            all_documents.extend(self.load_arxiv_papers(max_papers=max_docs_per_source))
        
        if include_patents:
            all_documents.extend(self.load_patents(max_patents=max_docs_per_source))
        
        if include_nist:
            all_documents.extend(self.load_nist_standards())
        
        if include_synthetic:
            all_documents.extend(self.load_synthetic_manufacturing_docs(num_docs=max_docs_per_source))
        
        logger.info(f"\n✅ Total documents loaded: {len(all_documents)}")
        
        # Summary by source
        sources = {}
        for doc in all_documents:
            source = doc.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        logger.info("Document sources:")
        for source, count in sources.items():
            logger.info(f"  • {source}: {count} documents")
        
        return all_documents
    
    def save_to_json(self, documents: List[Dict[str, Any]], filename: str = "public_documents.json"):
        """Save documents to JSON file"""
        
        with open(filename, 'w') as f:
            json.dump(documents, f, indent=2)
        
        logger.info(f"✅ Saved {len(documents)} documents to {filename}")
    
    def load_from_json(self, filename: str = "public_documents.json") -> List[Dict[str, Any]]:
        """Load documents from JSON file"""
        
        with open(filename, 'r') as f:
            documents = json.load(f)
        
        logger.info(f"✅ Loaded {len(documents)} documents from {filename}")
        return documents


def main():
    """Load and display public data"""
    
    loader = PublicDataLoader()
    
    print("\n🌐 Public Data Loader for RAG Testing")
    print("=" * 50)
    
    # Load all public data
    documents = loader.load_all_public_data(
        include_wikipedia=True,
        include_arxiv=True,
        include_patents=True,
        include_nist=True,
        include_synthetic=True,
        max_docs_per_source=3
    )
    
    # Save to file
    loader.save_to_json(documents, "data/public_manufacturing_docs.json")
    
    print(f"\n📊 Summary:")
    print(f"Total documents: {len(documents)}")
    print(f"Saved to: data/public_manufacturing_docs.json")
    
    # Show sample
    if documents:
        print(f"\n📄 Sample document:")
        sample = documents[0]
        print(f"Title: {sample.get('title', 'N/A')}")
        print(f"Source: {sample.get('source', 'N/A')}")
        print(f"Type: {sample.get('document_type', 'N/A')}")
        print(f"Content preview: {sample.get('content', '')[:200]}...")


if __name__ == "__main__":
    main()