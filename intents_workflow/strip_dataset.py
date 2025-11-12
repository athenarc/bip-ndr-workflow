"""
Dataset Stripper Utility

This utility creates a stripped version of the citation intent dataset for publication,
removing citation snippets and position information due to legal/copyright concerns.

The stripped version replaces citation contexts with citation IDs (using S2ORC notation),
preserving only the structural information and intent labels needed for citation graph analysis.

WARNING: This is a ONE-WAY transformation. Always maintain the full dataset privately
         for experiments and validation. The stripped version has limited research value
         but may be required for legal compliance in public releases.

Input:  Full MongoDB dataset with citation contexts
Output: Stripped MongoDB collection with citation IDs and intents only

Usage:
    python strip_dataset.py --source-collection dataset --target-collection dataset_stripped
    python strip_dataset.py --source-collection dataset --target-collection dataset_stripped --dry-run
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List

from doc2json.utils.env_util import get_keys
from doc2json.utils.mongo_util import connect_to_mongo_collection


def setup_logging():
    """Setup logging configuration."""
    logs_path = get_keys().get('logs_path', 'logs')
    log_dir = logs_path
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'strip_dataset_{timestamp}.log')
    
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
    logging.info("Dataset Stripper Utility")
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


def strip_citation_contexts(citation_contexts: List[Dict], citing_paper_id: str, 
                            cited_paper_id: str) -> List[Dict]:
    """
    Strip citation contexts, replacing text/positions with citation IDs.
    
    Args:
        citation_contexts: List of citation context dictionaries with text, positions, and intent
        citing_paper_id: DBLP ID of citing paper
        cited_paper_id: DBLP ID or DOI of cited paper
    
    Returns:
        List of stripped citation dictionaries with citation IDs and intents only
    """
    stripped = []
    
    for idx, context in enumerate(citation_contexts):
        # Use existing citation_id if present, otherwise generate one
        # (Full datasets created with updated workflow will have citation_id)
        citation_id = context.get('citation_id')
        if not citation_id:
            citation_id = generate_citation_id(citing_paper_id, cited_paper_id, idx)
        
        stripped.append({
            'citation_id': citation_id,
            'section': context.get('section', 'Unknown'),
            'intent': context.get('intent', 'Unknown')
        })
    
    return stripped


def strip_dataset_entry(entry: Dict) -> Dict:
    """
    Strip a single dataset entry, removing citation text and positions.
    
    Args:
        entry: Full dataset entry from MongoDB
    
    Returns:
        Stripped dataset entry
    """
    citing_paper = entry.get('citing_paper', {})
    citing_paper_id = citing_paper.get('dblp_id', 'unknown')
    
    stripped_entry = {
        'citing_paper': citing_paper.copy()  # Keep citing paper metadata as-is
    }
    
    # Process each cited paper
    cited_papers = entry.get('cited_papers', [])
    stripped_cited_papers = []
    
    for cited_paper in cited_papers:
        stripped_cited = cited_paper.copy()
        
        # Get cited paper ID (prefer dblp_id, fallback to doi)
        cited_paper_id = cited_paper.get('dblp_id') or cited_paper.get('doi', 'unknown')
        
        # Strip citation contexts if they exist
        if 'citation_contexts' in cited_paper:
            citation_contexts = cited_paper['citation_contexts']
            stripped_cited['citations'] = strip_citation_contexts(
                citation_contexts, 
                citing_paper_id, 
                cited_paper_id
            )
            
            # Remove the original citation_contexts field
            del stripped_cited['citation_contexts']
        
        stripped_cited_papers.append(stripped_cited)
    
    stripped_entry['cited_papers'] = stripped_cited_papers
    
    return stripped_entry


def strip_dataset(source_collection, target_collection, dry_run: bool = False):
    """
    Strip the entire dataset from source collection to target collection.
    
    Args:
        source_collection: MongoDB collection with full dataset
        target_collection: MongoDB collection for stripped dataset
        dry_run: If True, don't write to target collection (just show statistics)
    
    Returns:
        Statistics dictionary
    """
    stats = {
        'total_papers': 0,
        'papers_with_contexts': 0,
        'papers_without_contexts': 0,
        'total_cited_papers': 0,
        'cited_papers_with_contexts': 0,
        'cited_papers_without_contexts': 0,
        'total_citations': 0,
        'citations_stripped': 0
    }
    
    logging.info("Starting dataset stripping process...")
    logging.info(f"Source collection: {source_collection.name}")
    logging.info(f"Target collection: {target_collection.name}")
    logging.info(f"Dry run mode: {dry_run}")
    logging.info("")
    
    # Get total count
    total_entries = source_collection.count_documents({})
    logging.info(f"Found {total_entries} entries to process")
    logging.info("")
    
    if not dry_run:
        # Clear target collection
        target_collection.delete_many({})
        logging.info("Cleared target collection")
        logging.info("")
    
    processed = 0
    
    # Process each entry
    for entry in source_collection.find():
        processed += 1
        stats['total_papers'] += 1
        
        # Check if this paper has citation contexts
        has_contexts = any('citation_contexts' in cited for cited in entry.get('cited_papers', []))
        
        if has_contexts:
            stats['papers_with_contexts'] += 1
        else:
            stats['papers_without_contexts'] += 1
        
        # Process cited papers
        for cited_paper in entry.get('cited_papers', []):
            stats['total_cited_papers'] += 1
            
            if 'citation_contexts' in cited_paper:
                stats['cited_papers_with_contexts'] += 1
                num_contexts = len(cited_paper['citation_contexts'])
                stats['total_citations'] += num_contexts
                stats['citations_stripped'] += num_contexts
            else:
                stats['cited_papers_without_contexts'] += 1
        
        # Strip the entry
        stripped_entry = strip_dataset_entry(entry)
        
        # Insert into target collection (unless dry run)
        if not dry_run:
            # Remove _id to let MongoDB generate a new one
            if '_id' in stripped_entry:
                del stripped_entry['_id']
            target_collection.insert_one(stripped_entry)
        
        # Progress logging
        if processed % 100 == 0:
            logging.info(f"Processed {processed}/{total_entries} entries...")
    
    logging.info("")
    logging.info("=" * 80)
    logging.info("STRIPPING COMPLETE")
    logging.info("=" * 80)
    logging.info("")
    logging.info("Statistics:")
    logging.info(f"  Total citing papers: {stats['total_papers']}")
    logging.info(f"    - With citation contexts: {stats['papers_with_contexts']}")
    logging.info(f"    - Without citation contexts: {stats['papers_without_contexts']}")
    logging.info("")
    logging.info(f"  Total cited papers: {stats['total_cited_papers']}")
    logging.info(f"    - With citation contexts: {stats['cited_papers_with_contexts']}")
    logging.info(f"    - Without citation contexts: {stats['cited_papers_without_contexts']}")
    logging.info("")
    logging.info(f"  Total citations stripped: {stats['citations_stripped']}")
    logging.info("")
    
    if dry_run:
        logging.info("DRY RUN - No changes made to database")
    else:
        logging.info(f"✓ Stripped dataset saved to collection: {target_collection.name}")
    
    logging.info("=" * 80)
    
    return stats


def show_example_comparison(source_collection, target_collection):
    """
    Show a comparison of one entry before and after stripping.
    
    Args:
        source_collection: MongoDB collection with full dataset
        target_collection: MongoDB collection with stripped dataset
    """
    # Find an entry with citation contexts
    source_entry = source_collection.find_one({
        'cited_papers.citation_contexts': {'$exists': True}
    })
    
    if not source_entry:
        logging.warning("No entries with citation contexts found for comparison")
        return
    
    citing_paper_id = source_entry['citing_paper'].get('dblp_id', 'unknown')
    
    # Find corresponding stripped entry
    target_entry = target_collection.find_one({
        'citing_paper.dblp_id': citing_paper_id
    })
    
    if not target_entry:
        logging.warning("Could not find corresponding stripped entry")
        return
    
    logging.info("")
    logging.info("=" * 80)
    logging.info("EXAMPLE COMPARISON: Before and After Stripping")
    logging.info("=" * 80)
    logging.info("")
    logging.info(f"Citing Paper: {citing_paper_id}")
    logging.info("")
    
    # Find a cited paper with contexts
    source_cited = None
    target_cited = None
    
    for cited in source_entry.get('cited_papers', []):
        if 'citation_contexts' in cited:
            cited_id = cited.get('dblp_id') or cited.get('doi')
            source_cited = cited
            
            # Find in target
            for target_c in target_entry.get('cited_papers', []):
                if (target_c.get('dblp_id') or target_c.get('doi')) == cited_id:
                    target_cited = target_c
                    break
            break
    
    if source_cited and target_cited:
        cited_id = source_cited.get('dblp_id') or source_cited.get('doi', 'unknown')
        logging.info(f"Cited Paper: {cited_id}")
        logging.info("")
        logging.info("BEFORE (Full Version):")
        logging.info("-" * 80)
        
        contexts = source_cited.get('citation_contexts', [])
        for idx, ctx in enumerate(contexts[:2]):  # Show first 2 contexts
            logging.info(f"  Context {idx}:")
            logging.info(f"    Section: {ctx.get('section')}")
            logging.info(f"    Text: {ctx.get('text', '')[:100]}...")
            logging.info(f"    Positions: [{ctx.get('cite_start')}, {ctx.get('cite_end')}]")
            logging.info(f"    Intent: {ctx.get('intent')}")
            logging.info("")
        
        if len(contexts) > 2:
            logging.info(f"  ... and {len(contexts) - 2} more contexts")
            logging.info("")
        
        logging.info("")
        logging.info("AFTER (Stripped Version):")
        logging.info("-" * 80)
        
        citations = target_cited.get('citations', [])
        for idx, cit in enumerate(citations[:2]):  # Show first 2 citations
            logging.info(f"  Citation {idx}:")
            logging.info(f"    Citation ID: {cit.get('citation_id')}")
            logging.info(f"    Section: {cit.get('section')}")
            logging.info(f"    Intent: {cit.get('intent')}")
            logging.info("")
        
        if len(citations) > 2:
            logging.info(f"  ... and {len(citations) - 2} more citations")
            logging.info("")
        
        logging.info("=" * 80)
        logging.info("")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Strip citation dataset for publication (removes text snippets and positions)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be stripped (dry run)
  python strip_dataset.py --source-collection dataset --target-collection dataset_stripped --dry-run
  
  # Strip the dataset
  python strip_dataset.py --source-collection dataset --target-collection dataset_stripped
  
  # Show comparison example
  python strip_dataset.py --source-collection dataset --target-collection dataset_stripped --show-example

WARNING: Always maintain the full dataset privately. The stripped version has 
         limited research value but may be required for legal compliance.
        """
    )
    
    parser.add_argument(
        '--source-collection',
        type=str,
        required=True,
        help='Source MongoDB collection name (full dataset with contexts)'
    )
    
    parser.add_argument(
        '--target-collection',
        type=str,
        required=True,
        help='Target MongoDB collection name (stripped dataset)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview stripping without making changes'
    )
    
    parser.add_argument(
        '--show-example',
        action='store_true',
        help='Show before/after comparison example'
    )
    
    args = parser.parse_args()
    
    # Load environment
    load_dotenv()
    
    # Setup logging
    setup_logging()
    
    # Validate collections are different
    if args.source_collection == args.target_collection:
        logging.error("Source and target collections must be different!")
        logging.error("The source collection contains the full dataset that must be preserved.")
        sys.exit(1)
    
    # Connect to MongoDB
    logging.info("Connecting to MongoDB...")
    
    # Get MongoDB credentials from environment
    mongo_config = get_keys()
    mongo_ip = mongo_config.get('mongo_ip', 'localhost')
    mongo_db = mongo_config.get('mongo_db')
    mongo_user = mongo_config.get('mongo_user')
    mongo_pass = mongo_config.get('mongo_pass')
    
    if not mongo_db:
        logging.error("MONGO_DB not set in .env file!")
        sys.exit(1)
    
    # Connect to collections
    source_collection = connect_to_mongo_collection(
        db_name=mongo_db,
        collection_name=args.source_collection,
        ip=mongo_ip,
        username=mongo_user,
        password=mongo_pass,
        auth=bool(get_keys().get('mongo_user'))
    )
    target_collection = connect_to_mongo_collection(
        db_name=mongo_db,
        collection_name=args.target_collection,
        ip=mongo_ip,
        username=mongo_user,
        password=mongo_pass,
        auth=bool(get_keys().get('mongo_user'))
    )
    
    logging.info("✓ Connected to MongoDB")
    logging.info(f"  Database: {mongo_db}")
    logging.info(f"  Source collection: {args.source_collection}")
    logging.info(f"  Target collection: {args.target_collection}")
    logging.info("")
    
    # Strip the dataset
    stats = strip_dataset(source_collection, target_collection, dry_run=args.dry_run)
    
    # Show example comparison if requested
    if args.show_example and not args.dry_run:
        show_example_comparison(source_collection, target_collection)
    
    logging.info("Done!")


if __name__ == '__main__':
    main()
