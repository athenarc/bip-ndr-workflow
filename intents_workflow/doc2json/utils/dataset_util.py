"""
Dataset utilities for MongoDB operations.

This module handles dataset-specific operations including:
- Creating and managing dataset indexes
- Inserting/updating dataset entries
- Duplicate detection and handling
"""

import logging
from typing import Dict


def ensure_dataset_indexes(dataset_collection):
    """
    Create indexes on the dataset collection for optimal query performance.
    
    Indexes created:
        1. citing_paper.dblp_id (unique) - Primary key for duplicate detection
        2. cited_papers.dblp_id - For finding papers that cite a specific paper
        3. cited_papers.doi - For DOI-based lookups
        4. cited_papers.citation_contexts.citation_id - For citation intent analysis (sparse)
        5. Composite index on citing_paper.dblp_id + citing_paper.doi
    
    Args:
        dataset_collection: MongoDB collection for the dataset
    """
    logging.info("📑 Ensuring dataset indexes exist...")
    
    try:
        # Index 1: Primary key - citing_paper.dblp_id (UNIQUE)
        # This is our primary identifier for papers, must be unique
        dataset_collection.create_index(
            [("citing_paper.dblp_id", 1)],
            unique=True,
            name="citing_paper_dblp_id_unique"
        )
        logging.info("  ✓ Index 1: citing_paper.dblp_id (unique)")
        
        # Index 2: cited_papers.dblp_id
        # For finding all papers that cite a specific paper by DBLP ID
        dataset_collection.create_index(
            [("cited_papers.dblp_id", 1)],
            name="cited_papers_dblp_id"
        )
        logging.info("  ✓ Index 2: cited_papers.dblp_id")
        
        # Index 3: cited_papers.doi
        # For finding all papers that cite a specific paper by DOI
        dataset_collection.create_index(
            [("cited_papers.doi", 1)],
            name="cited_papers_doi"
        )
        logging.info("  ✓ Index 3: cited_papers.doi")
        
        # Index 4: citation_contexts.citation_id (SPARSE)
        # For citation intent analysis, only exists in intents mode
        dataset_collection.create_index(
            [("cited_papers.citation_contexts.citation_id", 1)],
            sparse=True,
            name="citation_contexts_citation_id"
        )
        logging.info("  ✓ Index 4: cited_papers.citation_contexts.citation_id (sparse)")
        
        # Index 5: Composite index for efficient lookups
        # When we need both DBLP ID and DOI together
        dataset_collection.create_index(
            [
                ("citing_paper.dblp_id", 1),
                ("citing_paper.doi", 1)
            ],
            name="citing_paper_composite"
        )
        logging.info("  ✓ Index 5: citing_paper composite (dblp_id + doi)")
        
        logging.info("✓ All indexes created successfully")
        
    except Exception as e:
        logging.error(f"Error creating indexes: {e}")
        logging.warning("Continuing without indexes - queries may be slow")


def insert_or_update_dataset_entry(collection, entry, stats: dict, skip_existing: bool = False):
    """
    Insert a dataset entry, avoiding duplicates.
    
    Args:
        collection: MongoDB collection
        entry: Dataset entry to insert
        stats: Statistics dictionary to update
        skip_existing: If True, skip existing entries (faster, default behavior)
    
    Returns:
        str: 'inserted' or 'skipped'
    
    Note: We always skip existing entries by default. There's no reason to update
    papers that are already in the dataset - what's in is in. This function only
    tracks insertions and skips.
    """
    citing_dblp_id = entry["citing_paper"].get("dblp_id")
    
    # Check if entry already exists
    existing = collection.find_one({"citing_paper.dblp_id": citing_dblp_id})
    
    if existing:
        # Paper already in dataset - skip it
        stats['last_run_papers_skipped_existing'] = stats.get('last_run_papers_skipped_existing', 0) + 1
        return 'skipped'
    else:
        # Insert new entry
        collection.insert_one(entry)
        stats['last_run_papers_inserted'] = stats.get('last_run_papers_inserted', 0) + 1
        return 'inserted'
