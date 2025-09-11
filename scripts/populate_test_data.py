#!/usr/bin/env python3
"""
Populate RAG implementations with test data
Creates sample manufacturing documents for testing
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

load_dotenv()

# Sample manufacturing documents
TEST_DOCUMENTS = [
    {
        "id": "maintenance_001",
        "title": "Equipment Maintenance Procedures",
        "content": """
EQUIPMENT MAINTENANCE PROCEDURES

Daily Maintenance Tasks:
- Check system pressure: Maintain 10-15 PSI for optimal performance
- Monitor temperature: Keep operating temperature between 20-25°C
- Inspect safety valves: Ensure all safety mechanisms are functional
- Record readings: Log all measurements in the daily maintenance log
- Visual inspection: Check for leaks, unusual sounds, or vibrations

Weekly Maintenance Tasks:
- Clean filters: Replace or clean air and fluid filters
- Test emergency systems: Verify emergency stop and backup systems
- Calibrate sensors: Check and adjust temperature and pressure sensors
- Update maintenance log: Review and update the weekly maintenance records
- Lubrication check: Inspect and refill lubrication systems

Monthly Maintenance Tasks:
- Complete system inspection: Thorough examination of all components
- Preventive maintenance: Execute scheduled preventive maintenance tasks
- Performance analysis: Review system performance metrics and trends
- Documentation update: Update maintenance procedures and schedules
        """,
        "metadata": {
            "document_type": "maintenance",
            "facility": "FAB-1",
            "department": "Operations",
            "keywords": ["maintenance", "procedures", "daily", "weekly", "monthly", "equipment"]
        }
    },
    {
        "id": "safety_002",
        "title": "Safety Equipment Requirements",
        "content": """
SAFETY EQUIPMENT REQUIREMENTS

Personal Protective Equipment (PPE):
- Hard hats: Required in all manufacturing areas
- Safety glasses: Mandatory for all personnel
- Steel-toed boots: Required for floor operations
- High-visibility vests: Needed in designated areas
- Hearing protection: Required in high-noise zones

Emergency Equipment:
- Fire extinguishers: Located every 50 feet
- Emergency showers: Available within 10 seconds of chemical areas
- First aid kits: Positioned at each workstation
- Emergency communication: Radio systems for immediate contact
- Evacuation routes: Clearly marked and regularly inspected

Respiratory Protection:
- N95 masks: For dust and particle protection
- Half-face respirators: For chemical exposure areas
- Full-face respirators: For high-hazard operations
- Supplied air systems: For confined space work
        """,
        "metadata": {
            "document_type": "safety",
            "facility": "FAB-1",
            "department": "Safety",
            "keywords": ["safety", "equipment", "PPE", "emergency", "protection"]
        }
    },
    {
        "id": "quality_003",
        "title": "Quality Control Procedures",
        "content": """
QUALITY CONTROL PROCEDURES

Inspection Standards:
- Visual inspection: Check for defects, scratches, or damage
- Dimensional verification: Measure critical dimensions within tolerances
- Function testing: Verify all operational parameters
- Documentation: Record all quality measurements and results

Testing Protocols:
- Incoming material inspection: Verify supplier quality standards
- In-process testing: Monitor quality during manufacturing
- Final inspection: Complete quality verification before shipping
- Statistical sampling: Use approved sampling plans and procedures

Quality Metrics:
- Defect rate: Target less than 0.1% defective products
- Customer satisfaction: Maintain 99%+ satisfaction rating
- Process capability: Cpk values greater than 1.33
- First-pass yield: Achieve 98%+ first-pass success rate

Corrective Actions:
- Root cause analysis: Investigate all quality issues
- Preventive measures: Implement controls to prevent recurrence
- Documentation: Maintain detailed quality records
- Continuous improvement: Regular review and enhancement of procedures
        """,
        "metadata": {
            "document_type": "quality",
            "facility": "FAB-1",
            "department": "Quality",
            "keywords": ["quality", "control", "inspection", "testing", "metrics"]
        }
    },
    {
        "id": "operations_004",
        "title": "Standard Operating Procedures",
        "content": """
STANDARD OPERATING PROCEDURES

Startup Procedures:
1. Pre-startup inspection: Check all systems before operation
2. System initialization: Follow proper startup sequence
3. Parameter verification: Confirm all settings are correct
4. Safety check: Ensure all safety systems are active
5. Documentation: Record startup parameters and times

Normal Operations:
- Monitor process parameters continuously
- Maintain equipment according to schedule
- Follow all safety protocols and procedures
- Document any deviations or abnormal conditions
- Communicate issues to supervision immediately

Shutdown Procedures:
1. Prepare for shutdown: Complete current operations safely
2. System shutdown: Follow proper shutdown sequence
3. Equipment securing: Ensure all equipment is properly secured
4. Documentation: Record shutdown parameters and conditions
5. Area inspection: Final check of work area before departure

