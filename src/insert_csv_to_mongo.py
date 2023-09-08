import os
import sys
import logging
import pandas as pd
import numpy as np
from pymongo import MongoClient, timeout
from datetime import datetime as dt
from dotenv import load_dotenv

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join("logs", f"{os.path.basename(__file__).replace('.py', '.log')}"))  # ,
        # logging.StreamHandler()
    ]
)


def split_concat_cells(df, concat_values):
    for value in concat_values:
        has_nan = df[value].isna()
        if df[value].notna().any():
            df.loc[~has_nan, value] = df.loc[~has_nan, value].apply(lambda x: x.replace('...|', '')).str.split('|')
    return df


def document_generator(df):
    for record in df.to_dict('records'):
        yield record


def get_keys():

    return {
        "mongo_db": os.getenv('MONGO_DB'),
        "mongo_coll": os.getenv('MONGO_COL'),
        "mongo_ip": os.getenv('MONGO_IP'),
        "mongo_user": os.getenv('MONGO_USER'),
        "mongo_pass": os.getenv('MONGO_PASS')
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


if __name__ == "__main__":
    load_dotenv()
    corpus_files = ["full_corpus_inproceedings.csv", "head_inproceedings.csv", "sm_head_inproceedings.csv", "full_corpus_article.csv"]

    article_fl = sys.argv[1]

    filepath = os.path.join(os.sep, "data", "dblp_corpus", "csv_split_by_type", "articles_csv", f"full_corpus_article_split_{article_fl}.csv")

    concat_values = ['author', 'author-orcid', 'cite', 'cite-label', 'ee', 'ee-type']

    collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['mongo_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    input_dblp_file = pd.read_csv(filepath, sep=";", low_memory=False)
    input_dblp_file = split_concat_cells(input_dblp_file, concat_values).replace(np.nan, '', regex=True)
    # input_dblp_file = input_dblp_file.replace(np.nan, '', regex=True)

    # mongo shell title_concat:
    # db.manuscript_metadata.find().forEach(function(doc) { doc.title_concat = doc.title.replace(/[^A-Za-z0-9]/g, '');db.manuscript_metadata.save(doc) });

    for document in document_generator(input_dblp_file):
        try:
            with timeout(2):
                collection.insert_one(document)
                logging.info(f'Successfully inserted document with ID: {document["id"]}')
        except Exception as e:
            logging.info(f'Insertion of document {document["id"]} failed. Error message: {e}')
