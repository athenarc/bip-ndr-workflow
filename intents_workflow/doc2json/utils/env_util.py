"""
Environment Configuration Utility

Provides centralized access to environment variables for the doc2json project.
"""

import os


def get_keys():
    """
    Retrieve all environment configuration keys.
    
    Returns:
        Dictionary containing all environment variables used by the project.
        
    Environment Variables:
        MongoDB Configuration:
            - MONGO_IP: MongoDB server address
            - MONGO_USER: MongoDB username (optional)
            - MONGO_PASS: MongoDB password (optional)
            - MONGO_DB: Database name
            - PAPERS_COL: Papers collection name
            - DBLP_DATASET: DBLP dataset collection name
            - STATS_COLLECTION: Statistics collection name
            
        Path Configuration:
            - PDF_PATH: Path to PDF files
            - TEI_PATH: Base path to TEI XML files
            - JSON_PATH: Path to JSON output files
            - CORPUS_PATH: Path to DBLP corpus
            - LOGS_PATH: Path to log files
            
        Tool Configuration:
            - GROBID_CONFIG_PATH: Path to GROBID configuration
            - PUB_RETRIEVER_PATH: Path to publication retriever
            
        Processing Configuration:
            - MODE: Processing mode (e.g., 'FullText', 'FullTextSegmented')
            - LATEST_DATE: Latest DBLP Dump date
            
        Dataset Generation Configuration:
            - S2ORC_JSONL_PATH: Base directory for S2ORC JSONL output files
            - CITATION_API_URL: URL endpoint for external Citation Intent API service
            - OUTPUT_DATASET_PATH: Path for final dataset output (optional)
    """
    return {
        "mongo_ip": os.getenv('MONGO_IP'),
        "mongo_user": os.getenv('MONGO_USER'),
        "mongo_pass": os.getenv('MONGO_PASS'),
        "mongo_db": os.getenv('MONGO_DB'),
        "papers_coll": os.getenv('PAPERS_COL'),
        "dblp_dataset": os.getenv('DBLP_DATASET'),
        "stats": os.getenv('STATS_COLLECTION'),
        "pdf_path": os.getenv('PDF_PATH'),
        "tei_path": os.getenv('TEI_PATH'),
        "json_path": os.getenv('JSON_PATH'),
        "corpus_path": os.getenv('DBLP_CORPUS_PATH'),
        "logs_path": os.getenv('LOGS_PATH'),
        "grobid_config_path": os.getenv('GROBID_CONFIG_PATH'),
        "pub_retriever_path": os.getenv('PUB_RETRIEVER_PATH'),
        "mode": os.getenv('MODE'),
        "latest_date": os.getenv('LATEST_DATE'),
        "s2orc_jsonl_path": os.getenv('S2ORC_JSONL_PATH'),
        "citation_api_url": os.getenv('CITATION_API_URL'),
        "output_dataset_path": os.getenv('OUTPUT_DATASET_PATH')
    }
