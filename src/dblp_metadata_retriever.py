import os
import json
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join("..", "logs", f"{os.path.basename(__file__).replace('.py', '.log')}")),
        logging.StreamHandler()
    ]
)


def get_keys():
    """
    Retrieves and returns a dictionary containing MongoDB connection keys.

    Returns:
        dict: Dictionary containing MongoDB connection keys.
    """

    return {
        "mongo_db": os.getenv('MONGO_DB'),
        "mongo_coll": os.getenv('MONGO_COL'),
        "dblp_dataset": os.getenv('DBLP_DATASET'),
        "stats": os.getenv('STATS_COLLECTION'),
        "mongo_ip": os.getenv('MONGO_IP'),
        "mongo_user": os.getenv('MONGO_USER'),
        "mongo_pass": os.getenv('MONGO_PASS')
    }


def connect_to_mongo_collection(db_name, collection_name, ip, username, password):
    """Connects to mongoDB collection"""

    client = MongoClient(
        host=ip,
        username=username,
        password=password
    )
    db = client[db_name]
    collection = db[collection_name]

    return collection


def lookup_dblp_id(collection, filename):
    """
    Looks up the DBLP ID associated with a given filename in a MongoDB collection.

    Args:
        collection: MongoDB collection to search for the DBLP ID.
        filename (str): The filename to search for.

    Returns:
        tuple or None: A tuple containing the DBLP ID and a boolean indicating if the reference file was parsed,
            or None if the DBLP ID is not found.
    """

    match_query_regex = {"key": {"$regex": filename.split('.')[0]}}
    match_query = {"filename": f"{filename.split('.')[0]}.pdf"}
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    if result_dict is not None:
        return result_dict['key'], result_dict['reference_file_parsed']
    else:
        logging.info(f"DBLP id for file {filename.split('.')[0]} not found. Skipping...")
        logging.info("")
        logging.info("---------------------")
        logging.info("")
        return None, None


def lookup_by_doi(collection, pub_doi):
    """
    Looks up a publication by its DOI in a MongoDB collection.

    Args:
        collection: MongoDB collection to search for the publication.
        pub_doi (str): The DOI of the publication.

    Returns:
        dict or None: A dictionary containing the publication information if found, or None if not found.
    """

    match_query_regex = {
        "ee": {
            "$regex": pub_doi,
            '$options': 'i'
        }
    }

    match_query = {
        'ee': f'https://doi.org/{pub_doi}'
    }
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    return result_dict


def lookup_by_title(collection, pub_title):
    """
    Looks up a publication by its title in a MongoDB collection.

    Args:
        collection: MongoDB collection to search for the publication.
        pub_title (str): The title of the publication.

    Returns:
        dict or None: A dictionary containing the publication information if found, or None if not found.
    """

    if pub_title is not None:

        match_query_regex = {
            "title": {
                "$regex": pub_title,
                '$options': 'i'
            }
        }

        match_query = {
            "title_concat": ''.join(filter(str.isalnum, pub_title))
        }

        result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
        return result_dict
    else:
        return None


