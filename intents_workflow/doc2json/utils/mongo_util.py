from pymongo import MongoClient
from doc2json.utils.env_util import get_keys


def connect_to_mongo_collection(db_name, collection_name, ip, username = None, password = None, auth = False):
    """Connects to mongoDB collection"""
    try:
        if auth:
            client = MongoClient(
                host=ip,
                username=username,
                password=password
            )
        else:
            client = MongoClient(host=ip)

        db = client[db_name]
        collection = db[collection_name]

        return collection
    except Exception as e:
        print(e)
        pass
