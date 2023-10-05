from utils import *


logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join("logs", f"{os.path.basename(__file__).replace('.py', '.log')}")),
        logging.StreamHandler()
    ]
)


def create_stats_collection():
    init_stats = {
        "key": "statistics",
        "total_files_checked": 0,
        "total_refs_checked": 0,
        "total_refs_skipped": 0,
        "total_dois_matched": 0,
        "total_dois_dblp": 0,
        "total_dblp_keys_matched": 0
    }

    coll = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=f"{get_keys()['stats']}_{dt.today().strftime('%d-%m-%Y')}",
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    coll.insert_one(init_stats)

    return coll


def reset_papers_collection(papers_collection):
    papers_collection.update_one(
        {"reference_file_parsed": True},
        {"$set": {"reference_file_parsed": False}},
        collation={'locale': 'en', 'strength': 2}
    )


def lookup_dblp_id(collection, filename):
    match_query = {"key_norm": f"{filename.split('.')[0]}"}
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
    match_query = {
        'ee': f'https://doi.org/{pub_doi}'
    }
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    return result_dict


def lookup_by_title(collection, pub_title):
    if pub_title is not None:

        match_query = {
            "title_concat": ''.join(filter(str.isalnum, pub_title))
        }

        result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
        return result_dict
    else:
        return None


def parse_biblstruct(collection, bib_entry):

    refs_checked = 0
    refs_skipped = 0
    dois_matched = 0
    dois_dblp = 0
    dblp_keys_matched = 0

    pub_doi = None
    pub_dblp_key = None
    pub_title = None
    raw_reference = None
    doi_url = None
    doi_dblp = None

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
                doi_dblp = [item for item in result_dict['ee'] if 'doi' in item]
                if len(doi_dblp) != 0:
                    doi_dblp = doi_dblp[0].split('.org/')[-1]
                    logging.info("Retrieved DOI from DBLP")
                    dois_dblp += 1
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
            "bibliographic_reference": raw_reference
        }
    elif pub_dblp_key and pub_title:
        if doi_dblp:
            bib_entry_dict = {
                "dblp_id": pub_dblp_key,
                "doi": doi_dblp,
                "bibliographic_reference": raw_reference
            }
        else:
            bib_entry_dict = {
                "dblp_id": pub_dblp_key,
                "bibliographic_reference": raw_reference
            }
    elif pub_doi and not pub_dblp_key:
        bib_entry_dict = {
            "doi": pub_doi,
            "bibliographic_reference": raw_reference
        }

    return bib_entry_dict, refs_checked, refs_skipped, dois_matched, dois_dblp, dblp_keys_matched


def get_dblp_meta(collection, json_dict):

    bib_refs_checked = 0
    bib_refs_skipped = 0
    bib_dois_matched = 0
    bib_dois_dblp = 0
    bib_dblp_keys_matched = 0

    bib_entries = []
    bib_entry_dict = []

    if type(json_dict['biblStruct']) == list:
        for bib_entry in json_dict["biblStruct"]:
            bib_entry_dict, refs_checked, refs_skipped, dois_matched, dois_dblp, dblp_keys_matched = parse_biblstruct(collection, bib_entry)
            bib_refs_checked += refs_checked
            bib_refs_skipped += refs_skipped
            bib_dois_matched += dois_matched
            bib_dois_dblp += dois_dblp
            bib_dblp_keys_matched += dblp_keys_matched
            if len(bib_entry_dict) != 0:
                bib_entries.append(bib_entry_dict)
    elif type(json_dict['biblStruct']) == dict:
        bib_entry = json_dict['biblStruct']
        bib_entry_dict, refs_checked, refs_skipped, dois_matched, dois_dblp, dblp_keys_matched = parse_biblstruct(collection, bib_entry)
        bib_refs_checked += refs_checked
        bib_refs_skipped += refs_skipped
        bib_dois_matched += dois_matched
        bib_dois_dblp += dois_dblp
        bib_dblp_keys_matched += dblp_keys_matched
        if len(bib_entry_dict) != 0:
            bib_entries.append(bib_entry_dict)

    return bib_entries, bib_refs_checked, bib_refs_skipped, bib_dois_matched, bib_dois_dblp, bib_dblp_keys_matched


