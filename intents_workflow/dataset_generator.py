"""
Dataset Generator with Citation Intent Support

This script generates citation datasets from TEI XML or JSON files with optional citation intent enrichment.
All paths are configured via .env file (see .env.example for configuration template).

Modes:
    1. intents: Full workflow (TEI XML → S2ORC JSON → JSONL with intents → MongoDB)
       - Requires: TEI_PATH in .env
       - Optional: JSON_PATH, S2ORC_JSONL_PATH (default to TEI_PATH parent directory)
       - Processes TEI XML files from TEI_PATH directory
       - Generates outputs in:
         * JSON_PATH: S2ORC JSON files
         * S2ORC_JSONL_PATH/base/: Citation JSONL files
         * S2ORC_JSONL_PATH/intents/: Citation JSONL with intent predictions
       - Stores in MongoDB with citation contexts
    
    2. references: References-only (JSON files → MongoDB, original dataset_generator behavior)
       - Requires: JSON_PATH in .env
       - Processes existing JSON files from JSON_PATH
       - Extracts bibliography entries only
       - No citation intent enrichment
       - Independent from citation work

Configuration:
    Create .env file based on .env.example with:
    - MongoDB: MONGO_IP, MONGO_DB, PAPERS_COL
    - Paths: TEI_PATH (for intents), JSON_PATH, S2ORC_JSONL_PATH (optional), LOGS_PATH (optional)
    - See .env.example for full configuration details

Usage:
    python dataset_generator.py --mode intents
    python dataset_generator.py --mode references
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Import project modules
from doc2json.grobid2json.tei_to_json import convert_tei_xml_file_to_s2orc_json
from doc2json.grobid2json.s2orc_converter import metadata_strip, generate_s2orc_jsonl, enrich_citations_with_intent
from doc2json.grobid2json.citation_intent_api import MockCitationIntentAPI, ExternalCitationIntentAPI
from doc2json.utils.env_util import get_keys
from doc2json.utils.mongo_util import connect_to_mongo_collection
from doc2json.utils.dblp_lookup_util import (
    lookup_paper_by_doi,
    lookup_paper_by_title,
    lookup_paper_by_filename
)
from doc2json.utils.stats_util import (
    create_stats_collection,
    update_cumulative_statistics,
    validate_statistics,
    print_final_statistics
)
from doc2json.utils.dataset_util import (
    ensure_dataset_indexes,
    insert_or_update_dataset_entry
)


def setup_logging(mode: str):
    """
    Setup logging configuration.
    
    Args:
        mode: Mode of operation ('intents' or 'references')
    """
    # Get logs path from environment, default to 'logs' in current directory
    logs_path = get_keys().get('logs_path')
    if not logs_path:
        logs_path = 'logs'
        logging.warning(f"LOGS_PATH not set in .env, using default: {logs_path}")
    
    log_dir = logs_path
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'dataset_generator_{mode}_{timestamp}.log')
    
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
        force=True
    )
    
    logging.info("=" * 80)
    logging.info(f"Dataset Generator - Mode: {mode.upper()}")
    logging.info(f"Log file: {log_file}")
    logging.info("=" * 80)


def generate_citation_id(citing_paper_id: str, cited_paper_id: str, citation_index: int) -> str:
    """
    Generate a citation ID using improved notation for easy parsing.
    
    Format: "citingPaperId>citedPaperId_CIT{index}"
    Example: "conf_acl_alta_BreenBB12>conf_coling_BilacT04_CIT0"
    
    This format allows easy parsing:
    - Split on '>' to get citing and cited paper IDs
    - Split on '_CIT' to separate IDs from citation index
    
    Args:
        citing_paper_id: DBLP ID of citing paper (e.g., "conf/acl-alta/BorschingerJ11")
        cited_paper_id: DBLP ID or DOI of cited paper (e.g., "conf/acl/Johnson07")
        citation_index: Index of this citation instance (0-based)
    
    Returns:
        Citation ID string
    """
    # Convert DBLP slash format to underscore format
    citing_id_clean = citing_paper_id.replace('/', '_').replace('-', '_')
    cited_id_clean = cited_paper_id.replace('/', '_').replace('-', '_').replace('.', '_')
    
    return f"{citing_id_clean}>{cited_id_clean}_CIT{citation_index}"


def reset_papers_collection(papers_collection):
    """
    Resets the `reference_file_parsed` field in the MongoDB collection.
    
    Args:
        papers_collection: MongoDB collection object for papers
    """
    result = papers_collection.update_many(
        {"reference_file_parsed": True},
        {"$set": {"reference_file_parsed": False}},
        collation={'locale': 'en', 'strength': 2}
    )
    logging.info(f"Reset {result.modified_count} papers' reference_file_parsed status")


def parse_s2orc_bib_entry(ref_id: str, bib_entry: dict, citing_dblp_id: Optional[str] = None, 
                          citation_contexts: Optional[Dict] = None):
    """
    Parses an S2ORC bibliographic entry and extracts relevant information.
    
    This function works with S2ORC JSON format (not TEI XML).
    The bib_entry has already been enriched with DBLP IDs during TEI→S2ORC conversion.
    
    Args:
        ref_id: Reference ID (e.g., "BIBREF0")
        bib_entry: S2ORC bibliography entry dict with title, dblp_id, other_ids, etc.
        citing_dblp_id: DBLP ID of the citing paper (for context lookup)
        citation_contexts: Dictionary with citation contexts
    
    Returns:
        Tuple containing (bib_entry_dict, refs_checked, refs_skipped, dois_matched, 
                         dois_dblp, dblp_keys_matched, citations)
    """
    refs_checked = 0
    refs_skipped = 0
    dois_matched = 0
    dois_dblp = 0
    dblp_keys_matched = 0
    citations = 0
    
    bib_entry_dict = {}
    
    refs_checked += 1
    logging.debug('')
    
    # Extract data from S2ORC format
    pub_title = bib_entry.get('title', '')
    pub_dblp_key = bib_entry.get('dblp_id')
    raw_reference = bib_entry.get('raw_text', '')
    
    # Extract DOI from other_ids
    pub_doi = None
    other_ids = bib_entry.get('other_ids', {})
    if 'DOI' in other_ids and other_ids['DOI']:
        pub_doi = other_ids['DOI'][0] if isinstance(other_ids['DOI'], list) else other_ids['DOI']
    
    # Statistics tracking
    if pub_dblp_key:
        dblp_keys_matched += 1
        if pub_doi:
            dois_matched += 1
            dois_dblp += 1  # Count papers with both DBLP ID and DOI
        logging.debug(f"DBLP KEY: {pub_dblp_key}")
    elif pub_doi:
        dois_matched += 1
        logging.debug(f"DOI only (no DBLP ID) for ref {ref_id}: {pub_title}")
    else:
        refs_skipped += 1
        logging.debug(f"No DBLP ID or DOI for ref {ref_id}: {pub_title}")
    
    # Build bibliography entry dictionary
    if pub_dblp_key:
        bib_entry_dict = {
            "dblp_id": pub_dblp_key,
            "bibliographic_reference": raw_reference
        }
        if pub_doi:
            bib_entry_dict["doi"] = pub_doi
        citations = 1  # Successfully created entry with identifier
    elif pub_doi:
        # Have DOI but no DBLP ID
        bib_entry_dict = {
            "doi": pub_doi,
            "bibliographic_reference": raw_reference
        }
        citations = 1  # Successfully created entry with identifier
    
    # Add citation contexts if available (only in intents mode)
    if bib_entry_dict and citation_contexts and citing_dblp_id:
        if citing_dblp_id in citation_contexts:
            # Try to match by DBLP ID first, then by DOI
            cited_id = bib_entry_dict.get('dblp_id') or bib_entry_dict.get('doi')
            if cited_id and cited_id in citation_contexts[citing_dblp_id]:
                bib_entry_dict['citation_contexts'] = citation_contexts[citing_dblp_id][cited_id]
                logging.debug(f"✓ Added {len(bib_entry_dict['citation_contexts'])} citation contexts for {cited_id}")
            else:
                logging.debug(f"No contexts found for cited paper: {cited_id}")
        else:
            logging.debug(f"No contexts found for citing paper: {citing_dblp_id}")
    
    return bib_entry_dict, refs_checked, refs_skipped, dois_matched, dois_dblp, dblp_keys_matched, citations


def get_s2orc_bib_entries(json_dict: dict, citing_dblp_id: Optional[str] = None,
                          citation_contexts: Optional[Dict] = None):
    """
    Retrieves bibliography entries from S2ORC JSON format.
    
    This function works with S2ORC JSON format where bibliography entries
    are stored in pdf_parse/bib_entries as a dictionary (not TEI XML biblStruct).
    
    Args:
        json_dict: S2ORC JSON dictionary with pdf_parse/bib_entries
        citing_dblp_id: DBLP ID of citing paper
        citation_contexts: Dictionary with citation contexts
    
    Returns:
        Tuple containing (bib_entries, refs_checked, refs_skipped, dois_matched, 
                         dois_dblp, dblp_keys_matched, citations)
    """
    bib_refs_checked = 0
    bib_refs_skipped = 0
    bib_dois_matched = 0
    bib_dois_dblp = 0
    bib_dblp_keys_matched = 0
    bib_citations = 0
    
    bib_entries = []
    
    # S2ORC format: pdf_parse -> bib_entries (dictionary keyed by ref_id)
    if 'pdf_parse' not in json_dict or 'bib_entries' not in json_dict['pdf_parse']:
        logging.warning("No bibliography entries found in S2ORC JSON")
        return bib_entries, bib_refs_checked, bib_refs_skipped, bib_dois_matched, bib_dois_dblp, bib_dblp_keys_matched, bib_citations
    
    bib_entries_dict = json_dict['pdf_parse']['bib_entries']
    
    # Iterate over all bibliography entries
    for ref_id, bib_entry in bib_entries_dict.items():
        bib_entry_dict, refs_checked, refs_skipped, dois_matched, dois_dblp, dblp_keys_matched, citations = \
            parse_s2orc_bib_entry(ref_id, bib_entry, citing_dblp_id, citation_contexts)
        
        bib_refs_checked += refs_checked
        bib_refs_skipped += refs_skipped
        bib_dois_matched += dois_matched
        bib_dois_dblp += dois_dblp
        bib_dblp_keys_matched += dblp_keys_matched
        bib_citations += citations
        
        if len(bib_entry_dict) != 0:
            bib_entries.append(bib_entry_dict)
    
    return bib_entries, bib_refs_checked, bib_refs_skipped, bib_dois_matched, bib_dois_dblp, bib_dblp_keys_matched, bib_citations


def load_citation_contexts_from_jsonl(jsonl_dir: str) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Load citation contexts with intents, organized by citing paper → cited paper.
    
    Args:
        jsonl_dir: Directory containing JSONL files with citation intents
    
    Returns:
        Dictionary structure:
        {
            "citing_paper_dblp_id": {
                "cited_paper_dblp_id": [
                    {
                        "citation_id": "conf_acl_Smith20_conf_acl_Johnson07_CIT0",
                        "section": "...",
                        "text": "...",
                        "cite_start": ...,
                        "cite_end": ...,
                        "intent": "..."
                    },
                    ...
                ]
            }
        }
    """
    contexts = {}
    total_citations = 0
    
    logging.info(f"Loading citation contexts from: {jsonl_dir}")
    
    if not os.path.exists(jsonl_dir):
        logging.warning(f"Citation contexts directory does not exist: {jsonl_dir}")
        return contexts
    
    for file in os.scandir(jsonl_dir):
        if file.is_file() and file.name.endswith('_i.jsonl'):
            with open(file.path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        citation = json.loads(line.strip())
                        
                        citing_id = citation['citingPaperId']
                        cited_id = citation['citedPaperId']
                        
                        # Initialize nested dict structure
                        if citing_id not in contexts:
                            contexts[citing_id] = {}
                        if cited_id not in contexts[citing_id]:
                            contexts[citing_id][cited_id] = []
                        
                        # Generate citation ID for this citation instance
                        citation_index = len(contexts[citing_id][cited_id])
                        citation_id = generate_citation_id(citing_id, cited_id, citation_index)
                        
                        # Add citation context with citation ID
                        contexts[citing_id][cited_id].append({
                            'citation_id': citation_id,
                            'section': citation.get('sectionName', 'Unknown'),
                            'text': citation['string'],
                            'cite_start': citation['citeStart'],
                            'cite_end': citation['citeEnd'],
                            'intent': citation.get('citationIntent', 'Unknown')
                        })
                        
                        total_citations += 1
                    except (json.JSONDecodeError, KeyError) as e:
                        logging.warning(f"Error parsing line in {file.name}: {e}")
                        continue
    
    logging.info(f"Loaded {total_citations} citation contexts for {len(contexts)} citing papers")
    
    return contexts


def process_tei_to_s2orc_with_intents(tei_file: str, output_json_dir: str, 
                                       output_jsonl_dir: str, output_jsonl_intent_dir: str,
                                       papers_collection, intent_api) -> Optional[str]:
    """
    Process a single TEI XML file to S2ORC JSON with citation intents.
    
    Args:
        tei_file: Path to TEI XML file
        output_json_dir: Directory for output JSON files
        output_jsonl_dir: Directory for output JSONL files (without intent)
        output_jsonl_intent_dir: Directory for output JSONL files (with intent)
        papers_collection: MongoDB collection for DBLP lookup
        intent_api: Citation intent API instance
    
    Returns:
        DBLP ID of the paper if successful, None otherwise
    """
    try:
        filename = os.path.basename(tei_file)
        paper_id = filename.replace('.tei.xml', '')
        
        logging.info(f"Processing: {filename}")
        
        # Convert TEI XML to S2ORC JSON
        paper = convert_tei_xml_file_to_s2orc_json(
            tei_file, 
            paper_id,
        )
        
        if paper is None:
            logging.warning(f"Failed to convert {filename}")
            return None
        
        # Strip metadata
        paper_dict = metadata_strip(paper)
        
        # Save stripped JSON
        json_output_file = os.path.join(output_json_dir, f"{paper_id}.json")
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(paper_dict, f, indent=2, ensure_ascii=False)
        
        # Generate citation JSONL
        generate_s2orc_jsonl(paper_dict, output_jsonl_dir, paper_id)
        
        # Enrich with citation intents
        jsonl_file = os.path.join(output_jsonl_dir, f"{paper_id}.jsonl")
        output_with_intent = os.path.join(output_jsonl_intent_dir, f"{paper_id}_i.jsonl")
        
        if os.path.exists(jsonl_file):
            enrich_citations_with_intent(
                jsonl_file,
                intent_api,
                output_file=output_with_intent
            )
        
        logging.info(f"✓ Processed {filename} → {paper_id}.json")
        
        return paper_id
        
    except Exception as e:
        logging.error(f"Error processing {tei_file}: {e}")
        return None


def iterate_json_reference_files(papers_collection, dataset_collection, stats_collection,
                                  json_path: str, citation_contexts: Optional[Dict], stats: dict,
                                  skip_existing: bool = False):
    """
    Iterates through JSON reference files, processes bibliography data, and updates MongoDB.
    
    This function is used in both modes:
    - In 'intents' mode: citation_contexts contains intent-enriched citation data
    - In 'references' mode: citation_contexts is None (bibliography only, like original workflow)
    
    Args:
        papers_collection: MongoDB collection object for papers
        dataset_collection: MongoDB collection object for the dataset
        stats_collection: MongoDB collection object for statistics
        json_path: Path to the directory containing JSON reference files
        citation_contexts: Dictionary with citation contexts (intents mode) or None (references mode)
        stats: Dictionary containing statistics counters
        skip_existing: If True, skip papers already in dataset (faster). If False, update them.
    
    Returns:
        Updated statistics dictionary
    """
    # Capture initial stats at the start of this run
    import copy
    initial_stats = copy.deepcopy(stats)
    
    files_processed = 0
    files_skipped_already_in_dataset = 0
    total_files = len([f for f in os.scandir(json_path) if f.is_file() and f.name.endswith('.json')])
    logging.info(f"Found {total_files} JSON files to process")
    
    for fl in os.scandir(json_path):
        try:
            if fl.is_file() and fl.name.endswith('.json'):
                bib_entries = []
                
                dblp_id, file_checked, dblp_url = lookup_paper_by_filename(papers_collection, fl.name)
                
                if dblp_id is not None:
                    # Early check: if skip_existing and paper already in dataset, skip entirely
                    if skip_existing:
                        existing_entry = dataset_collection.find_one({"citing_paper.dblp_id": dblp_id})
                        if existing_entry:
                            files_skipped_already_in_dataset += 1
                            if files_skipped_already_in_dataset <= 5:  # Log first 5
                                logging.info(f"⏭️  Skipping {fl.name} - already in dataset (DBLP ID: {dblp_id})")
                            elif files_skipped_already_in_dataset % 100 == 0:  # Then every 100th
                                logging.info(f"⏭️  Skipped {files_skipped_already_in_dataset} papers already in dataset...")
                            continue
                    
                    if file_checked is False:
                        files_processed += 1
                        logging.info(f"[{files_processed}/{total_files}] Processing {fl.name} (DBLP ID: {dblp_id})")
                        
                        with open(fl, "r", encoding="utf-8") as json_file:
                            json_dict = json.load(json_file)
                            
                            # Use paper_id from JSON file (e.g., "conf_aaai_0001GM20") 
                            # to match citation contexts indexed by citingPaperId in JSONL files
                            citing_paper_id = json_dict.get("paper_id", dblp_id)
                            logging.debug(f"Citing paper_id: {citing_paper_id} (DBLP ID: {dblp_id})")
                            
                            # Get bibliography (with or without citation contexts)
                            bib_entries, bib_refs_checked, bib_refs_skipped, \
                            bib_dois_matched, bib_dois_dblp, bib_dblp_keys_matched, bib_citations = \
                                get_s2orc_bib_entries(
                                    json_dict,
                                    citing_dblp_id=citing_paper_id,  # Use paper_id from JSON
                                    citation_contexts=citation_contexts  # None in references mode
                                )
                        
                        # Build citing paper entry
                        if dblp_url is not None:
                            dblp_doi_list = [item for item in dblp_url if 'doi' in item]
                            if len(dblp_doi_list) != 0:
                                dblp_doi = dblp_doi_list[0].split('org/')[-1]
                                dblp_entry_dict = {
                                    "citing_paper": {
                                        "dblp_id": dblp_id,
                                        "doi": dblp_doi
                                    },
                                    "cited_papers": bib_entries
                                }
                            else:
                                dblp_entry_dict = {
                                    "citing_paper": {
                                        "dblp_id": dblp_id,
                                    },
                                    "cited_papers": bib_entries
                                }
                        else:
                            dblp_entry_dict = {
                                "citing_paper": {
                                    "dblp_id": dblp_id,
                                },
                                "cited_papers": bib_entries
                            }
                        
                        # Update CUMULATIVE statistics (total_* fields keep growing)
                        stats['last_run_papers_checked'] += 1
                        stats['total_refs_checked'] += bib_refs_checked
                        stats['total_refs_skipped'] += bib_refs_skipped
                        stats['total_dois_matched'] += bib_dois_matched
                        stats['total_dois_dblp'] += bib_dois_dblp
                        stats['total_dblp_keys_matched'] += bib_dblp_keys_matched
                        stats['total_citations'] += bib_citations
                        
                        # Count citation contexts (only if available in intents mode)
                        if citation_contexts is not None:
                            for bib_entry in bib_entries:
                                if 'citation_contexts' in bib_entry:
                                    stats['total_papers_with_contexts'] += 1
                                    stats['total_contexts_added'] += len(bib_entry['citation_contexts'])
                                else:
                                    stats['total_papers_without_contexts'] += 1
                        
                        logging.info(f"  → Refs checked: {bib_refs_checked}, Citations: {bib_citations}, Skipped: {bib_refs_skipped}")
                        logging.info(f"  → DBLP IDs: {bib_dblp_keys_matched}, DOIs: {bib_dois_matched}, Both: {bib_dois_dblp}")
                        
                        if citation_contexts is not None and bib_citations > 0:
                            contexts_count = sum(len(be.get('citation_contexts', [])) for be in bib_entries)
                            papers_with_ctx = sum(1 for be in bib_entries if 'citation_contexts' in be)
                            logging.info(f"  → Citation contexts: {contexts_count} contexts for {papers_with_ctx}/{bib_citations} papers")
                        
                        # Update MongoDB
                        papers_collection.update_one(
                            {"key": dblp_id},
                            {"$set": {"reference_file_parsed": True}},
                            collation={'locale': 'en', 'strength': 2}
                        )
                        
                        # Only insert dataset entry if there are cited papers
                        if len(bib_entries) > 0:
                            action = insert_or_update_dataset_entry(
                                dataset_collection,
                                dblp_entry_dict,
                                stats,
                                skip_existing=skip_existing
                            )
                            if action == 'inserted':
                                stats['total_papers'] += 1  # Increment total papers in dataset
                                logging.info(f"  ✅ Inserted new entry for {dblp_id}")
                            elif action == 'skipped':
                                logging.info(f"  ⏭️  Skipped existing entry for {dblp_id}")
                        else:
                            stats['total_papers_skipped_no_citations'] += 1
                            logging.info(f"  ⚠️  Skipping entry - no cited papers made it through")
                        
        except Exception as e:
            logging.error(f"Error processing {fl.name}: {e}")
            continue
    
    # Update cumulative statistics ONCE after processing all papers
    update_cumulative_statistics(stats_collection, stats, initial_stats)
    
    logging.info("")
    logging.info(f"✓ Processed {stats['last_run_papers_checked']} papers successfully")
    if files_skipped_already_in_dataset > 0:
        logging.info(f"⏭️  Skipped {files_skipped_already_in_dataset} papers already in dataset (early check)")
    logging.info(f"✓ Citations extracted this run: {stats.get('total_citations', 0) - initial_stats.get('total_citations', 0)}")
    logging.info(f"✓ Refs skipped this run: {stats.get('total_refs_skipped', 0) - initial_stats.get('total_refs_skipped', 0)}")
    
    return stats


def run_intents_mode(args):
    """
    Run the full citation intent workflow.
    
    Steps:
        1. Process TEI XML files to S2ORC JSON
        2. Generate citation JSONL files
        3. Enrich citations with intents
        4. Load citation contexts
        5. Process JSON files with contexts
        6. Save to MongoDB
    """
    logging.info("Running in INTENTS mode (full workflow with citation intent enrichment)")
    logging.info("")
    
    # Get paths from environment
    tei_input_path = get_keys()['tei_path']
    json_output_dir = get_keys().get('json_path')
    s2orc_jsonl_base_path = get_keys().get('s2orc_jsonl_path')
    
    if not tei_input_path:
        logging.error("TEI_PATH must be set in environment file (.env)")
        logging.error("Please set TEI_PATH in .env file and try again")
        return
    
    if not os.path.exists(tei_input_path):
        logging.error(f"TEI input path does not exist: {tei_input_path}")
        return
    
    # If JSON_PATH not set, use TEI_PATH parent directory
    if not json_output_dir:
        json_output_dir = os.path.join(os.path.dirname(tei_input_path), 'JSON_OUT')
        logging.warning(f"JSON_PATH not set in .env, using: {json_output_dir}")
    
    # If S2ORC_JSONL_PATH not set, use TEI_PATH parent directory
    if not s2orc_jsonl_base_path:
        s2orc_jsonl_base_path = os.path.join(os.path.dirname(tei_input_path), 'S2ORC_JSONL')
        logging.warning(f"S2ORC_JSONL_PATH not set in .env, using: {s2orc_jsonl_base_path}")
    
    logging.info(f"TEI input path: {tei_input_path}")
    logging.info(f"JSON output path: {json_output_dir}")
    logging.info(f"S2ORC JSONL base path: {s2orc_jsonl_base_path}")
    
    # Create output directories with subdirectories for base and intents
    jsonl_base_dir = os.path.join(s2orc_jsonl_base_path, 'base')
    jsonl_intents_dir = os.path.join(s2orc_jsonl_base_path, 'intents')
    
    os.makedirs(json_output_dir, exist_ok=True)
    os.makedirs(jsonl_base_dir, exist_ok=True)
    os.makedirs(jsonl_intents_dir, exist_ok=True)
    
    logging.info(f"  → JSON files: {json_output_dir}")
    logging.info(f"  → S2ORC JSONL (base): {jsonl_base_dir}")
    logging.info(f"  → S2ORC JSONL (intents): {jsonl_intents_dir}")
    
    # Connect to MongoDB
    papers_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['papers_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys().get('mongo_user'),
        password=get_keys().get('mongo_pass'),
        auth=bool(get_keys().get('mongo_user'))
    )
    
    dataset_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=f"{get_keys()['dblp_dataset']}_{get_keys()['mode']}_{get_keys()['latest_date']}",
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass'],
        auth=bool(get_keys().get('mongo_user'))
    )
    
    # Handle fresh start if requested
    if args.fresh_start:
        logging.warning("🔄 FRESH START mode enabled - clearing dataset and statistics!")
        dataset_collection.delete_many({})
        logging.info(f"  ✓ Cleared dataset collection")
    
    # Ensure indexes exist for optimal performance
    ensure_dataset_indexes(dataset_collection)
    
    stats_collection = create_stats_collection(fresh_start=args.fresh_start)
    stats = stats_collection.find_one({"key": "statistics"})
    
    # Initialize citation intent API
    logging.info("Initializing Citation Intent API...")
    citation_api_url = get_keys().get('citation_api_url')
    
    if citation_api_url:
        logging.info(f"Using external Citation Intent API: {citation_api_url}")
        intent_api = ExternalCitationIntentAPI(api_url=citation_api_url)
    else:
        logging.warning("CITATION_API_URL not set in .env, using mock implementation")
        intent_api = MockCitationIntentAPI()
    
    # Step 1: Process TEI XML files
    logging.info("=" * 80)
    logging.info("STEP 1: Processing TEI XML files to S2ORC JSON with citation intents")
    logging.info("=" * 80)
    
    tei_files = list(Path(tei_input_path).glob('*.tei.xml'))
    logging.info(f"Found {len(tei_files)} TEI XML files")
    
    processed_papers = []
    for i, tei_file in enumerate(tei_files, 1):
        logging.info(f"\n[{i}/{len(tei_files)}] Processing {tei_file.name}...")
        paper_id = process_tei_to_s2orc_with_intents(
            str(tei_file),
            json_output_dir,
            jsonl_base_dir,
            jsonl_intents_dir,
            papers_collection,
            intent_api
        )
        if paper_id:
            processed_papers.append(paper_id)
    
    logging.info(f"\n✓ Processed {len(processed_papers)}/{len(tei_files)} TEI files successfully")
    
    # Step 2: Load citation contexts
    logging.info("")
    logging.info("=" * 80)
    logging.info("STEP 2: Loading citation contexts from JSONL files")
    logging.info("=" * 80)
    
    citation_contexts = load_citation_contexts_from_jsonl(jsonl_intents_dir)
    
    # Step 3: Process JSON files with citation contexts
    logging.info("")
    logging.info("=" * 80)
    logging.info("STEP 3: Processing JSON reference files with citation contexts")
    logging.info("=" * 80)
    
    reset_papers_collection(papers_collection)
    
    # Log deduplication strategy
    if args.skip_existing:
        logging.info("📋 Skip-existing mode: Will skip papers already in dataset (faster)")
    else:
        logging.info("🔄 Update mode: Will update existing papers with new data (default)")
    
    stats = iterate_json_reference_files(
        papers_collection,
        dataset_collection,
        stats_collection,
        json_output_dir,
        citation_contexts,
        stats,
        skip_existing=args.skip_existing
    )
    
    # Print final statistics
    print_final_statistics(stats, mode='intents')


