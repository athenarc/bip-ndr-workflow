import os
import json
import logging
import sys
from pymongo import MongoClient, timeout
from datetime import datetime as dt
from dotenv import load_dotenv


def get_keys():
    return {
        "mongo_db": os.getenv('MONGO_DB'),
        "mongo_coll": os.getenv('MONGO_COL'),
        "mongo_ip": os.getenv('MONGO_IP'),
        "mongo_user": os.getenv('MONGO_USER'),
        "mongo_pass": os.getenv('MONGO_PASS'),
        "dblp_dataset": os.getenv('DBLP_DATASET'),
        "stats": os.getenv('STATS_COLLECTION'),
        "pdf_path": os.getenv('PDF_PATH'),
        "tei_path": os.getenv('PDF_PATH'),
        "json_path": os.getenv('PDF_PATH'),
        "corpus_path": os.getenv('DBLP_CORPUS_PATH'),
        "logs_path": os.getenv('LOGS_PATH'),
        "grobid_config_path": os.getenv('GROBID_CONFIG_PATH')
    }


def connect_to_mongo_collection(db_name, collection_name, ip, username, password):
    """Connects to mongoDB collection"""
    try:
        # client = MongoClient()
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
