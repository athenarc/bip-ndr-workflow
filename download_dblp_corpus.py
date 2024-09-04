import requests
import re
from utils.helper_utils import *
from bs4 import BeautifulSoup

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(get_keys()["logs_path"], f"{os.path.basename(__file__).replace('.py', '.log')}")),
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
    url = "https://dblp.org/xml/release/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36"
    }

    response = requests.get(url, headers=headers, timeout=4)

    soup = BeautifulSoup(response.text, 'html.parser')
    links = str(soup.find_all('a', href=True))

    latest_xml = re.findall(r'dblp-\d+-\d+-\d+\.xml\.gz', links)[0]
    latest_dtd = re.findall(r'dblp-\d+-\d+-\d+\.dtd', links)[0]

    xml_url = url + latest_xml
    dtd_url = url + latest_dtd

    latest_path = os.path.join(corpus_path, latest_xml.split('.')[0])
    latest_date = re.findall(r'\d+-\d+-\d+', latest_xml)[0]

    if not os.path.exists(latest_path):
        os.makedirs(latest_path)
        os.makedirs(os.path.join(latest_path, 'DL-Object'))

        xml_url = url + latest_xml
        dtd_url = url + latest_dtd

        get_file(xml_url, os.path.join(latest_path, latest_xml), headers)
        get_file(dtd_url, os.path.join(latest_path, latest_dtd), headers)

        # Update the LATEST_DATE in .env file
        update_latest_date_in_env(latest_date)
    else:
        logging.info(f"DBLP corpus with release date {latest_date} already exists, skipping...")
