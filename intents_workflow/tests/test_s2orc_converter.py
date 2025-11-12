"""
Test cases for S2ORC Converter Module

Tests the metadata_strip() and generate_s2orc_jsonl() functions
to ensure proper citation extraction and metadata handling.
"""

import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch

from doc2json.grobid2json.s2orc_converter import metadata_strip, generate_s2orc_jsonl


class TestMetadataStrip(unittest.TestCase):
    """Test cases for metadata_strip function"""

    def setUp(self):
        """Create mock paper objects for testing"""
        self.mock_paper = Mock()

    def test_metadata_strip_preserves_paper_id(self):
        """Test that paper_id is preserved after stripping"""
        test_json = {
            'paper_id': 'test_paper_123',
            'header': {'generated_with': 'S2ORC v1', 'date_generated': '2024-01-01'},
            'title': 'Test Paper',
            'authors': [],
            'year': '2024',
            'venue': 'Test Conference',
            'identifiers': {},
            'abstract': [],
            'pdf_parse': {
                'abstract': [],
                'body_text': [],
                'bib_entries': {}
            }
        }
        self.mock_paper.release_json.return_value = test_json
        
        result = metadata_strip(self.mock_paper)
        
        self.assertEqual(result['paper_id'], 'test_paper_123')

    def test_metadata_strip_preserves_essential_metadata(self):
        """Test that essential metadata fields are preserved"""
        test_json = {
            'paper_id': 'test_paper',
            'header': {'info': 'header_info'},
            'title': 'Test Title',
            'authors': [{'first': 'John', 'last': 'Doe'}],
            'year': '2024',
            'venue': 'Conference',
            'identifiers': {'doi': '10.1234/test'},
            'abstract': [],
            'pdf_parse': {
                'abstract': [],
                'body_text': [],
                'bib_entries': {}
            }
        }
        self.mock_paper.release_json.return_value = test_json
        
        result = metadata_strip(self.mock_paper)
        
        self.assertEqual(result['title'], 'Test Title')
        self.assertEqual(result['year'], '2024')
        self.assertEqual(result['venue'], 'Conference')
        self.assertIn('authors', result)

    def test_metadata_strip_body_text_keeps_essential_fields(self):
        """Test that only essential paragraph fields are kept"""
        test_json = {
            'paper_id': 'test_paper',
            'header': {},
            'title': 'Test',
            'authors': [],
            'year': '2024',
            'venue': 'Conf',
            'identifiers': {},
            'abstract': [],
            'pdf_parse': {
                'abstract': [],
                'body_text': [
                    {
                        'text': 'This is a paragraph.',
                        'cite_spans': [{'start': 10, 'end': 15, 'ref_id': 'ref1'}],
                        'ref_spans': [],
                        'eq_spans': [],
                        'section': 'Introduction',
                        'sec_num': '1',
                        # These fields should be stripped:
                        'extra_field': 'should be removed',
                        'another_field': 123
                    }
                ],
                'bib_entries': {'ref1': {'title': 'Cited Paper'}}
            }
        }
        self.mock_paper.release_json.return_value = test_json
        
        result = metadata_strip(self.mock_paper)
        
        body_text = result['pdf_parse']['body_text'][0]
        # Check that essential fields are present
        self.assertIn('text', body_text)
        self.assertIn('cite_spans', body_text)
        self.assertIn('section', body_text)
        self.assertIn('sec_num', body_text)
        # Check that extra fields are removed
        self.assertNotIn('extra_field', body_text)
        self.assertNotIn('another_field', body_text)

    def test_metadata_strip_bibliography_preserved(self):
        """Test that bibliography entries are preserved"""
        bib_entries = {
            'ref1': {
                'title': 'Paper 1',
                'authors': [],
                'dblp_id': 'dblp_123',
                'year': 2020
            },
            'ref2': {
                'title': 'Paper 2',
                'authors': [],
                'dblp_id': 'dblp_456',
                'year': 2021
            }
        }
        test_json = {
            'paper_id': 'test_paper',
            'header': {},
            'title': 'Test',
            'authors': [],
            'year': '2024',
            'venue': 'Conf',
            'identifiers': {},
            'abstract': [],
            'pdf_parse': {
                'abstract': [],
                'body_text': [],
                'bib_entries': bib_entries
            }
        }
        self.mock_paper.release_json.return_value = test_json
        
        result = metadata_strip(self.mock_paper)
        
        self.assertEqual(len(result['pdf_parse']['bib_entries']), 2)
        self.assertIn('ref1', result['pdf_parse']['bib_entries'])
        self.assertIn('ref2', result['pdf_parse']['bib_entries'])


