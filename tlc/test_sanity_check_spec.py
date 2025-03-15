"""
Tests for the sanity_check_spec module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from tlc.sanity_check_spec import (
    get_module_name,
    read_qa_file,
    write_qa_file,
    write_context_free_spec,
    setup_logging,
    sanity_check_spec,
)


class TestSanityCheckSpec(unittest.TestCase):
    """Test cases for the sanity_check_spec module."""

    def test_get_module_name(self):
        """Test extracting module name from spec path."""
        self.assertEqual(get_module_name("module-name.md"), "module-name")
        self.assertEqual(get_module_name("/path/to/module-name.md"), "module-name")
        self.assertEqual(get_module_name("path/with/module-name.md"), "module-name")

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="Test Q&A content")
    def test_read_qa_file_exists(self, mock_file, mock_exists):
        """Test reading Q&A file when it exists."""
        mock_exists.return_value = True
        result = read_qa_file("module-name")
        self.assertEqual(result, "Test Q&A content")
        mock_file.assert_called_once_with(Path("tlc/module-name.questions.md"), "r")

    @patch("pathlib.Path.exists")
    def test_read_qa_file_not_exists(self, mock_exists):
        """Test reading Q&A file when it doesn't exist."""
        mock_exists.return_value = False
        result = read_qa_file("module-name")
        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open)
    @patch("logging.info")
    def test_write_qa_file(self, mock_log, mock_file):
        """Test writing Q&A file."""
        write_qa_file("module-name", "Test Q&A content")
        mock_file.assert_called_once_with(Path("tlc/module-name.questions.md"), "w")
        mock_file().write.assert_called_once_with("Test Q&A content")
        mock_log.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("logging.info")
    def test_write_context_free_spec(self, mock_log, mock_file):
        """Test writing context-free spec file."""
        write_context_free_spec("module-name", "Test spec content")
        mock_file.assert_called_once_with(Path("tlc/module-name.no-context.md"), "w")
        mock_file().write.assert_called_once_with("Test spec content")
        mock_log.assert_called_once()

    @patch("pathlib.Path.mkdir")
    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    @patch("logging.getLogger")
    def test_setup_logging(self, mock_get_logger, mock_stream_handler, mock_file_handler, mock_mkdir):
        """Test setting up logging."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        result = setup_logging("module-name")
        
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertEqual(mock_logger.addHandler.call_count, 2)
        self.assertEqual(result, mock_logger)

    @patch("tlc.sanity_check_spec.preprocess_spec_context")
    @patch("tlc.sanity_check_spec.write_context_free_spec")
    @patch("tlc.sanity_check_spec.read_qa_file")
    @patch("tlc.sanity_check_spec.SimpleChat")
    @patch("tlc.sanity_check_spec.setup_logging")
    @patch("tlc.sanity_check_spec.save_logs")
    def test_sanity_check_spec_no_questions(self, mock_save_logs, mock_setup_logging, 
                                           mock_simple_chat, mock_read_qa, 
                                           mock_write_context, mock_preprocess):
        """Test sanity check with no questions."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        
        mock_chat = MagicMock()
        mock_simple_chat.return_value = mock_chat
        
        # Configure chat responses
        mock_chat.call.side_effect = [
            "Initial sanity check response",  # Step 1
            "Information check response",     # Step 2
            "yes",                           # Step 3 - should build
            "no"                             # Step 4 - no questions
        ]
        
        mock_preprocess.return_value = "Context-free spec content"
        mock_read_qa.return_value = None
        
        # Call the function
        sanity_check_spec("test-module.md")
        
        # Verify calls
        mock_setup_logging.assert_called_once_with("test-module")
        mock_preprocess.assert_called_once_with("test-module.md")
        mock_write_context.assert_called_once_with("test-module", "Context-free spec content")
        mock_read_qa.assert_called_once_with("test-module")
        
        # Verify SimpleChat was created with the correct system prompt
        self.assertTrue(mock_simple_chat.called)
        system_prompt = mock_simple_chat.call_args[0][0]
        self.assertIn("specification compiler", system_prompt.lower())
        
        # Verify chat calls
        self.assertEqual(mock_chat.call.call_count, 4)
        
        # Verify logs were saved
        mock_save_logs.assert_called_once()

    @patch("tlc.sanity_check_spec.preprocess_spec_context")
    @patch("tlc.sanity_check_spec.write_context_free_spec")
    @patch("tlc.sanity_check_spec.read_qa_file")
    @patch("tlc.sanity_check_spec.write_qa_file")
    @patch("tlc.sanity_check_spec.SimpleChat")
    @patch("tlc.sanity_check_spec.setup_logging")
    @patch("tlc.sanity_check_spec.save_logs")
    def test_sanity_check_spec_with_questions(self, mock_save_logs, mock_setup_logging, 
                                             mock_simple_chat, mock_write_qa, mock_read_qa, 
                                             mock_write_context, mock_preprocess):
        """Test sanity check with questions."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        
        mock_chat = MagicMock()
        mock_simple_chat.return_value = mock_chat
        
        # Configure chat responses
        mock_chat.call.side_effect = [
            "Initial sanity check response",  # Step 1
            "Information check response",     # Step 2
            "yes",                           # Step 3 - should build
            "yes",                           # Step 4 - has questions
            "Q&A content"                    # Step 5 - Q&A content
        ]
        
        mock_preprocess.return_value = "Context-free spec content"
        mock_read_qa.return_value = "Existing Q&A content"
        
        # Call the function
        sanity_check_spec("test-module.md")
        
        # Verify calls
        mock_setup_logging.assert_called_once_with("test-module")
        mock_preprocess.assert_called_once_with("test-module.md")
        mock_write_context.assert_called_once_with("test-module", "Context-free spec content")
        mock_read_qa.assert_called_once_with("test-module")
        
        # Verify SimpleChat was created with the correct system prompt
        self.assertTrue(mock_simple_chat.called)
        
        # Verify chat calls
        self.assertEqual(mock_chat.call.call_count, 5)
        
        # Verify Q&A file was written
        mock_write_qa.assert_called_once_with("test-module", "Q&A content")
        
        # Verify logs were saved
        mock_save_logs.assert_called_once()


if __name__ == "__main__":
    unittest.main() 