def run_references_mode(args):
    """
    Run the references-only workflow (original dataset_generator behavior).
    
    This mode processes existing JSON files to extract bibliography entries only,
    without any citation intent enrichment. This is the original workflow behavior.
    
    Steps:
        1. Load existing JSON files
        2. Process bibliography entries
        3. Save to MongoDB (no citation contexts)
    """
    logging.info("Running in REFERENCES mode (bibliography only, no citation intents)")
    logging.info("")
    
    # Get JSON path from environment
    json_path = get_keys()['json_path']
    if not json_path:
        logging.error("JSON_PATH not set in environment file (.env)")
        logging.error("Please set JSON_PATH in .env file and try again")
        return
    
    if not os.path.exists(json_path):
        logging.error(f"JSON path does not exist: {json_path}")
        return
    
    logging.info(f"JSON input path: {json_path}")
    
    # Connect to MongoDB
    papers_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=get_keys()['papers_coll'],
        ip=get_keys()['mongo_ip'],
        username=get_keys().get('mongo_user'),
        password=get_keys().get('mongo_pass'),
        auth=bool(get_keys().get('mongo_user'))
    )
    
    dataset_collection = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=f"{get_keys()['dblp_dataset']}_{get_keys()['latest_date']}",
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass'],
        auth=bool(get_keys().get('mongo_user'))
    )
    
    # Handle fresh start if requested
    if args.fresh_start:
        logging.warning("🔄 FRESH START mode enabled - clearing dataset and statistics!")
        dataset_collection.delete_many({})
        logging.info(f"  ✓ Cleared dataset collection")
    
    # Ensure indexes exist for optimal performance
    ensure_dataset_indexes(dataset_collection)
    
    stats_collection = create_stats_collection(fresh_start=args.fresh_start)
    stats = stats_collection.find_one({"key": "statistics"})
    
    # Process JSON files (no citation contexts - bibliography only)
    logging.info("=" * 80)
    logging.info("Processing JSON reference files (bibliography only)")
    logging.info("=" * 80)
    
    reset_papers_collection(papers_collection)
    
    # Log deduplication strategy
    if args.skip_existing:
        logging.info("📋 Skip-existing mode: Will skip papers already in dataset (faster)")
    else:
        logging.info("🔄 Update mode: Will update existing papers with new data (default)")
    
    # Pass None for citation_contexts to get pure bibliography extraction
    stats = iterate_json_reference_files(
        papers_collection,
        dataset_collection,
        stats_collection,
        json_path,
        citation_contexts=None,  # No contexts in references mode
        stats=stats,
        skip_existing=args.skip_existing
    )
    
    # Print final statistics
    print_final_statistics(stats, mode='references')


