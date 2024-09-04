import pandas as pd
import numpy as np
import re
import jsonlines
from utils.helper_utils import *
from glob2 import glob

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(get_keys()["logs_path"], f"{os.path.basename(__file__).replace('.py', '.log')}")),
        # logging.StreamHandler()
    ]
)


def create_download_object(corpus_path, latest_date):
    """
    Generates a download object and saves it to a JSON file.

    :param corpus_path: Path to the DBLP corpus directory.
    :param latest_date: The latest date for which the download object is created.

    :return: None
    """
    logging.info("----------------------------Starting up Download Object Generator----------------------------")
    match_query = {
        "$and": [
            {"ee-type": "oa"},
            {"import_date": latest_date},
            {"ee": {"$not": {"$regex": "doi"}}}]
    }
    json_data = []
    for doc in collection.find(match_query, collation={'locale': 'en', 'strength': 2}):

        id_value = doc['key_norm']
        json_entry = {
            'id': id_value,
            'url': doc['ee'][0]
        }
        json_data.append(json_entry)

        filepath = os.path.join(corpus_path, "DL_Object")
        if not os.path.exists(os.path.join(filepath, "input")):
            os.makedirs(os.path.join(filepath, "input"))
        if not os.path.exists(os.path.join(filepath, "output")):
            os.makedirs(os.path.join(filepath, "output"))

    with jsonlines.open(os.path.join(filepath, "input", "input_urls.jsonl"), mode="w") as writer:
        writer.write_all(json_data)

    
def match_key_to_filename(pdf_path):
    """
    Matches DBLP keys to filenames for downloaded PDFs.

    :param pdf_path: Path to the directory containing PDF files.

    :return: None
    """
    logging.info("----------------------------Starting up Key to Filename Matching----------------------------")
    for fl in os.scandir(pdf_path):
        if fl.is_file() and fl.name.endswith(".pdf"):

            match_query = {"key_norm": fl.name.split('.')[0], "PDF_downloaded": False}
            update_query = {"$set": {"PDF_downloaded": True, "filename_norm": fl.name}}

            result = collection.update_one(match_query, update_query, collation={'locale': 'en', 'strength': 2})
            if result.modified_count > 0:
                logging.info(f"Successfully updated DB. Added filename to key: {fl.name.split('.')[0]}.")
            else:
                logging.info(f"Filename {fl.name} already in DB. Skipping...")


def import_to_mongo(input_dblp_file):
    """
    Imports data from a CSV file to a MongoDB collection.

    :param input_dblp_file: DataFrame containing CSV file data.

    :return: None
    """

    logging.info("----------------------------Starting up Mongo Importer----------------------------")
    for document in document_generator(input_dblp_file):
        if collection.find_one({"key": document['key']}, collation={'locale': 'en', 'strength': 2}):
            logging.info(f"Document with key: {document['key']} already exists in collection. Skipping...")
        else:
            try:
                with timeout(2):
                    collection.insert_one(document)
                    logging.info(f"Successfully inserted document with key: {document['key']}")
            except Exception as e:
                logging.info(f"Insertion of document with key: {document['key']} failed. Error message: {e}")


def split_concat_cells(df, concat_values):
    """
    Splits concatenated cell values in a DataFrame.

    :param df: The DataFrame to process.
    :param concat_values: List of column names with concatenated values.

    :return: DataFrame with split values.
    """
    for value in concat_values:
        has_nan = df[value].isna()
        if df[value].notna().any():
            df.loc[~has_nan, value] = df.loc[~has_nan, value].apply(lambda x: x.replace('...|', '')).str.split('|')
    return df


def document_generator(df):
    """
    Generates documents for insertion into MongoDB from a DataFrame.

    :param df: The DataFrame to process.

    :yield: Document dictionary for insertion into MongoDB.
    """
    for doc in df.to_dict('records'):
        doc['title_concat'] = re.sub(r'\W+', '', doc['title'])
        doc['key_norm'] = doc['key'].replace("/", "_")
        # doc['filename_norm'] = f"{doc['key_norm']}.pdf"
        doc['PDF_downloaded'] = False
        doc['reference_file_parsed'] = False
        doc['import_date'] = get_keys()['latest_date']
        # print(doc)
        yield doc


if __name__ == "__main__":
    load_dotenv()

    latest_date = get_keys()['latest_date']
    pdf_path = get_keys()['pdf_path']
    corpus_path = get_keys()['corpus_path']
    corpus_path = os.path.join(get_keys()['corpus_path'], f"dblp-{latest_date}")
    csv_files = [
        f"dblp_{latest_date}_inproceedings.csv",
        f"dblp_{latest_date}_article.csv"
    ]

    collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['papers_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    concat_values = ['author', 'author-orcid', 'cite', 'cite-label', 'ee', 'ee-type']

    if len(sys.argv) > 0:   # TODO: remake cli functionality with click
        command = int(sys.argv[1])
        batches = False
        batch_num = None

        if command == 0:
            # if command is import-to-mongo
            for input_file in csv_files:
                input_dblp_file = pd.read_csv(os.path.join(corpus_path, input_file), sep=";", low_memory=False)
                input_dblp_file = split_concat_cells(input_dblp_file, concat_values).replace(np.nan, '', regex=True)
                import_to_mongo(input_dblp_file)
        elif command == 1:
            # if command is create-download-object
            create_download_object(corpus_path, latest_date)
        elif command == 2:
            # if command is match-key-to-filename
            if len(sys.argv) > 2:
                if sys.argv[2] == '--batch':
                    # if flag --batch exists, process only the DocFiles folders

                    if len(sys.argv) > 3:
                        if sys.argv[3] == 'all':
                            # if option is "all" process all the DocFiles folders
                            batch_dirs = [folder for folder in glob(os.path.join(pdf_path, "DocFiles_*")) if os.path.isdir(folder)]

                            for batch_dir in batch_dirs:
                                logging.info(f"Processing batch number {batch_dir.split('_')[-1]}...")
                                match_key_to_filename(batch_dir)
                        elif sys.argv[3].isnumeric():
                            # if option is a batch number that exists, process only the corresponding DocFiles folder
                            batch_num = sys.argv[3]
                            batch_dir = os.path.join(pdf_path, f"DocFiles_{batch_num}")
                            batch_dir = batch_dir if os.path.isdir(batch_dir) else None

                            if batch_dir is not None:
                                logging.info(f"Processing batch number {batch_num}...")
                                match_key_to_filename(batch_dir)
                            else:
                                logging.error(f"Batch folder with number: {batch_num}, doesn't exist. Exiting...")
                                exit
                        else:
                            logging.error("Unknown option for flag \"--batch\". Exiting...")
                            exit
                    else:
                        logging.error("No option selected for flag \"--batch\". Exiting...")
                        exit
                else:
                    logging.error("Unknown flag. Exiting...")
                    exit
            else:
                logging.info("No batch selected, processing entire PDF folder...")
                match_key_to_filename(pdf_path)
    else:
        logging.error("No option selected. Exiting...")
        exit