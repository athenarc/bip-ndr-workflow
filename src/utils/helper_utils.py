import os
import json
import logging
import sys
from pymongo import MongoClient, timeout
from datetime import datetime as dt
from dotenv import load_dotenv, set_key


def get_keys():
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
        "latest_date": os.getenv('LATEST_DATE')
    }


def connect_to_mongo_collection(db_name, collection_name, ip, username, password):
    """Connects to mongoDB collection"""
    try:
        client = MongoClient(
            host=ip,
            username=username,
            password=password
        )
        db = client[db_name]
        collection = db[collection_name]

        return collection
    except Exception as e:
        print(e)
        pass
