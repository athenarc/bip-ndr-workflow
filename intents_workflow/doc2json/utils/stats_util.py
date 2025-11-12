"""
Statistics utilities for dataset generation.

This module handles all statistics-related operations including:
- Creating and initializing statistics collections
- Updating cumulative statistics across runs
- Validating statistics consistency
- Printing statistics summaries
"""

import logging
from datetime import datetime
from typing import Dict

from doc2json.utils.env_util import get_keys
from doc2json.utils.mongo_util import connect_to_mongo_collection


def create_stats_collection(fresh_start: bool = False):
    """
    Creates and initializes a MongoDB collection for storing statistics.
    
    Args:
        fresh_start: If True, deletes existing statistics and starts fresh.
                    If False (default), preserves and accumulates statistics across runs.
    
    Returns:
        MongoDB collection object for storing statistics
    """
    init_stats = {
        "key": "statistics",
        # CUMULATIVE FIELDS - These represent the ENTIRE dataset across ALL runs
        # All fields with "total_" prefix are cumulative and keep growing
        "total_papers": 0,              # Total papers in dataset (cumulative)
        "total_refs_checked": 0,        # Total references checked (cumulative)
        "total_refs_skipped": 0,        # Total references skipped (cumulative)
        "total_dois_matched": 0,        # Total DOIs matched (cumulative)
        "total_dois_dblp": 0,           # Total DOIs from DBLP (cumulative)
        "total_dblp_keys_matched": 0,  # Total DBLP keys matched (cumulative)
        "total_citations": 0,           # Total citations in dataset (cumulative)
        "total_contexts_added": 0,      # Total contexts in dataset (cumulative)
        "total_papers_with_contexts": 0,    # Total papers with contexts (cumulative)
        "total_papers_without_contexts": 0, # Total papers without contexts (cumulative)
        "total_papers_skipped_no_citations": 0,  # Total papers skipped because no citations (cumulative)
        # RUN TRACKING - Information about the current/last run only
        "total_runs": 0,                     # Number of times the generator has run
        "last_run_papers_checked": 0,        # Papers checked in last run
        "last_run_papers_inserted": 0,       # Papers inserted in last run
        "last_run_papers_skipped_existing": 0,  # Papers skipped in last run (already in DB)
        "run_history": []                    # List of run timestamps and details
    }
    
    coll = connect_to_mongo_collection(
        db_name=get_keys()['mongo_db'],
        collection_name=f"{get_keys()['stats']}_{get_keys()['mode']}_{get_keys()['latest_date']}",
        ip=get_keys()['mongo_ip'],
        username=get_keys()['mongo_user'],
        password=get_keys()['mongo_pass'],
        auth=bool(get_keys().get('mongo_user'))
    )
    
    if fresh_start:
        # Remove existing stats and insert new
        coll.delete_many({"key": "statistics"})
        coll.insert_one(init_stats)
        logging.info("🔄 Fresh start: Statistics collection cleared")
    else:
        # Check if statistics exist, if not create them
        existing_stats = coll.find_one({"key": "statistics"})
        if not existing_stats:
            coll.insert_one(init_stats)
            logging.info("📊 Statistics collection initialized")
        else:
            logging.info("📊 Statistics collection found - will accumulate across runs")
    
    return coll


