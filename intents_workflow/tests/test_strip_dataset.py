"""
Unit tests for dataset stripping utility.

These tests verify that citation contexts are correctly stripped
and replaced with citation IDs while preserving structure.
"""

import pytest
from strip_dataset import (
    generate_citation_id,
    strip_citation_contexts,
    strip_dataset_entry
)


def test_generate_citation_id():
    """Test citation ID generation with various formats."""
    # Basic DBLP IDs
    cit_id = generate_citation_id(
        "conf/acl/Smith20",
        "conf/acl/Johnson07",
        0
    )
    assert cit_id == "conf_acl_Smith20>conf_acl_Johnson07_CIT0"
    
    # Multiple citation instances
    cit_id_1 = generate_citation_id(
        "conf/acl/Smith20",
        "conf/acl/Johnson07",
        1
    )
    assert cit_id_1 == "conf_acl_Smith20>conf_acl_Johnson07_CIT1"
    
    # DOI as cited paper ID
    cit_id_doi = generate_citation_id(
        "conf/acl/Smith20",
        "10.1234/example.2020",
        0
    )
    assert cit_id_doi == "conf_acl_Smith20>10_1234_example_2020_CIT0"


def test_strip_citation_contexts():
    """Test stripping of citation contexts."""
    contexts = [
        {
            "section": "Introduction",
            "text": "Previous work (Johnson, 2007) showed...",
            "cite_start": 15,
            "cite_end": 29,
            "intent": "background information"
        },
        {
            "section": "Methods",
            "text": "We use the approach from Johnson (2007).",
            "cite_start": 25,
            "cite_end": 39,
            "intent": "method"
        }
    ]
    
    stripped = strip_citation_contexts(
        contexts,
        "conf/acl/Smith20",
        "conf/acl/Johnson07"
    )
    
    assert len(stripped) == 2
    
    # First citation
    assert "citation_id" in stripped[0]
    assert stripped[0]["citation_id"] == "conf_acl_Smith20>conf_acl_Johnson07_CIT0"
    assert stripped[0]["section"] == "Introduction"
    assert stripped[0]["intent"] == "background information"
    assert "text" not in stripped[0]
    assert "cite_start" not in stripped[0]
    assert "cite_end" not in stripped[0]
    
    # Second citation
    assert stripped[1]["citation_id"] == "conf_acl_Smith20>conf_acl_Johnson07_CIT1"
    assert stripped[1]["section"] == "Methods"
    assert stripped[1]["intent"] == "method"


def test_strip_dataset_entry_with_contexts():
    """Test stripping a complete dataset entry with citation contexts."""
    entry = {
        "citing_paper": {
            "dblp_id": "conf/acl/Smith20",
            "doi": "10.1234/smith2020"
        },
        "cited_papers": [
            {
                "dblp_id": "conf/acl/Johnson07",
                "bibliographic_reference": "Johnson, M. (2007). Example paper.",
                "citation_contexts": [
                    {
                        "section": "Introduction",
                        "text": "Previous work (Johnson, 2007) showed...",
                        "cite_start": 15,
                        "cite_end": 29,
                        "intent": "background information"
                    }
                ]
            },
            {
                "doi": "10.5678/brown2019",
                "bibliographic_reference": "Brown, A. (2019). Another paper.",
                "citation_contexts": [
                    {
                        "section": "Methods",
                        "text": "Following Brown et al. (2019)...",
                        "cite_start": 10,
                        "cite_end": 29,
                        "intent": "method"
                    }
                ]
            }
        ]
    }
    
    stripped = strip_dataset_entry(entry)
    
    # Check citing paper unchanged
    assert stripped["citing_paper"]["dblp_id"] == "conf/acl/Smith20"
    assert stripped["citing_paper"]["doi"] == "10.1234/smith2020"
    
    # Check cited papers
    assert len(stripped["cited_papers"]) == 2
    
    # First cited paper (with DBLP ID)
    cited1 = stripped["cited_papers"][0]
    assert cited1["dblp_id"] == "conf/acl/Johnson07"
    assert cited1["bibliographic_reference"] == "Johnson, M. (2007). Example paper."
    assert "citation_contexts" not in cited1
    assert "citations" in cited1
    assert len(cited1["citations"]) == 1
    assert cited1["citations"][0]["citation_id"] == "conf_acl_Smith20>conf_acl_Johnson07_CIT0"
    assert cited1["citations"][0]["intent"] == "background information"
    assert "text" not in cited1["citations"][0]
    
    # Second cited paper (with DOI only)
    cited2 = stripped["cited_papers"][1]
    assert cited2["doi"] == "10.5678/brown2019"
    assert "citations" in cited2
    assert len(cited2["citations"]) == 1
    assert cited2["citations"][0]["citation_id"] == "conf_acl_Smith20>10_5678_brown2019_CIT0"


