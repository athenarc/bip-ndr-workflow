#!/usr/bin/env python3
import os
import sys
import json
import math
import shutil
import tempfile
import logging
import ctypes
from glob2 import glob
from multiprocessing import Process
import click
from utils.helper_utils import *
from submodules.grobid_client_python.grobid_client.grobid_client import GrobidClient

libgcc_s = ctypes.CDLL('libgcc_s.so.1')

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def list_pdfs(root_dir):
    """Recursively list all .pdf files under root_dir."""
    pattern = os.path.join(root_dir, "**/*.pdf")
    return sorted([p for p in glob(pattern) if os.path.isfile(p)])

def chunk_list(items, parts):
    """Split items into 'parts' chunks as evenly as possible."""
    if parts <= 1:
        return [items]
    k = int(math.ceil(len(items) / float(parts)))
    return [items[i:i+k] for i in range(0, len(items), k)]

def make_temp_input_dir(files):
    """Create a temp directory containing symlinks to given files (fallback to copy)."""
    tmpdir = tempfile.mkdtemp(prefix="grobid_chunk_")
    for f in files:
        dst = os.path.join(tmpdir, os.path.basename(f))
        try:
            os.symlink(os.path.abspath(f), dst)
        except Exception:
            shutil.copy2(f, dst)
    return tmpdir

def write_temp_client_config(base_config_path, server_url):
    """Create a temp client config JSON overriding grobid_server."""
    with open(base_config_path) as f:
        cfg = json.load(f)
    cfg["grobid_server"] = server_url
    tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
    json.dump(cfg, tmp)
    tmp.close()
    return tmp.name

def process_on_server(server_url, files, service_name, out_dir, workers, base_config_path,
                      consolidate_citations=False, include_raw_citations=False,
                      consolidate_header=False, segment_sentences=False):
    """Run the official Python client on one server for a subset of files."""
    if not files:
        return
    tmp_input = make_temp_input_dir(files)
    tmp_cfg = write_temp_client_config(base_config_path, server_url)
    try:
        client = GrobidClient(config_path=tmp_cfg)
        client.process(
            service=service_name,
            input_path=tmp_input,
            output=out_dir,
            consolidate_citations=consolidate_citations,
            include_raw_citations=include_raw_citations,
            consolidate_header=consolidate_header,
            segment_sentences=segment_sentences,
            force=False,
            verbose=True,
            n=workers  
        )
    finally:
        try:
            shutil.rmtree(tmp_input, ignore_errors=True)
        except Exception:
            pass
        try:
            os.unlink(tmp_cfg)
        except Exception:
            pass

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

@click.command()
@click.argument('service', type=int, required=True)
@click.option('--batch', default=None, help="Batch number to process or 'all' for all batches.")
@click.option('--config', default='', help="Config suffix number for GROBID client (uses config{.X}.json).")
@click.option('--workers', default=6, type=int, help="Parallel workers per server (match server concurrency).")
@click.option('--server', 'servers', multiple=True,
              help="GROBID base URL. Repeat to add more (e.g. --server http://localhost:8070 --server http://localhost:8072).")
def main(service, batch, config, workers, servers):
    """
    SERVICE: 0=processFulltextDocument, 1=processReferences, 2=processHeaderDocument, 3=processFulltextDocumentSegmented
    """

    load_dotenv()
    logs_path = os.path.join(get_keys()['logs_path'], get_keys()["latest_date"])
    os.makedirs(logs_path, exist_ok=True)

    logging.basicConfig(
        format='%(asctime)s \t %(message)s',
        level=logging.INFO,
        datefmt='%d-%m-%Y %H:%M:%S',
        handlers=[
            logging.FileHandler(os.path.join(logs_path, f"{os.path.basename(__file__).replace('.py', '.log')}"))
        ]
    )

    pdf_root = get_keys()['pdf_path']
    tei_root = os.path.join(get_keys()['tei_path'], get_keys()['mode'])
    os.makedirs(tei_root, exist_ok=True)

    if config != '':
        config = f".{config}"
    base_config_path = os.path.join(get_keys()['grobid_config_path'], f"config{config}.json")

    if not servers:
        servers = ("http://localhost:8070",)
    servers = [s.strip() for s in servers if s.strip()]
    logging.info(f"Servers: {servers} (workers per server={workers})")

    service_options = ["processFulltextDocument",
                       "processReferences",
                       "processHeaderDocument",
                       "processFulltextDocumentSegmented"]
    service_name = service_options[service]
    logging.info(f"Selected service: {service_name}")

    # Determine input/output subset based on --batch
    pdf_path = pdf_root
    tei_path = tei_root
    if batch:
        if batch == 'all':
            batch_dirs = [folder.split('/')[-1]
                          for folder in glob(os.path.join(pdf_root, "DocFiles_*"))
                          if os.path.isdir(folder)]
            batch_dirs = sorted(batch_dirs)
            logging.info("All batches selected.")
        elif batch.isnumeric():
            batch_dirs = [f'DocFiles_{batch}']
            logging.info(f"Batch DocFiles_{batch} selected.")
        else:
            logging.error('Invalid value for --batch (use a number or "all").')
            raise click.BadParameter("Invalid value for --batch. Use a number or 'all'.")
    else:
        batch_dirs = [None]
        logging.info("No specific batch selected, processing entire PDF folder...")

    # Build the list of PDF files to process
    pdf_files = []
    for b in batch_dirs:
        if b is None:
            root = pdf_path
            out_dir = tei_path
        else:
            root = os.path.join(pdf_path, b)
            out_dir = os.path.join(tei_path, b)
            os.makedirs(out_dir, exist_ok=True)
        files = list_pdfs(root)
        if not files:
            logging.warning(f"No PDFs found under {root}")
        else:
            pdf_files.extend([(files, out_dir)])

    total_files = sum(len(fs) for fs, _ in pdf_files)
    print(f"Total PDFs to process: {total_files}")
    print(f"Output base: {tei_path}")

    consolidate_citations = False
    include_raw_citations = False
    consolidate_header = False
    segment_sentences = False
    if service == 0:  # processFulltextDocument
        consolidate_citations = True
        include_raw_citations = True
    elif service == 1:  # processReferences
        consolidate_citations = True
        include_raw_citations = True
    elif service == 2:  # processHeaderDocument
        consolidate_header = True
        # include_raw_affiliations not exposed in client; header fields included by default
    elif service == 3:  # processFulltextDocumentSegmented
        consolidate_citations = True
        include_raw_citations = True
        segment_sentences = True

    # Fan-out across servers: spawn one process per server and split each batch's files evenly
    procs = []
    for files, out_dir in pdf_files:
        parts = chunk_list(files, len(servers))
        for server_url, part in zip(servers, parts):
            p = Process(
                target=process_on_server,
                args=(server_url, part, service_name, out_dir, workers, base_config_path,
                      consolidate_citations, include_raw_citations,
                      consolidate_header, segment_sentences)
            )
            p.start()
            procs.append(p)

    # Wait for all
    for p in procs:
        p.join()

    print("All processing complete.")
    logging.info("All processing complete.")

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        main(standalone_mode=False)
    except SystemExit as e:
        if e.code not in (0, None):
            raise