class TestGenerateS2OrcJsonl(unittest.TestCase):
    """Test cases for generate_s2orc_jsonl function"""

    def setUp(self):
        """Create temporary directory for test outputs"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generate_s2orc_jsonl_creates_file(self):
        """Test that JSONL file is created"""
        paper = {
            'paper_id': 'citing_paper_1',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Previous work [1] showed that...',
                        'cite_spans': [
                            {'start': 15, 'end': 18, 'ref_id': 'ref1'}
                        ],
                        'section': 'Introduction',
                        'sec_num': '1'
                    }
                ],
                'bib_entries': {
                    'ref1': {
                        'title': 'Cited Paper',
                        'dblp_id': 'cited_paper_1'
                    }
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        self.assertTrue(os.path.exists(output_file))

    def test_generate_s2orc_jsonl_valid_json_lines(self):
        """Test that each line in JSONL is valid JSON"""
        paper = {
            'paper_id': 'citing_paper_1',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Previous work [1] and [2] showed...',
                        'cite_spans': [
                            {'start': 15, 'end': 18, 'ref_id': 'ref1'},
                            {'start': 23, 'end': 26, 'ref_id': 'ref2'}
                        ],
                        'section': 'Introduction',
                        'sec_num': '1'
                    }
                ],
                'bib_entries': {
                    'ref1': {'title': 'Paper 1', 'dblp_id': 'paper_1'},
                    'ref2': {'title': 'Paper 2', 'dblp_id': 'paper_2'}
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        with open(output_file, 'r') as f:
            for line in f:
                json_obj = json.loads(line)  # Should not raise exception
                self.assertIsInstance(json_obj, dict)

    def test_generate_s2orc_jsonl_citation_count(self):
        """Test that correct number of citations are extracted"""
        paper = {
            'paper_id': 'citing_paper_1',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Citation [1]',
                        'cite_spans': [{'start': 10, 'end': 13, 'ref_id': 'ref1'}],
                        'section': 'Section A',
                        'sec_num': '1'
                    },
                    {
                        'text': 'More citations [2] and [3]',
                        'cite_spans': [
                            {'start': 14, 'end': 17, 'ref_id': 'ref2'},
                            {'start': 22, 'end': 25, 'ref_id': 'ref3'}
                        ],
                        'section': 'Section B',
                        'sec_num': '2'
                    }
                ],
                'bib_entries': {
                    'ref1': {'title': 'P1', 'dblp_id': 'p1'},
                    'ref2': {'title': 'P2', 'dblp_id': 'p2'},
                    'ref3': {'title': 'P3', 'dblp_id': 'p3'}
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        line_count = 0
        with open(output_file, 'r') as f:
            for line in f:
                line_count += 1
        
        self.assertEqual(line_count, 3)  # 3 citations total

    def test_generate_s2orc_jsonl_skips_unmapped_citations(self):
        """Test that citations without DBLP IDs are skipped"""
        paper = {
            'paper_id': 'citing_paper_1',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Citations [1], [2], [3]',
                        'cite_spans': [
                            {'start': 12, 'end': 15, 'ref_id': 'ref1'},
                            {'start': 17, 'end': 20, 'ref_id': 'ref2'},
                            {'start': 22, 'end': 25, 'ref_id': 'ref3'}
                        ],
                        'section': 'Intro',
                        'sec_num': '1'
                    }
                ],
                'bib_entries': {
                    'ref1': {'title': 'P1', 'dblp_id': 'p1'},
                    'ref2': {'title': 'P2', 'dblp_id': None},  # No DBLP ID
                    'ref3': {'title': 'P3', 'dblp_id': 'p3'}
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        line_count = 0
        with open(output_file, 'r') as f:
            for line in f:
                line_count += 1
        
        self.assertEqual(line_count, 2)  # Only 2 citations (ref2 skipped)

    def test_generate_s2orc_jsonl_contains_required_fields(self):
        """Test that each JSONL line contains all required fields"""
        paper = {
            'paper_id': 'citing_paper_1',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Previous work [1] showed...',
                        'cite_spans': [{'start': 14, 'end': 17, 'ref_id': 'ref1'}],
                        'section': 'Related Work',
                        'sec_num': '2'
                    }
                ],
                'bib_entries': {
                    'ref1': {'title': 'Paper 1', 'dblp_id': 'cited_paper_1'}
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        with open(output_file, 'r') as f:
            line = f.readline()
            json_obj = json.loads(line)
            
            # Check for required fields
            required_fields = [
                'ref_id',
                'sectionName',
                'citeStart',
                'citeEnd',
                'string',
                'citingPaperId',
                'citedPaperId',
                'unique_id'
            ]
            for field in required_fields:
                self.assertIn(field, json_obj)

    def test_generate_s2orc_jsonl_paper_ids_correct(self):
        """Test that citing and cited paper IDs are correctly set"""
        paper = {
            'paper_id': 'my_paper_123',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Cited work [1]',
                        'cite_spans': [{'start': 11, 'end': 14, 'ref_id': 'ref1'}],
                        'section': 'Intro',
                        'sec_num': '1'
                    }
                ],
                'bib_entries': {
                    'ref1': {'title': 'Other Paper', 'dblp_id': 'other_paper_456'}
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        with open(output_file, 'r') as f:
            json_obj = json.loads(f.readline())
            
            self.assertEqual(json_obj['citingPaperId'], 'my_paper_123')
            self.assertEqual(json_obj['citedPaperId'], 'other_paper_456')
            self.assertEqual(json_obj['unique_id'], 'my_paper_123>other_paper_456')

    def test_generate_s2orc_jsonl_empty_body_text(self):
        """Test handling of papers with no body text"""
        paper = {
            'paper_id': 'empty_paper',
            'pdf_parse': {
                'body_text': [],
                'bib_entries': {}
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'empty_paper')
        
        output_file = os.path.join(self.test_dir, 'empty_paper.jsonl')
        # Should still create file, but it will be empty
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.path.getsize(output_file), 0)

    def test_generate_s2orc_jsonl_citation_positions(self):
        """Test that citation positions are correctly captured"""
        paper = {
            'paper_id': 'citing_paper',
            'pdf_parse': {
                'body_text': [
                    {
                        'text': 'Some text here [1] more text',
                        'cite_spans': [{'start': 15, 'end': 18, 'ref_id': 'ref1'}],
                        'section': 'Main',
                        'sec_num': '1'
                    }
                ],
                'bib_entries': {
                    'ref1': {'title': 'Cited', 'dblp_id': 'cited'}
                }
            }
        }
        
        generate_s2orc_jsonl(paper, self.test_dir, 'test_paper')
        
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        with open(output_file, 'r') as f:
            json_obj = json.loads(f.readline())
            
            self.assertEqual(json_obj['citeStart'], 15)
            self.assertEqual(json_obj['citeEnd'], 18)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""

    def setUp(self):
        """Create temporary directory for test outputs"""
        self.test_dir = tempfile.mkdtemp()
        self.mock_paper = Mock()

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_metadata_strip_then_generate_jsonl(self):
        """Test complete workflow: strip metadata then generate JSONL"""
        # Create mock paper with full data
        full_json = {
            'paper_id': 'test_paper',
            'header': {'generated': 'header'},
            'title': 'Test Paper',
            'authors': [],
            'year': '2024',
            'venue': 'Conf',
            'identifiers': {},
            'abstract': [],
            'pdf_parse': {
                'abstract': [],
                'body_text': [
                    {
                        'text': 'Previous work [1] showed interesting results.',
                        'cite_spans': [{'start': 15, 'end': 18, 'ref_id': 'ref1'}],
                        'ref_spans': [],
                        'eq_spans': [],
                        'section': 'Background',
                        'sec_num': '2',
                        'extra_metadata': 'should be removed'
                    }
                ],
                'bib_entries': {
                    'ref1': {
                        'title': 'Related Work',
                        'authors': [],
                        'dblp_id': 'related_paper_123',
                        'year': 2023,
                        'venue': 'Journal'
                    }
                }
            }
        }
        self.mock_paper.release_json.return_value = full_json
        
        # Step 1: Strip metadata
        stripped = metadata_strip(self.mock_paper)
        
        # Step 2: Generate JSONL
        generate_s2orc_jsonl(stripped, self.test_dir, 'test_paper')
        
        # Verify JSONL was created with correct data
        output_file = os.path.join(self.test_dir, 'test_paper.jsonl')
        with open(output_file, 'r') as f:
            json_obj = json.loads(f.readline())
            self.assertEqual(json_obj['citingPaperId'], 'test_paper')
            self.assertEqual(json_obj['citedPaperId'], 'related_paper_123')
            self.assertIn('Previous work', json_obj['string'])


if __name__ == '__main__':
    unittest.main()
