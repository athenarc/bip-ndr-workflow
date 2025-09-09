import requests
import re
from utils.helper_utils import *
from bs4 import BeautifulSoup

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(get_keys()["logs_path"], get_keys()["latest_date"], f"{os.path.basename(__file__).replace('.py', '.log')}")),
        logging.StreamHandler()
    ]
)


def get_file(url, path, headers):
    """
    Downloads a file from a given URL and saves it to the specified path.

    :param url (str): The URL of the file to be downloaded.
    :param path (str): The local path where the file will be saved.
    :param headers (dict): HTTP headers to be included in the request.

    :return: None
    """

    logging.info(f"Downloading file {url.split('/')[-1]}")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        with open(path, "wb") as f:
            f.write(response.content)
        logging.info(f"Download complete")
    else:
        logging.info(f"URL: \"{url}\" returned status code: {response.status_code}")


def update_latest_date_in_env(latest_date, env_file_path=".env"):
    """
    Updates the LATEST_DATE variable in the .env file with the latest date.

    :param latest_date (str): The new date to be set in the .env file.
    :param env_file_path (str): The path to the .env file.

    :return: None
    """
    logging.info(f"Updating LATEST_DATE in {env_file_path} to {latest_date}")

    # Load the .env file
    load_dotenv(env_file_path)

    # Update the LATEST_DATE variable
    set_key(env_file_path, "LATEST_DATE", latest_date)

if __name__ == "__main__":
    load_dotenv()

    corpus_path = get_keys()['corpus_path']
    release_url = "https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml"
    artifact_base_url = "https://drops.dagstuhl.de/entities/artifact/10.4230/"
    storage_base_url = "https://drops.dagstuhl.de/storage/artifacts/dblp/xml/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36"
    }

    response = requests.get(release_url, headers=headers, timeout=4)

    soup = BeautifulSoup(response.text, 'html.parser')
    links = str(soup.find_all('a', href=True))

    print(links)

    latest_artifact = re.findall(r'dblp\.xml\.\d+-\d+-\d+', links)[0]
    latest_date = re.findall(r'\d+-\d+-\d+', latest_artifact)[0]
    artifact_year = latest_date.split('-')[0]

    print(latest_artifact)
    
    artifact_url = f"{artifact_base_url}{latest_artifact}"
    print(artifact_url)

    local_xml = f"dblp-{latest_date}.xml.gz"
    storage_url = f"{storage_base_url}{artifact_year}/{local_xml}"
    print(storage_url)

    latest_path = os.path.join(corpus_path, f"dblp-{latest_date}")

    if not os.path.exists(latest_path):
        os.makedirs(latest_path)
        os.makedirs(os.path.join(latest_path, 'DL_Object'))

        get_file(storage_url, os.path.join(latest_path, local_xml), headers)

        # Update the LATEST_DATE in .env file
        update_latest_date_in_env(latest_date)
    else:
        logging.info(f"DBLP corpus with release date {latest_date} already exists, skipping...")
