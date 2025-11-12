"""
DBLP Lookup Utilities

Shared functions for looking up papers in the DBLP MongoDB collection.
These utilities are used by both the TEI XML parsing workflow and the 
references-only workflow.
"""

from typing import Optional, Dict, Tuple, List
import pymongo


def lookup_paper_by_doi(collection: pymongo.collection.Collection, doi: str) -> Optional[Dict]:
    """
    Look up a paper in DBLP by DOI.
    
    Args:
        collection: MongoDB collection object for DBLP papers
        doi: DOI string (e.g., "10.1234/example")
    
    Returns:
        Full DBLP document if found, None otherwise
    """
    if not doi:
        return None
    
    match_query = {'ee': f'https://doi.org/{doi}'}
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    return result_dict


def lookup_paper_by_arxiv(collection: pymongo.collection.Collection, arxiv_id: str) -> Optional[Dict]:
    """
    Look up a paper in DBLP by arXiv ID.
    
    Args:
        collection: MongoDB collection object for DBLP papers
        arxiv_id: arXiv identifier (e.g., "arXiv:1234.5678" or "1234.5678")
    
    Returns:
        Full DBLP document if found, None otherwise
    """
    if not arxiv_id:
        return None
    
    # Handle both formats: "arXiv:1234.5678" and "1234.5678"
    if ':' in arxiv_id:
        arxiv_id = arxiv_id.split(':')[1]
    
    match_query = {'ee': f'https://arxiv.org/abs/{arxiv_id}'}
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    return result_dict


def lookup_paper_by_title(collection: pymongo.collection.Collection, title: str) -> Optional[Dict]:
    """
    Look up a paper in DBLP by title using fuzzy matching.
    
    Uses the title_concat field (alphanumeric characters only) for matching
    with case-insensitive collation.
    
    Args:
        collection: MongoDB collection object for DBLP papers
        title: Paper title string
    
    Returns:
        Full DBLP document if found, None otherwise
    """
    if not title:
        return None
    
    # Normalize title: remove all non-alphanumeric characters
    match_query = {"title_concat": ''.join(filter(str.isalnum, title))}
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    return result_dict


def lookup_paper_by_filename(collection: pymongo.collection.Collection, 
                              filename: str) -> Tuple[Optional[str], Optional[bool], Optional[List]]:
    """
    Look up a paper in DBLP by filename (key_norm field).
    
    This is used for matching JSON filenames to DBLP records where the filename
    should correspond to the normalized DBLP key.
    
    Args:
        collection: MongoDB collection object for DBLP papers
        filename: File name (e.g., "conf/acl/Smith2020.json")
    
    Returns:
        Tuple of (dblp_key, reference_file_parsed, doi_urls):
        - dblp_key: Original DBLP key (e.g., "conf/acl/Smith2020")
        - reference_file_parsed: Boolean flag indicating if bibliography was parsed
        - doi_urls: List of DOI URLs from the 'ee' field
        Returns (None, None, None) if not found
    """
    if not filename:
        return None, None, None
    
    # Remove file extension to get key_norm
    key_norm = filename.split('.')[0]
    
    match_query = {"key_norm": key_norm}
    result_dict = collection.find_one(match_query, collation={'locale': 'en', 'strength': 2})
    
    if result_dict is not None:
        return (
            result_dict.get('key'),
            result_dict.get('reference_file_parsed', False),
            result_dict.get('ee', [])
        )
    else:
        return None, None, None


def lookup_bibliography_entry_dblp_id(collection: pymongo.collection.Collection,
                                      doi: Optional[str] = None,
                                      arxiv: Optional[str] = None,
                                      title: Optional[str] = None) -> Optional[str]:
    """
    Look up a bibliography entry in DBLP and return normalized key.
    
    Tries multiple lookup strategies in order of priority:
    1. DOI lookup (most reliable)
    2. arXiv ID lookup
    3. Title fuzzy matching (least reliable)
    
    This function is optimized for bibliography parsing where we only need
    the DBLP key for citation linking.
    
    Args:
        collection: MongoDB collection object for DBLP papers
        doi: Optional DOI string
        arxiv: Optional arXiv ID string
        title: Optional title string
    
    Returns:
        DBLP key (key) with slash format if found, None otherwise
    """
    # Try DOI first (most reliable)
    if doi:
        result = lookup_paper_by_doi(collection, doi)
        if result is not None:
            return result.get('key')
    
    # Try arXiv second
    if arxiv:
        result = lookup_paper_by_arxiv(collection, arxiv)
        if result is not None:
            return result.get('key')
    
    # Fall back to title matching
    if title:
        result = lookup_paper_by_title(collection, title)
        if result is not None:
            return result.get('key')
    
    return None
