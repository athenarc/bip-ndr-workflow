import ctypes
import click
from glob2 import glob
from utils.helper_utils import *
libgcc_s = ctypes.CDLL('libgcc_s.so.1')
from submodules.grobid_client_python.grobid_client.grobid_client import GrobidClient

load_dotenv()
logs_path = os.path.join(get_keys()['logs_path'], get_keys()["latest_date"])

logging.basicConfig(
    format='%(asctime)s \t %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(logs_path, f"{os.path.basename(__file__).replace('.py', '.log')}"))
    ]
)


def run_grobid_service(service, pdf_path, tei_path, service_options, client):

    if service == 0:  # processFulltextDocument        
        print(f"running service {service} with input: {pdf_path} and output: {tei_path}")

        client.process(
            service=service_options[0],
            input_path=pdf_path,
            output=tei_path,
            consolidate_citations=True,
            include_raw_citations=True,
            consolidate_header=False,
            force=False,
            verbose=True,
            n=8)
    elif service == 1:  # processReferences
        print(f"running service {service} with input: {pdf_path} and output: {tei_path}")

        client.process(
            service=service_options[1],
            input_path=pdf_path,
            output=tei_path,
            consolidate_citations=1,
            consolidate_header=False,
            include_raw_citations=True,
            force=False,
            verbose=True,
            n=8)
    elif service == 2:  # processHeader
        print(f"running service {service} with input: {pdf_path} and output: {tei_path}")

        client.process(
            service=service_options[2],
            input_path=pdf_path,
            output=tei_path,
            consolidate_header=1,
            include_raw_affiliations=1,
            force=False,
            verbose=True,
            n=8)
    elif service == 3:  # processFulltextDocument
        print(f"running service {service} with input: {pdf_path} and output: {tei_path}")

        client.process(
            service=service_options[0],
            input_path=pdf_path,
            output=tei_path,
            consolidate_header=False,
            consolidate_citations=True,
            include_raw_citations=True,
            force=False,
            segment_sentences=True,
            verbose=True,
            n=8)


@click.command()
@click.argument('service', type=int, required=True)
@click.option('--batch', default=None, help="Batch number to process or 'all' for all batches.")
@click.option('--config', default='', help="Config number for GROBID.")
def get_user_arguments(service, batch, config):
    """
    CLI for processing PDF batches.
    
    \b
    SERVICE: An integer representing the service number.
    --batch: Specify a batch number or 'all' to process all batches.
    """

    pdf_path = get_keys()['pdf_path']
    if config != '':
        config = f".{config}"
    config_path = os.path.join(get_keys()['grobid_config_path'], f"config{config}.json")

    # print(config_path)
    client = GrobidClient(config_path=config_path)

    # Determine which batches to process based on the batch option
    batch_dirs = None
    if batch:
        if batch == 'all':
            batch_dirs = [folder.split('/')[-1] for folder in glob(os.path.join(pdf_path, "DocFiles_*")) if os.path.isdir(folder)]
            logging.info("All batches selected.")
        elif batch.isnumeric():
            batch_dirs = f'DocFiles_{batch}'
            logging.info(f"Batch DocFiles_{batch} selected.")
        else:
            logging.error("Unknown option for flag \"--batch\". Exiting...")
            raise click.BadParameter("Invalid value for --batch. Use a number or 'all'.")
    else:        
        # No --batch option given, we process the entire PDF folder
        logging.info("No specific batch selected, processing entire PDF folder...")

    # Return the service and batch_dirs to __main__
    return service, batch_dirs, client


if __name__ == "__main__":

    # Initializing paths and configurations
    pdf_path = get_keys()['pdf_path']
    tei_path = os.path.join(get_keys()['tei_path'], get_keys()['mode'])

    service_options = ["processFulltextDocument", "processReferences", "processHeaderDocument", "processFulltextDocumentSegmented"]

    # Parse arguments and get the service and batch_dirs from CLI
    service, batch_dirs, client = get_user_arguments(standalone_mode=False)  # Use standalone_mode=False to avoid automatic exit after click
    # print(service, batch_dirs)
    logging.info(f"Using PDF path: {pdf_path}")
    logging.info(f"Using TEI path: {tei_path}")
    logging.info(f"Selected service: {service_options[service]}")
    print(f"Using PDF path: {pdf_path}")
    print(f"Using TEI path: {tei_path}")
    print(f"Selected service: {service_options[service]}")
    
    if not os.path.exists(tei_path):
        os.makedirs(tei_path)

    if batch_dirs is not None:
        if type(batch_dirs) is str:
            tei_path = os.path.join(tei_path, batch_dirs)
            pdf_path = os.path.join(pdf_path, batch_dirs)
            if not os.path.exists(tei_path):
                os.makedirs(tei_path)
            run_grobid_service(service, pdf_path, tei_path, service_options, client)
        elif type(batch_dirs) is list:
            pdf_path = sorted([os.path.join(pdf_path, batch_dir) for batch_dir in batch_dirs])
            tei_path = sorted([os.path.join(tei_path, batch_dir) for batch_dir in batch_dirs])

            for tei_batch_dir, pdf_batch_dir in zip(tei_path, pdf_path):
                if not os.path.exists(tei_batch_dir):
                    os.makedirs(tei_batch_dir)
                run_grobid_service(service, pdf_batch_dir, tei_batch_dir, service_options, client)
    else:
        run_grobid_service(service, pdf_path, tei_path, service_options, client)