def iterate_json_reference_files(papers_collection, dataset_collection, stats_collection, json_path, stats):

    for fl in os.scandir(json_path):

        bib_refs_checked = 0
        bib_refs_skipped = 0
        bib_dois_matched = 0
        bib_dois_dblp = 0
        bib_dblp_keys_matched = 0

        try:
            if fl.is_file():
                bib_entries = []

                dblp_id, file_checked = lookup_dblp_id(papers_collection, fl.name)

                if dblp_id is not None:
                    if file_checked is False:
                        logging.info("")
                        logging.info(f'Checking file with dblp_id: {dblp_id}')
                        with open(fl, "r", encoding="utf-8") as json_file:
                            json_dict = json.load(json_file)
                            bib_entries, bib_refs_checked, bib_refs_skipped, bib_dois_matched, bib_dois_dblp, bib_dblp_keys_matched = get_dblp_meta(papers_collection, json_dict)

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
                        stats['total_dois_dblp'] += bib_dois_dblp
                        stats['total_dblp_keys_matched'] += bib_dblp_keys_matched

                        logging.info("")
                        logging.info("---------------------")
                        logging.info(f'Refs checked: {bib_refs_checked}')
                        logging.info(f'Refs skipped: {bib_refs_skipped}')
                        logging.info(f'DOIs matched: {bib_dois_matched}')
                        logging.info(f'DOI retrieved from DBLP: {bib_dois_dblp}')
                        logging.info(f'DBLP keys matched: {bib_dblp_keys_matched}')
                        logging.info("---------------------")

                        papers_collection.update_one(
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
                                    "total_dois_dblp": stats["total_dois_dblp"],
                                    "total_dblp_keys_matched": stats["total_dblp_keys_matched"]
                                }
                            }
                        )
        except Exception as e:
            print(e)
            pass

    return stats


def main():
    load_dotenv()

    # json_path = os.path.join(os.sep, "data", "dblp_corpus", "full_corpus", "json_references")
    # json_path = os.path.join(os.sep, "home", "pkoloveas", "Desktop", "dblp_corpus", "full_corpus", "json_references")
    # json_path = os.path.join("data")
    json_path = get_keys()['json_path']

    # dblp_dataset = []

    papers_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['papers_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    dblp_dataset_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=f"{get_keys()['dblp_dataset']}_{dt.today().strftime('%d-%m-%Y')}",
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    stats_collection = create_stats_collection()

    stats = stats_collection.find({"key": "statistics"})[0]
    # print(stats[0])
    stats["total_files_checked"] = int(stats["total_files_checked"])
    stats["total_refs_checked"] = int(stats["total_refs_checked"])
    stats["total_refs_skipped"] = int(stats["total_refs_skipped"])
    stats["total_dois_matched"] = int(stats["total_dois_matched"])
    stats["total_dois_dblp"] = int(stats["total_dois_dblp"])
    stats["total_dblp_keys_matched"] = int(stats["total_dblp_keys_matched"])

    reset_papers_collection(papers_collection)

    logging.info("----------------------------Starting up----------------------------")
    stats = iterate_json_reference_files(papers_collection, dblp_dataset_collection, stats_collection, json_path, stats)

    logging.info('')
    logging.info(f'Total Files checked: {stats["total_files_checked"]}')
    logging.info(f'Total Refs checked: {stats["total_refs_checked"]}')
    logging.info(f'Total Refs skipped: {stats["total_refs_skipped"]}')
    logging.info(f'Total DOIs matched: {stats["total_dois_matched"]}')
    logging.info(f'Total DOIs retrieved from DBLP: {stats["total_dois_dblp"]}')
    logging.info(f'Total DBLP keys matched: {stats["total_dblp_keys_matched"]}')


if __name__ == "__main__":
    main()
