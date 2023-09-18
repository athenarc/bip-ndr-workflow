from submodules.grobid_client_python.grobid_client.grobid_client import GrobidClient
import os
import sys
import ctypes
libgcc_s = ctypes.CDLL('libgcc_s.so.1')
config_path = os.path.join("..", "submodules", "grobid_client_python", "config.json")
pdf_path = os.path.join("..", "data", "PDFs")
tei_path = os.path.join("..", "data", "TEI_XML")

service_options = ["processFulltextDocument", "processReferences", "processHeaderDocument"]

if __name__ == "__main__":
    client = GrobidClient(config_path=config_path)
    service = int(sys.argv[1])

    if len(sys.argv) > 2:
        folder_name = sys.argv[2]

    if service == 0:  # processFulltextDocument
        tei_path = os.path.join(tei_path, "FullText")
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
            n=10)
    elif service == 1:  # processReferences
        tei_path = os.path.join(tei_path, "References")
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
            n=10)
    elif service == 2:  # processHeader
        tei_path = os.path.join(tei_path, "Headers")
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
            n=10)
    elif service == 3:  # processFulltextDocument
        tei_path = os.path.join(tei_path, "FullTextSegmented")
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
            n=10)