def parse_biblstruct(collection, bib_entry):
    """
    Parses a bibliographic entry and extracts relevant information.

    Args:
        collection: The collection of bibliographic entries.
        bib_entry: The bibliographic entry to parse.

    Returns:
        A tuple containing the parsed information:
            - bib_entry_dict: A dictionary containing the parsed information:
                - 'dblp_id': The DBLP key of the publication (if available).
                - 'doi': The DOI of the publication (if available).
                - 'doi_url': The URL associated with the DOI (if available).
                - 'bibliographic_reference': The raw bibliographic reference.
            - refs_checked: The number of references checked.
            - refs_skipped: The number of references skipped.
            - dois_matched: The number of DOIs matched.
            - dblp_keys_matched: The number of DBLP keys matched.

    """

    refs_checked = 0
    refs_skipped = 0
    dois_matched = 0
    dblp_keys_matched = 0

    pub_doi = None
    pub_dblp_key = None
    pub_title = None
    raw_reference = None
    doi_url = None

    bib_entry_dict = []

    refs_checked += 1
    logging.info('')

    if "analytic" in bib_entry:
        if bib_entry["analytic"] is not None:
            if "idno" in bib_entry["analytic"]:
                if type(bib_entry["analytic"]["idno"]) == list:
                    for idno in bib_entry["analytic"]["idno"]:
                        if type(idno) == dict:
                            if "@type" in idno:
                                if idno["@type"] == "DOI":
                                    if "#text" in idno:
                                        pub_doi = idno["#text"]
                else:
                    if "@type" in bib_entry["analytic"]["idno"]:
                        if bib_entry["analytic"]["idno"]["@type"] == "DOI":
                            pub_doi = bib_entry["analytic"]["idno"]["#text"]

            if "title" in bib_entry["analytic"]:
                if bib_entry["analytic"]["title"] is not None:
                    if "#text" in bib_entry["analytic"]["title"]:
                        pub_title = bib_entry["analytic"]["title"]["#text"]
            else:
                if "monogr" in bib_entry:
                    if "title" in bib_entry["monogr"]:
                        if bib_entry["monogr"]:
                            if bib_entry["monogr"]["title"] is not None:
                                if "#text" in bib_entry["monogr"]["title"]:
                                    pub_title = bib_entry["monogr"]["title"]["#text"]
        else:
            if "monogr" in bib_entry:
                if "title" in bib_entry["monogr"]:
                    if bib_entry["monogr"]:
                        if bib_entry["monogr"]["title"] is not None:
                            if "#text" in bib_entry["monogr"]["title"]:
                                pub_title = bib_entry["monogr"]["title"]["#text"]
    else:
        if "title" in bib_entry["monogr"]:
            if bib_entry["monogr"]["title"] is not None:
                if "#text" in bib_entry["monogr"]["title"]:
                    pub_title = bib_entry["monogr"]["title"]["#text"]

    if type(bib_entry["note"]) == list:
        for note in bib_entry["note"]:
            if type(note) == dict:
                raw_reference = note["#text"]
    else:
        raw_reference = bib_entry["note"]["#text"]

    if pub_doi is not None:
        logging.info(f"DOI: {pub_doi}")
        result_dict = lookup_by_doi(collection, pub_doi)
        if result_dict is not None:
            logging.info("DOI Match!")
            dois_matched += 1
            doi_url = [item for item in result_dict['ee'] if 'doi' in item][0]
            logging.info(f"Matched DOI URL: {doi_url}")
            pub_dblp_key = result_dict['key']
            dblp_keys_matched += 1
            logging.info(f"DBLP KEY: {pub_dblp_key}")
        else:
            logging.info("No DOI match, trying Title...")
            logging.info(f"Title: {pub_title}")
            result_dict = lookup_by_title(collection, pub_title)
            if result_dict is not None:
                logging.info("Title Match!")
                logging.info(f"Matched Title: {result_dict['title']}")
                pub_dblp_key = result_dict['key']
                dblp_keys_matched += 1
                logging.info(f"DBLP KEY: {pub_dblp_key}")
            else:
                refs_skipped += 1
                logging.info("No DOI or Title match. Skipping...")
    else:
        logging.info("No DOI found in bib entry, trying Title...")
        logging.info(f"Title: {pub_title}")
        if pub_title is not None:
            result_dict = lookup_by_title(collection, pub_title)
            if result_dict is not None:
                logging.info("Title Match!")
                logging.info(f"Matched Title: {result_dict['title']}")
                pub_dblp_key = result_dict['key']
                dblp_keys_matched += 1
                logging.info(f"DBLP KEY: {pub_dblp_key}")
            else:
                refs_skipped += 1
                logging.info("No DOI or Title match. Skipping...")
        else:
            refs_skipped += 1
            logging.info("No DOI or Title match. Skipping...")

    if pub_dblp_key and pub_doi:
        bib_entry_dict = {
            "dblp_id": pub_dblp_key,
            "doi": pub_doi,
            "doi_url": doi_url,
            "bibliographic_reference": raw_reference
        }
    elif pub_dblp_key and pub_title:
        bib_entry_dict = {
            "dblp_id": pub_dblp_key,
            "bibliographic_reference": raw_reference
        }
    elif pub_doi and not pub_dblp_key:
        bib_entry_dict = {
            "doi": pub_doi,
            "bibliographic_reference": raw_reference
        }

    return bib_entry_dict, refs_checked, refs_skipped, dois_matched, dblp_keys_matched


def get_dblp_meta(collection, json_dict):
    """
    Retrieve metadata from a JSON dictionary with bibliographic references.

    Args:
        collection (str): The name of the collection to search in.
        json_dict (dict): The JSON dictionary containing bibliographic information.

    Returns:
        tuple: A tuple containing:
            - bib_entries (list): A list of parsed bibliographic entries.
            - bib_refs_checked (int): The total number of references checked.
            - bib_refs_skipped (int): The total number of references skipped.
            - bib_dois_matched (int): The total number of DOIs matched.
            - bib_dblp_keys_matched (int): The total number of DBLP keys matched.
    """

    bib_refs_checked = 0
    bib_refs_skipped = 0
    bib_dois_matched = 0
    bib_dblp_keys_matched = 0

    bib_entries = []
    bib_entry_dict = []

    if type(json_dict['biblStruct']) == list:
        for bib_entry in json_dict["biblStruct"]:
            bib_entry_dict, refs_checked, refs_skipped, dois_matched, dblp_keys_matched = parse_biblstruct(collection, bib_entry)
            bib_refs_checked += refs_checked
            bib_refs_skipped += refs_skipped
            bib_dois_matched += dois_matched
            bib_dblp_keys_matched += dblp_keys_matched
            if len(bib_entry_dict) != 0:
                bib_entries.append(bib_entry_dict)
    elif type(json_dict['biblStruct']) == dict:
        bib_entry = json_dict['biblStruct']
        bib_entry_dict, refs_checked, refs_skipped, dois_matched, dblp_keys_matched = parse_biblstruct(collection, bib_entry)
        bib_refs_checked += refs_checked
        bib_refs_skipped += refs_skipped
        bib_dois_matched += dois_matched
        bib_dblp_keys_matched += dblp_keys_matched
        if len(bib_entry_dict) != 0:
            bib_entries.append(bib_entry_dict)

    return bib_entries, bib_refs_checked, bib_refs_skipped, bib_dois_matched, bib_dblp_keys_matched


