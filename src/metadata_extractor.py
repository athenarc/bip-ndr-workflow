import pandas as pd
import numpy as np
from src.utils import *


logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join("logs", f"{os.path.basename(__file__).replace('.py', '.log')}"))  # ,
        # logging.StreamHandler()
    ]
)

# TODO: add create_downloadl_object() function


def match_key_to_filename(pdf_path):

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

    logging.info("----------------------------Starting up Mongo Importer----------------------------")
    for document in document_generator(input_dblp_file):
        try:
            with timeout(2):
                collection.insert_one(document)
                logging.info(f'Successfully inserted document with ID: {document["id"]}')
        except Exception as e:
            logging.info(f'Insertion of document {document["id"]} failed. Error message: {e}')


def split_concat_cells(df, concat_values):
    for value in concat_values:
        has_nan = df[value].isna()
        if df[value].notna().any():
            df.loc[~has_nan, value] = df.loc[~has_nan, value].apply(lambda x: x.replace('...|', '')).str.split('|')
    return df


def document_generator(df):
    for record in df.to_dict('records'):
        yield record


if __name__ == "__main__":
    load_dotenv()

    # pdf_path = os.path.join("..", "data", "PDFs")
    pdf_path = get_keys()['pdf_path']

    # article_fl = sys.argv[1]
    # corpus_files = ["full_corpus_inproceedings.csv", "head_inproceedings.csv", "sm_head_inproceedings.csv", "full_corpus_article.csv"]
    # corpus_path = os.path.join(os.sep, "data", "DBLP_corpus", "csv_split_by_type", "articles_csv", f"full_corpus_article_split_{article_fl}.csv")
    corpus_path = get_keys()['corpus_path']

    collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['mongo_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass']
    )

    concat_values = ['author', 'author-orcid', 'cite', 'cite-label', 'ee', 'ee-type']

    input_dblp_file = pd.read_csv(corpus_path, sep=";", low_memory=False)
    input_dblp_file = split_concat_cells(input_dblp_file, concat_values).replace(np.nan, '', regex=True)
    # input_dblp_file = input_dblp_file.replace(np.nan, '', regex=True)

    # mongo shell title_concat:
    # db.manuscript_metadata.find().forEach(function(doc) { doc.title_concat = doc.title.replace(/[^A-Za-z0-9]/g, '');db.manuscript_metadata.save(doc) });

    import_to_mongo(input_dblp_file)
    match_key_to_filename(pdf_path)
