"""
test_modules.py — Unit tests for backend modules.

Tests:
  - llm module (Ollama/Groq interfaces)
  - query_analyzer (query parsing)
  - navigator (tree traversal)
  - answer_generator (answer generation)
  - main (FastAPI endpoints)
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import llm
import query_analyzer
import navigator
import answer_generator
import asyncio


# ============================================================================
# TEST UTILITIES
# ============================================================================

def load_test_kb():
    """Load a small test knowledge base."""
    return {
        "System Design": {
            "keywords": ["system", "design"],
            "content": "System design is the art of building scalable systems.",
            "children": {
                "Caching": {
                    "keywords": ["caching", "cache"],
                    "content": "Caching stores frequently used data in fast storage.",
                    "children": {
                        "Consistent Hashing": {
                            "keywords": ["hashing", "consistent"],
                            "content": "Consistent hashing ensures minimal data redistribution when servers change.",
                            "children": {},
                        }
                    },
                },
                "Databases": {
                    "keywords": ["database", "sql", "nosql"],
                    "content": "Databases store and retrieve structured data efficiently.",
                    "children": {},
                },
            },
        }
    }


# ============================================================================
# TEST CASES
# ============================================================================

class TestLLMModule(unittest.TestCase):
    """Test llm.py functions."""
    
    def test_parse_json_response_valid(self):
        """Test parsing valid JSON response."""
        text = '{"key": "value", "number": 42}'
        result = llm.parse_json_response(text)
        self.assertEqual(result["key"], "value")
        self.assertEqual(result["number"], 42)
    
    def test_parse_json_response_invalid(self):
        """Test parsing invalid JSON response."""
        text = "This is not JSON"
        result = llm.parse_json_response(text)
        self.assertEqual(result, {})
    
    def test_parse_json_response_embedded(self):
        """Test parsing embedded JSON in text."""
        text = 'Some text before {"key": "value"} and after'
        result = llm.parse_json_response(text)
        self.assertEqual(result["key"], "value")
    
    @patch("llm.requests.post")
    def test_call_ollama_success(self, mock_post):
        """Test successful Ollama call."""
        mock_post.return_value.json.return_value = {"response": "Test response"}
        result = llm.call_ollama("Test prompt")
        self.assertEqual(result, "Test response")
    
    @patch("llm.requests.post")
    def test_call_ollama_error(self, mock_post):
        """Test Ollama connection error."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(RuntimeError):
            llm.call_ollama("Test prompt")


class TestQueryAnalyzer(unittest.TestCase):
    """Test query_analyzer.py functions."""
    
    def test_extract_keywords_from_text(self):
        """Test keyword extraction."""
        text = "How does consistent hashing work in distributed systems?"
        keywords = query_analyzer.extract_keywords_from_text(text)
        
        # Should extract longer words
        self.assertIn("consistent", keywords)
        self.assertIn("hashing", keywords)
        # Short words should be filtered
        self.assertNotIn("how", keywords)
    
    @patch("query_analyzer.call_llm_async")
    def test_analyze_query(self, mock_llm):
        """Test query analysis."""
        mock_llm.return_value = (
            '{"intent": "understand", "keywords": ["hashing", "distributed"], '
            '"domain": "distributed-systems"}'
        )
        
        result = asyncio.run(query_analyzer.analyze_query("How does hashing work?"))
        self.assertEqual(result["intent"], "understand")
        self.assertIn("hashing", result["keywords"])


class TestNavigator(unittest.TestCase):
    """Test navigator.py functions."""
    
    def setUp(self):
        """Set up test knowledge base."""
        self.kb = load_test_kb()
        self.root = self.kb["System Design"]
    
    def test_keyword_match_score(self):
        """Test keyword matching score."""
        node = {
            "keywords": ["caching", "cache"],
            "content": "Caching stores frequently used data.",
        }
        
        # Exact match
        score = navigator.keyword_match_score(["caching"], node)
        self.assertGreater(score, 0.5)
        
        # No match
        score = navigator.keyword_match_score(["xyz"], node)
        self.assertEqual(score, 0.0)
    
    def test_extract_children_with_children_key(self):
        """Test extracting children from 'children' key."""
        children = navigator.extract_children(self.root)
        self.assertIn("Caching", children)
        self.assertIn("Databases", children)
    
    def test_extract_children_empty(self):
        """Test extracting from node with no children."""
        leaf_node = {"keywords": ["test"], "content": "Test"}
        children = navigator.extract_children(leaf_node)
        self.assertEqual(children, {})
    
    def test_compute_confidence(self):
        """Test confidence calculation."""
        # Confidence = score + depth * 0.05 (capped at 1.0)
        conf = navigator.compute_confidence(0.5, 0)
        self.assertEqual(conf, 0.5)
        
        conf = navigator.compute_confidence(0.5, 10)
        self.assertEqual(conf, 1.0)  # Capped at 1.0
    
    def test_full_tree_traversal(self):
        """Test exhaustive tree traversal."""
        keywords = ["hashing"]
        best_node, name, path, score = navigator.full_tree_traversal(
            "hashing", keywords, self.root
        )
        
        # Should find Consistent Hashing node
        self.assertGreater(score, 0.0)
        self.assertEqual(name, "Consistent Hashing")


class TestAnswerGenerator(unittest.TestCase):
    """Test answer_generator.py functions."""
    
    def test_extract_excerpt_short_content(self):
        """Test excerpt extraction with short content."""
        content = "This is a short content."
        excerpt = answer_generator.extract_excerpt(content, 100)
        self.assertEqual(excerpt, content)
    
    def test_extract_excerpt_long_content(self):
        """Test excerpt extraction with long content."""
        content = "This is a long content. " * 10
        excerpt = answer_generator.extract_excerpt(content, 50)
        self.assertLess(len(excerpt), len(content))
        self.assertTrue(excerpt.endswith("...") or excerpt.endswith("."))
    
    @patch("answer_generator.call_llm_async")
    def test_generate_answer(self, mock_llm):
        """Test answer generation."""
        mock_llm.return_value = "Test answer"

        answer = asyncio.run(
            answer_generator.generate_answer(
                "Test query",
                "Test content",
                ["System Design", "Caching"],
            )
        )

        self.assertEqual(answer, "Test answer")


class TestIntegration(unittest.TestCase):
    """Integration tests for the full pipeline."""
    
    def setUp(self):
        """Set up test data."""
        self.kb = load_test_kb()
        self.root = self.kb["System Design"]
    
    @patch("navigator.call_llm_async")
    def test_full_query_pipeline_keyword_only(self, mock_llm):
        """Test full pipeline with keyword-only scoring."""
        # Mock LLM to avoid external calls
        mock_llm.return_value = '{"Consistent Hashing": 0.1, "Databases": 0.0}'
        
        keywords = ["hashing", "consistent"]
        
        result = asyncio.run(
            navigator.navigate_tree(
                "How does consistent hashing work?",
                keywords,
                self.root,
                max_depth=3,
            )
        )
        
        # Should navigate to some node
        self.assertIn("best_node", result)
        self.assertGreaterEqual(result["score"], 0.0)


# ============================================================================
# MAIN
# ============================================================================

def run_all_tests():
    """Run all tests and print results."""
    print("\n" + "="*70)
    print("RUNNING BACKEND MODULE TESTS")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestLLMModule))
    suite.addTests(loader.loadTestsFromTestCase(TestQueryAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestNavigator))
    suite.addTests(loader.loadTestsFromTestCase(TestAnswerGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
