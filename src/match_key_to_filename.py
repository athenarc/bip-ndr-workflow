import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join("logs", f"{os.path.basename(__file__).replace('.py', '.log')}")),
        logging.StreamHandler()
    ]
)


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

    pdf_path = os.path.join("..", "data", "PDFs")

    load_dotenv()

    collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['mongo_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    logging.info("----------------------------Starting up----------------------------")
    for fl in os.scandir(pdf_path):
        if fl.is_file() and fl.name.endswith(".pdf"):

            match_query = {"key_norm": fl.name.split('.')[0], "PDF_downloaded": False}
            update_query = {"$set": {"PDF_downloaded": True, "filename_norm": fl.name}}

            result = collection.update_one(match_query, update_query, collation={'locale': 'en', 'strength': 2})
            if result.modified_count > 0:
                logging.info(f"Successfully updated DB. Added filename to key: {fl.name.split('.')[0]}.")
            else:
                logging.info(f"Filename {fl.name} already in DB. Skipping...")