def main():
    """Main entry point for the dataset generator."""
    parser = argparse.ArgumentParser(
        description='Generate citation datasets with optional intent enrichment.\n'
                    'All paths are configured via .env file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration:
  All paths must be configured in .env file before running:
  - TEI_PATH: Directory containing TEI XML files (for intents mode)
  - JSON_PATH: Directory for S2ORC JSON files (read by references, written by intents)
  - S2ORC_JSONL_PATH: Base directory for JSONL files (optional, defaults to TEI_PATH parent)
  - MONGO_IP, MONGO_DB, PAPERS_COL: MongoDB configuration
  
  Directory structure (intents mode):
    JSON_PATH/              - S2ORC JSON files
    S2ORC_JSONL_PATH/
      ├── base/             - Citation JSONL files
      └── intents/          - Citation JSONL with intent predictions
  
  See .env.example for full configuration details.

Duplicate Handling:
  By default, the script intelligently handles duplicates:
  - Existing papers in the dataset are UPDATED with new data
  - Statistics accumulate across multiple runs
  - Use --skip-existing for faster processing (skips updates)
  - Use --fresh-start to clear everything and start over

Examples:
  # Full workflow with citation intents (default: update existing)
  python dataset_generator.py --mode intents

  # References only (uses existing JSON files)
  python dataset_generator.py --mode references
  
  # Skip existing papers for faster processing
  python dataset_generator.py --mode intents --skip-existing
  
  # Start fresh (clear dataset and statistics)
  python dataset_generator.py --mode intents --fresh-start
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['intents', 'references'],
        help='Mode of operation: "intents" for full workflow with citation intent enrichment, '
             '"references" for bibliography-only extraction (original workflow)'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip papers that already exist in the dataset (faster, no updates). '
             'Default: False (updates existing papers with new data)'
    )
    
    parser.add_argument(
        '--fresh-start',
        action='store_true',
        help='Clear dataset and statistics collections before starting. '
             'Default: False (accumulates data across multiple runs)'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Verify required environment variables
    required_vars = ['MONGO_IP', 'MONGO_DB', 'PAPERS_COL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please configure your .env file based on .env.example")
        sys.exit(1)
    
    # Mode-specific validation
    if args.mode == 'intents':
        if not os.getenv('TEI_PATH'):
            print("Error: Intents mode requires TEI_PATH to be set in .env file")
            print("Optional: Set JSON_PATH and S2ORC_JSONL_PATH (default to TEI_PATH parent directory)")
            sys.exit(1)
    elif args.mode == 'references':
        if not os.getenv('JSON_PATH'):
            print("Error: References mode requires JSON_PATH to be set in .env file")
            sys.exit(1)
    
    # Setup logging
    setup_logging(args.mode)
    
    # Run appropriate mode
    try:
        if args.mode == 'intents':
            run_intents_mode(args)
        else:
            run_references_mode(args)
        
        logging.info("")
        logging.info("✓ Dataset generation completed successfully!")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        logging.exception("Stack trace:")
        sys.exit(1)


if __name__ == "__main__":
    main()