def test_strip_dataset_entry_without_contexts():
    """Test stripping an entry without citation contexts (references mode)."""
    entry = {
        "citing_paper": {
            "dblp_id": "conf/acl/Smith20"
        },
        "cited_papers": [
            {
                "dblp_id": "conf/acl/Johnson07",
                "bibliographic_reference": "Johnson, M. (2007). Example paper."
            }
        ]
    }
    
    stripped = strip_dataset_entry(entry)
    
    # Entry should be unchanged except for removal of citation_contexts field
    assert stripped["citing_paper"]["dblp_id"] == "conf/acl/Smith20"
    assert len(stripped["cited_papers"]) == 1
    assert stripped["cited_papers"][0]["dblp_id"] == "conf/acl/Johnson07"
    assert "citation_contexts" not in stripped["cited_papers"][0]
    assert "citations" not in stripped["cited_papers"][0]


def test_strip_multiple_citations_same_paper():
    """Test stripping when same paper is cited multiple times."""
    contexts = [
        {
            "section": "Introduction",
            "text": "First mention (Smith, 2020)...",
            "cite_start": 15,
            "cite_end": 27,
            "intent": "background information"
        },
        {
            "section": "Methods",
            "text": "Second mention (Smith, 2020)...",
            "cite_start": 16,
            "cite_end": 28,
            "intent": "method"
        },
        {
            "section": "Results",
            "text": "Third mention (Smith, 2020)...",
            "cite_start": 14,
            "cite_end": 26,
            "intent": "results comparison"
        }
    ]
    
    stripped = strip_citation_contexts(
        contexts,
        "conf/acl/Jones21",
        "conf/acl/Smith20"
    )
    
    assert len(stripped) == 3
    
    # Check each citation has unique ID
    assert stripped[0]["citation_id"] == "conf_acl_Jones21>conf_acl_Smith20_CIT0"
    assert stripped[1]["citation_id"] == "conf_acl_Jones21>conf_acl_Smith20_CIT1"
    assert stripped[2]["citation_id"] == "conf_acl_Jones21>conf_acl_Smith20_CIT2"
    
    # Check intents preserved
    assert stripped[0]["intent"] == "background information"
    assert stripped[1]["intent"] == "method"
    assert stripped[2]["intent"] == "results comparison"


def test_citation_id_format_consistency():
    """Test that citation IDs follow consistent format."""
    cit_id = generate_citation_id(
        "conf/acl-naacl/Smith-Jones20",
        "journals/ai/Brown.Miller19",
        5
    )
    
    # Should convert slashes, dashes, and dots to underscores
    # Should use > separator between citing and cited papers
    assert "/" not in cit_id
    assert "." not in cit_id
    assert ">" in cit_id
    # Note: dashes in names are converted to underscores
    assert cit_id == "conf_acl_naacl_Smith_Jones20>journals_ai_Brown_Miller19_CIT5"


def test_strip_with_existing_citation_id():
    """Test stripping when citation_id is already present (new workflow)."""
    contexts = [
        {
            "citation_id": "conf_acl_Jones21>conf_acl_Smith20_CIT0",
            "section": "Introduction",
            "text": "Previous work (Smith, 2020) showed...",
            "cite_start": 15,
            "cite_end": 29,
            "intent": "background information"
        },
        {
            "citation_id": "conf_acl_Jones21>conf_acl_Smith20_CIT1",
            "section": "Methods",
            "text": "We use the approach from Smith (2020).",
            "cite_start": 25,
            "cite_end": 39,
            "intent": "method"
        }
    ]
    
    stripped = strip_citation_contexts(
        contexts,
        "conf/acl/Jones21",
        "conf/acl/Smith20"
    )
    
    assert len(stripped) == 2
    
    # Should preserve existing citation IDs
    assert stripped[0]["citation_id"] == "conf_acl_Jones21>conf_acl_Smith20_CIT0"
    assert stripped[1]["citation_id"] == "conf_acl_Jones21>conf_acl_Smith20_CIT1"
    
    # Text and positions should be removed
    assert "text" not in stripped[0]
    assert "cite_start" not in stripped[0]
    assert "cite_end" not in stripped[0]
    
    # Section and intent should be preserved
    assert stripped[0]["section"] == "Introduction"
    assert stripped[0]["intent"] == "background information"
    assert stripped[1]["section"] == "Methods"
    assert stripped[1]["intent"] == "method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
