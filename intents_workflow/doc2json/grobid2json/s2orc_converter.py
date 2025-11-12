"""
S2ORC Converter Module

This module provides utilities for converting parsed S2ORC paper objects
to various output formats and extracting citation relationships.
"""

import os
import json
from typing import Dict, List, Optional


def metadata_strip(paper) -> Dict:
    """
    Strip paper metadata to essential fields only.
    
    Reduces the size of the output JSON by keeping only:
    - Paper-level metadata: paper_id, header, title, authors, year, venue, identifiers, abstract
    - Paragraph-level data: text, cite_spans, section, sec_num
    
    This is useful for reducing storage requirements while maintaining
    enough information for citation analysis and research paper analysis tasks.
    
    Args:
        paper: S2ORC Paper object with release_json() method
        
    Returns:
        Dict: Stripped paper data with minimized metadata
        
    Example:
        >>> stripped_paper = metadata_strip(paper)
        >>> stripped_paper['paper_id']  # Still have paper ID
        >>> len(stripped_paper['pdf_parse']['body_text'][0])  # But fewer fields per paragraph
    """
    paper_store = {}
    pdf_parse = {}
    
    # Top-level metadata fields to keep
    keys_paper = ['paper_id', 'header', 'title', 'authors', 'year', 'venue', 'identifiers', 'abstract']
    
    # PDF parse section fields to keep
    keys_pdf_parse = ['abstract', 'body_text']
    
    # Per-paragraph fields to keep (important for citation analysis)
    keys_body_text = ['text', 'cite_spans', 'section', 'sec_num']

    # Extract paper-level metadata
    full_json = paper.release_json()
    for key in keys_paper:
        paper_store[key] = full_json[key]

    # Extract paragraph-level data
    for key in keys_pdf_parse:
        paragraphs = []
        for paragraph in full_json['pdf_parse'][key]:
            paragraph_store = {}
            for key_body in keys_body_text:
                paragraph_store[key_body] = paragraph[key_body]
            paragraphs.append(paragraph_store)
        pdf_parse[key] = paragraphs
    
    # Keep bibliography entries (needed for citation linking)
    pdf_parse['bib_entries'] = full_json['pdf_parse']['bib_entries']
    paper_store['pdf_parse'] = pdf_parse

    return paper_store


def generate_s2orc_jsonl(paper: Dict, output_dir: str, pid: str) -> None:
    """
    Extract citation relationships from a paper and generate JSONL file.
    
    This function creates training data for citation context understanding tasks.
    Each line in the output JSONL contains:
    - Citation metadata: citing paper ID, cited paper ID, citation position
    - Context: full text of the paragraph containing the citation
    - Section information: where in the paper the citation appears
    
    The cited_paper_id is looked up from the bibliography using DBLP IDs,
    enabling linking to the global DBLP corpus.
    
    Args:
        paper (Dict): Stripped paper dictionary with citation and bibliography data
        output_dir (str): Directory where JSONL file will be saved
        pid (str): Paper ID (used as filename)
        
    Returns:
        None (writes JSONL file to disk)
        
    Example:
        >>> generate_s2orc_jsonl(stripped_paper, 'output/', 'paper_123')
        # Creates: output/paper_123.jsonl
        # Each line contains one citation with full context
    """
    # Extract body text and bibliography
    body_text = paper["pdf_parse"]["body_text"]
    bib_entries = paper["pdf_parse"]["bib_entries"]

    # Create a dictionary for quick lookup of identifiers by bibliography reference ID
    # Prioritize DBLP IDs, fall back to DOI if DBLP ID not available
    bib_dict = {}
    for key, value in bib_entries.items():
        if "dblp_id" in value and value["dblp_id"]:
            bib_dict[key] = value["dblp_id"]
        elif "other_ids" in value and "DOI" in value["other_ids"]:
            doi = value["other_ids"]["DOI"]
            bib_dict[key] = doi[0] if isinstance(doi, list) else doi

    # List to hold the final JSONL lines
    jsonl_lines = []

    # Loop through each paragraph/text block
    for text_block in body_text:
        section_name = text_block["section"]
        text = text_block["text"]
        cite_spans = text_block["cite_spans"]

        # Loop through each citation mention in this paragraph
        for cite in cite_spans:
            cite_start = cite["start"]
            cite_end = cite["end"]
            ref_id = cite["ref_id"]

            # Get the DBLP ID of the cited paper
            cited_paper_id = bib_dict.get(ref_id)
            citing_paper_id = paper["paper_id"]

            # Only create record if we have a valid DBLP ID for the cited paper
            if cited_paper_id:
                jsonl_obj = {
                    "ref_id": f"{citing_paper_id}_{ref_id}",
                    "sectionName": section_name,
                    "citeStart": cite_start,
                    "citeEnd": cite_end,
                    "string": text,  # Full paragraph text with citation context
                    "citingPaperId": citing_paper_id,
                    "citedPaperId": cited_paper_id,
                    "unique_id": f"{citing_paper_id}>{cited_paper_id}"
                }
                jsonl_lines.append(json.dumps(jsonl_obj))

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Save the output to a .jsonl file (one JSON object per line)
    output_file = os.path.join(output_dir, f"{pid}.jsonl")
    with open(output_file, 'w') as out_f:
        for line in jsonl_lines:
            out_f.write(line + '\n')


def enrich_citations_with_intent(jsonl_file: str, citation_intent_api, output_file: Optional[str] = None) -> List[Dict]:
    """
    Enrich JSONL citation records with citation intent predictions.
    
    This function reads a JSONL file containing citation records and adds
    a 'citationIntent' field to each record by calling the citation intent API.
    
    Citation intents capture the role/purpose of the citation:
    - Background: Foundational or contextual work
    - Methods: References methodology or techniques
    - Results: Comparative results or findings
    - Motivation: Work that motivated the research
    - Future: Work mentioned as future direction
    - Other: Other purposes
    
    Args:
        jsonl_file (str): Path to input JSONL file with citation records
        citation_intent_api: CitationIntentAPI instance for intent prediction
        output_file (Optional[str]): If provided, write enriched data to this file
        
    Returns:
        List[Dict]: List of citation records with added 'citationIntent' field
        
    Example:
        >>> from doc2json.grobid2json.citation_intent_api import MockCitationIntentAPI
        >>> api = MockCitationIntentAPI()
        >>> enriched = enrich_citations_with_intent('citations.jsonl', api, 'enriched.jsonl')
        >>> enriched[0]['citationIntent']  # "Background"
    """
    enriched_citations = []
    
    # Read JSONL file and process each citation
    with open(jsonl_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            citation = json.loads(line)
            
            # For real API, we need the actual cite positions
            # The API will preprocess the text to add @@CITATION@@ tag
            text = citation.get("string", "")
            cite_start = citation.get("citeStart", 0)
            cite_end = citation.get("citeEnd", 0)
            
            # Predict intent using the API
            # The API expects the full text and citation positions
            intent = citation_intent_api.predict_intent(
                citation_context=text,
                cite_start=cite_start,
                cite_end=cite_end,
                citing_section=citation.get("sectionName", "")
            )
            
            # Add intent to citation record
            citation["citationIntent"] = intent
            enriched_citations.append(citation)
    
    # Optionally write to output file
    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, 'w') as out_f:
            for citation in enriched_citations:
                out_f.write(json.dumps(citation) + '\n')
    
    return enriched_citations