def update_cumulative_statistics(stats_collection, current_run_stats: dict, initial_stats: dict):
    """
    Update statistics cumulatively across multiple runs.
    
    All fields with "total_" prefix are CUMULATIVE - they represent the entire dataset.
    Run tracking fields (last_run_*) show what happened in the current run only.
    
    Args:
        stats_collection: MongoDB statistics collection
        current_run_stats: Statistics accumulated during current run
        initial_stats: Statistics at the start of current run (from DB)
    """
    # CUMULATIVE fields - these keep growing, representing the entire dataset
    cumulative_fields = [
        'total_papers',                      # Total papers in dataset
        'total_refs_checked',                # Total refs checked across all runs
        'total_refs_skipped',                # Total refs skipped across all runs
        'total_dblp_keys_matched',           # Total DBLP keys matched
        'total_dois_matched',                # Total DOIs matched
        'total_dois_dblp',                   # Total DOIs from DBLP
        'total_citations',                   # Total citations in dataset
        'total_contexts_added',              # Total contexts in dataset
        'total_papers_with_contexts',        # Total papers with contexts
        'total_papers_without_contexts',     # Total papers without contexts
        'total_papers_skipped_no_citations'  # Total papers skipped (no citations)
    ]
    
    # RUN TRACKING fields - these show what happened THIS RUN only
    run_tracking_fields = [
        'last_run_papers_checked',           # Papers checked in this run
        'last_run_papers_inserted',          # Papers inserted in this run
        'last_run_papers_skipped_existing'   # Papers skipped (already in DB)
    ]
    
    # Calculate the delta for this run
    run_delta = {}
    all_fields = cumulative_fields + run_tracking_fields
    for field in all_fields:
        current_value = current_run_stats.get(field, 0)
        initial_value = initial_stats.get(field, 0)
        run_delta[field] = current_value - initial_value
    
    # Build updated statistics
    updated_stats = {'key': 'statistics'}
    
    # CUMULATIVE fields: ADD the delta to existing values (keep growing)
    for field in cumulative_fields:
        existing_value = initial_stats.get(field, 0)
        delta = run_delta.get(field, 0)
        updated_stats[field] = existing_value + delta
    
    # RUN TRACKING fields: Use the delta (this run's values only)
    for field in run_tracking_fields:
        updated_stats[field] = run_delta.get(field, 0)
    
    # Track run history
    run_history = initial_stats.get('run_history', [])
    run_history.append({
        'timestamp': datetime.now().isoformat(),
        'papers_checked': run_delta.get('last_run_papers_checked', 0),
        'papers_inserted': run_delta.get('last_run_papers_inserted', 0),
        'papers_skipped_existing': run_delta.get('last_run_papers_skipped_existing', 0),
        'citations_added': run_delta.get('total_citations', 0)
    })
    updated_stats['run_history'] = run_history
    updated_stats['total_runs'] = initial_stats.get('total_runs', 0) + 1
    
    # Update statistics in database
    stats_collection.update_one(
        {"key": "statistics"},
        {"$set": updated_stats},
        upsert=True
    )


def validate_statistics(stats: dict) -> bool:
    """
    Validates statistics for consistency and logical correctness.
    
    Args:
        stats: Statistics dictionary to validate
    
    Returns:
        True if all validations pass, False otherwise
    """
    all_valid = True
    
    print("")
    print("=" * 80)
    logging.info("")
    logging.info("=" * 80)
    logging.info("STATISTICS VALIDATION")
    logging.info("=" * 80)
    
    # Validation 1: Citations + Skipped = Total Checked
    check1_left = stats['total_citations'] + stats['total_refs_skipped']
    check1_right = stats['total_refs_checked']
    check1_pass = check1_left == check1_right
    
    logging.info(f"Check 1: total_citations + total_refs_skipped = total_refs_checked")
    logging.info(f"  {stats['total_citations']} + {stats['total_refs_skipped']} = {check1_left}")
    logging.info(f"  Expected: {check1_right}")
    logging.info(f"  Status: {'✓ PASS' if check1_pass else '✗ FAIL'}")
    all_valid = all_valid and check1_pass
    
    # Validation 2: DOIs with DBLP <= DBLP keys matched
    check2_left = stats['total_dois_dblp']
    check2_right = stats['total_dblp_keys_matched']
    check2_pass = check2_left <= check2_right
    
    logging.info(f"\nCheck 2: total_dois_dblp <= total_dblp_keys_matched")
    logging.info(f"  {check2_left} <= {check2_right}")
    logging.info(f"  Status: {'✓ PASS' if check2_pass else '✗ FAIL'}")
    all_valid = all_valid and check2_pass
    
    # Validation 3: DOIs with DBLP <= DOIs matched
    check3_left = stats['total_dois_dblp']
    check3_right = stats['total_dois_matched']
    check3_pass = check3_left <= check3_right
    
    logging.info(f"\nCheck 3: total_dois_dblp <= total_dois_matched")
    logging.info(f"  {check3_left} <= {check3_right}")
    logging.info(f"  Status: {'✓ PASS' if check3_pass else '✗ FAIL'}")
    all_valid = all_valid and check3_pass
    
    # Validation 4: Inclusion-Exclusion Principle
    check4_left = stats['total_citations']
    check4_right = stats['total_dblp_keys_matched'] + stats['total_dois_matched'] - stats['total_dois_dblp']
    check4_pass = check4_left == check4_right
    
    logging.info(f"\nCheck 4: total_citations = total_dblp_keys_matched + total_dois_matched - total_dois_dblp")
    logging.info(f"  {check4_left} = {stats['total_dblp_keys_matched']} + {stats['total_dois_matched']} - {stats['total_dois_dblp']}")
    logging.info(f"  {check4_left} = {check4_right}")
    logging.info(f"  Status: {'✓ PASS' if check4_pass else '✗ FAIL'}")
    all_valid = all_valid and check4_pass
    
    # Validation 5: Papers skipped (no citations) should be reasonable
    check5_papers_skipped = stats.get('total_papers_skipped_no_citations', 0)
    check5_pass = check5_papers_skipped >= 0
    
    logging.info(f"\nCheck 5: total_papers_skipped_no_citations >= 0")
    logging.info(f"  {check5_papers_skipped} >= 0")
    logging.info(f"  Status: {'✓ PASS' if check5_pass else '✗ FAIL'}")
    all_valid = all_valid and check5_pass
    
    # Summary
    logging.info("")
    logging.info("=" * 80)
    if all_valid:
        logging.info("✓ ALL VALIDATIONS PASSED")
    else:
        logging.error("✗ SOME VALIDATIONS FAILED - CHECK YOUR DATA")
    logging.info("=" * 80)
    
    return all_valid