def iterate_json_reference_files(inproceedings_collection, dataset_collection, stats_collection, json_filepath, stats):
    """
    Iterate over JSON reference files, extract metadata, and update MongoDB collections.

    Args:
        inproceedings_collection (collection): The collection for inproceedings data.
        dataset_collection (collection): The collection for dataset data.
        stats_collection (collection): The collection for statistics data.
        json_filepath (str): The path to the directory containing JSON files.
        stats (dict): A dictionary containing statistics.

    Returns:
        dict: A dictionary containing updated statistics.
    """

    for fl in os.scandir(json_filepath):

        bib_refs_checked = 0
        bib_refs_skipped = 0
        bib_dois_matched = 0
        bib_dblp_keys_matched = 0

        if fl.is_file():
            bib_entries = []

            dblp_id, file_checked = lookup_dblp_id(inproceedings_collection, fl.name)

            if dblp_id is not None:
                if file_checked is False:
                    logging.info("")
                    logging.info(f'Checking file with dblp_id: {dblp_id}')
                    with open(fl, "r", encoding="utf-8") as json_file:
                        json_dict = json.load(json_file)
                        bib_entries, bib_refs_checked, bib_refs_skipped, bib_dois_matched, bib_dblp_keys_matched = get_dblp_meta(inproceedings_collection, json_dict)

                    dblp_entry_dict = {
                        "citing_paper": {
                            "dblp_id": dblp_id,
                        },
                        "cited_papers": bib_entries
                    }

                    stats['total_files_checked'] += 1
                    stats['total_refs_checked'] += bib_refs_checked
                    stats['total_refs_skipped'] += bib_refs_skipped
                    stats['total_dois_matched'] += bib_dois_matched
                    stats['total_dblp_keys_matched'] += bib_dblp_keys_matched

                    logging.info("")
                    logging.info("---------------------")
                    logging.info(f'Refs checked: {bib_refs_checked}')
                    logging.info(f'Refs skipped: {bib_refs_skipped}')
                    logging.info(f'DOIs matched: {bib_dois_matched}')
                    logging.info(f'DBLP keys matched: {bib_dblp_keys_matched}')
                    logging.info("---------------------")

                    inproceedings_collection.update_one(
                        {"key": dblp_id},
                        {"$set": {"reference_file_parsed": True}},
                        collation={'locale': 'en', 'strength': 2}
                    )
                    dataset_collection.insert_one(dblp_entry_dict)

                    stats_collection.update_one(
                        {"key": "statistics"},
                        {
                            "$set": {
                                "total_files_checked": stats["total_files_checked"],
                                "total_refs_checked": stats["total_refs_checked"],
                                "total_refs_skipped": stats["total_refs_skipped"],
                                "total_dois_matched": stats["total_dois_matched"],
                                "total_dblp_keys_matched": stats["total_dblp_keys_matched"]
                            }
                        }
                    )

    return stats


def main():
    """
    Entry point for the program. Processes JSON reference files and logs processing results.

    Returns:
        None
    """

    json_filepath = os.path.join("..", "data", "json_References")  # path to the folder containing the json bib files - Default: json_references

    inproceedings_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['mongo_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    dblp_dataset_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['dblp_dataset'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    stats_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['stats'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    stats = stats_collection.find()[0]
    # print(stats[0])
    stats["total_files_checked"] = int(stats["total_files_checked"])
    stats["total_refs_checked"] = int(stats["total_refs_checked"])
    stats["total_refs_skipped"] = int(stats["total_refs_skipped"])
    stats["total_dois_matched"] = int(stats["total_dois_matched"])
    stats["total_dblp_keys_matched"] = int(stats["total_dblp_keys_matched"])

    logging.info("----------------------------Starting up----------------------------")
    stats = iterate_json_reference_files(inproceedings_collection, dblp_dataset_collection, stats_collection, json_filepath, stats)

    logging.info('')
    logging.info(f'Total Files checked: {stats["total_files_checked"]}')
    logging.info(f'Total Refs checked: {stats["total_refs_checked"]}')
    logging.info(f'Total Refs skipped: {stats["total_refs_skipped"]}')
    logging.info(f'Total DOIs matched: {stats["total_dois_matched"]}')
    logging.info(f'Total DBLP keys matched: {stats["total_dblp_keys_matched"]}')


if __name__ == "__main__":
    main()