Change Management:
- All process changes require engineering approval
- Document all modifications in the change control system
- Train personnel on new procedures before implementation
- Verify changes through testing and validation
        """,
        "metadata": {
            "document_type": "operations",
            "facility": "FAB-1",
            "department": "Operations",
            "keywords": ["operations", "procedures", "startup", "shutdown", "standard"]
        }
    },
    {
        "id": "training_005",
        "title": "Employee Training Requirements",
        "content": """
EMPLOYEE TRAINING REQUIREMENTS

New Employee Orientation:
- Safety training: 8-hour comprehensive safety program
- Equipment training: Hands-on training for assigned equipment
- Quality procedures: Understanding of quality standards
- Emergency procedures: Fire, chemical spill, and evacuation training
- Documentation: Complete training records and certifications

Ongoing Training:
- Annual safety refresher: Required for all employees
- Equipment updates: Training on new or modified equipment
- Quality improvements: Updates to quality procedures and standards
- Regulatory compliance: Training on new regulations and requirements

Specialized Training:
- Hazardous materials handling: For chemical operations personnel
- Confined space entry: For maintenance and repair teams
- Lock-out/tag-out procedures: For maintenance personnel
- Crane and rigging operations: For material handling teams

Training Documentation:
- Individual training records: Maintained for each employee
- Certification tracking: Monitor expiration dates and renewals
- Training effectiveness: Evaluate training program success
- Continuous improvement: Update training based on feedback and results
        """,
        "metadata": {
            "document_type": "training",
            "facility": "FAB-1",
            "department": "HR",
            "keywords": ["training", "employee", "certification", "safety", "procedures"]
        }
    }
]

def populate_bigquery_basic():
    """Populate BigQuery Basic implementation"""
    try:
        from cloud_shell_rag import GoogleCloudRAG
        
        print("🔄 Populating BigQuery Basic with test data...")
        rag = GoogleCloudRAG()
        
        # Create dataset and tables if needed
        rag.initialize_bigquery()
        
        # Add documents
        for doc in TEST_DOCUMENTS:
            print(f"   Adding: {doc['title']}")
            rag.add_document(doc['content'], doc['id'], doc.get('metadata', {}))
        
        print("✅ BigQuery Basic populated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error populating BigQuery Basic: {e}")
        return False

def populate_bigquery_enhanced():
    """Populate BigQuery Enhanced implementation"""
    try:
        from bigquery_rag_enhanced import BigQueryRAGEnhanced
        
        print("🔄 Populating BigQuery Enhanced with test data...")
        rag = BigQueryRAGEnhanced()
        
        # Initialize the system
        rag.initialize_bigquery()
        
        # Add documents
        for doc in TEST_DOCUMENTS:
            print(f"   Adding: {doc['title']}")
            result = rag.add_document(
                content=doc['content'],
                document_id=doc['id'],
                title=doc['title'],
                metadata=doc.get('metadata', {})
            )
            
        print("✅ BigQuery Enhanced populated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error populating BigQuery Enhanced: {e}")
        print(f"   Details: {str(e)[:200]}...")
        return False

def populate_rag_engine():
    """Populate RAG Engine implementation"""
    try:
        from rag_engine_implementation import RAGEngineImplementation
        
        print("🔄 Populating RAG Engine with test data...")
        rag = RAGEngineImplementation()
        
        # Create or get corpus
        rag.create_or_get_corpus()
        
        # Create test files and upload
        test_dir = Path("temp_test_docs")
        test_dir.mkdir(exist_ok=True)
        
        for doc in TEST_DOCUMENTS:
            doc_file = test_dir / f"{doc['id']}.txt"
            with open(doc_file, 'w') as f:
                f.write(f"Title: {doc['title']}\n\n")
                f.write(doc['content'])
            
            print(f"   Adding: {doc['title']}")
            rag.import_files([str(doc_file)])
        
        # Clean up temp files
        for file in test_dir.glob("*.txt"):
            file.unlink()
        test_dir.rmdir()
        
        print("✅ RAG Engine populated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error populating RAG Engine: {e}")
        return False

def main():
    print("🚀 Starting test data population...")
    print("=" * 60)
    
    # Determine which implementations to populate
    mode = os.getenv("RAG_DEPLOYMENT_MODE", "all")
    
    success_count = 0
    total_count = 0
    
    if mode in ["bigquery_basic", "all"]:
        total_count += 1
        if populate_bigquery_basic():
            success_count += 1
    
    if mode in ["bigquery_enhanced", "all"]:
        total_count += 1
        if populate_bigquery_enhanced():
            success_count += 1
    
    if mode in ["rag_engine", "all"]:
        total_count += 1
        if populate_rag_engine():
            success_count += 1
    
    print("=" * 60)
    print(f"📊 Population Summary: {success_count}/{total_count} implementations populated")
    
    if success_count > 0:
        print("\n🎯 Test Queries You Can Try:")
        print("   • What are the maintenance procedures?")
        print("   • What safety equipment is required?")
        print("   • How do I perform quality checks?")
        print("   • What are the training requirements?")
        print("   • What is the startup procedure?")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)