def print_final_statistics(stats: dict, mode: str):
    """
    Print final statistics summary and validate consistency.
    
    Args:
        stats: Statistics dictionary
        mode: Mode of operation ('intents' or 'references')
    """
    # First validate the statistics
    is_valid = validate_statistics(stats)
    
    # Then print the summary
    logging.info("")
    logging.info("=" * 80)
    logging.info("FINAL STATISTICS")
    logging.info("=" * 80)
    logging.info(f"Mode: {mode.upper()}")
    logging.info(f"Total runs: {stats.get('total_runs', 1)}")
    logging.info("")
    logging.info("📊 CUMULATIVE DATASET STATISTICS (All Runs):")
    logging.info(f"  Total papers in dataset: {stats.get('total_papers', 0)}")
    logging.info(f"  Total citations: {stats.get('total_citations', 0)}")
    logging.info(f"  Total references checked: {stats.get('total_refs_checked', 0)}")
    logging.info(f"  Total references skipped: {stats.get('total_refs_skipped', 0)}")
    logging.info(f"  Total papers skipped (no citations): {stats.get('total_papers_skipped_no_citations', 0)}")
    logging.info("")
    logging.info("📈 CUMULATIVE MATCHING STATISTICS:")
    logging.info(f"  Total DBLP keys matched: {stats.get('total_dblp_keys_matched', 0)}")
    logging.info(f"  Total DOIs matched: {stats.get('total_dois_matched', 0)}")
    logging.info(f"  Total DOIs from DBLP: {stats.get('total_dois_dblp', 0)}")
    
    if mode == 'intents':
        logging.info("")
        logging.info("📝 CUMULATIVE CONTEXT STATISTICS:")
        logging.info(f"  Total papers with contexts: {stats.get('total_papers_with_contexts', 0)}")
        logging.info(f"  Total papers without contexts: {stats.get('total_papers_without_contexts', 0)}")
        logging.info(f"  Total contexts added: {stats.get('total_contexts_added', 0)}")
        
        if stats.get('total_papers_with_contexts', 0) > 0:
            avg_contexts = stats['total_contexts_added'] / stats['total_papers_with_contexts']
            logging.info(f"  Average contexts per paper: {avg_contexts:.2f}")
    
    logging.info("")
    logging.info("🔄 LAST RUN SUMMARY:")
    logging.info(f"  Papers checked: {stats.get('last_run_papers_checked', 0)}")
    logging.info(f"  Papers inserted: {stats.get('last_run_papers_inserted', 0)}")
    logging.info(f"  Papers skipped (existing): {stats.get('last_run_papers_skipped_existing', 0)}")
    
    # Show run history if available
    if 'run_history' in stats and len(stats['run_history']) > 1:
        logging.info("")
        logging.info("📜 RUN HISTORY (Last 5 runs):")
        for i, run in enumerate(stats['run_history'][-5:], 1):
            logging.info(f"  Run {i}: {run.get('timestamp', 'N/A')} - "
                        f"{run.get('papers_checked', 0)} checked, "
                        f"{run.get('papers_inserted', 0)} inserted, "
                        f"{run.get('papers_skipped_existing', 0)} skipped")
    
    logging.info("=" * 80)
