import ctypes
from utils.helper_utils import *
libgcc_s = ctypes.CDLL('libgcc_s.so.1')
from submodules.grobid_client_python.grobid_client.grobid_client import GrobidClient


if __name__ == "__main__":
    load_dotenv()

    config_path = get_keys()['grobid_config_path']
    pdf_path = get_keys()['pdf_path']
    tei_path = os.path.join(get_keys()['tei_path'], get_keys()['mode'])

    service_options = ["processFulltextDocument", "processReferences", "processHeaderDocument"]

    client = GrobidClient(config_path=config_path)
    service = int(sys.argv[1])

    if len(sys.argv) > 2:
        folder_name = sys.argv[2]

    if service == 0:  # processFulltextDocument
        if not os.path.exists(tei_path):
            os.makedirs(tei_path)

        if folder_name:
            tei_path = os.path.join(tei_path, folder_name)
            pdf_path = os.path.join(pdf_path, folder_name)
            if not os.path.exists(tei_path):
                os.makedirs(tei_path)

        client.process(
            service=service_options[0],
            input_path=pdf_path,
            output=tei_path,
            consolidate_citations=True,
            include_raw_citations=True,
            force=False,
            verbose=True,
            n=30)
    elif service == 1:  # processReferences
        if not os.path.exists(tei_path):
            os.makedirs(tei_path)

        if folder_name:
            tei_path = os.path.join(tei_path, folder_name)
            pdf_path = os.path.join(pdf_path, folder_name)
            if not os.path.exists(tei_path):
                os.makedirs(tei_path)

        client.process(
            service=service_options[1],
            input_path=pdf_path,
            output=tei_path,
            consolidate_citations=1,
            include_raw_citations=True,
            force=False,
            verbose=True,
            n=30)
    elif service == 2:  # processHeader
        if not os.path.exists(tei_path):
            os.makedirs(tei_path)

        if folder_name:
            tei_path = os.path.join(tei_path, folder_name)
            pdf_path = os.path.join(pdf_path, folder_name)
            if not os.path.exists(tei_path):
                os.makedirs(tei_path)

        client.process(
            service=service_options[2],
            input_path=pdf_path,
            output=tei_path,
            consolidate_header=1,
            include_raw_affiliations=1,
            force=False,
            verbose=True,
            n=30)
    elif service == 3:  # processFulltextDocument
        if not os.path.exists(tei_path):
            os.makedirs(tei_path)

        if folder_name:
            tei_path = os.path.join(tei_path, folder_name)
            pdf_path = os.path.join(pdf_path, folder_name)
            if not os.path.exists(tei_path):
                os.makedirs(tei_path)

        client.process(
            service=service_options[0],
            input_path=pdf_path,
            output=tei_path,
            consolidate_citations=True,
            force=False,
            verbose=True,
            segment_sentences=True,
            n=30)
