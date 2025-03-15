"""
Tests for the specification_document module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from tlc.specification_document import (
    load_specification_document,
    list_imports,
    describe_interface,
)
from tlc.markdown_parser import Section, TextBlock, CodeBlock


class TestSpecificationDocument(unittest.TestCase):
    """Test cases for the specification_document module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock specification document
        self.mock_spec = Section(
            "Test Specification",
            [
                TextBlock("This is a test specification with a dependency @test-dependency.md"),
                Section(
                    "Dependencies",
                    [
                        TextBlock("- @dependency1.md"),
                        TextBlock("- @dependency2.md"),
                    ]
                ),
                Section(
                    "Usage",
                    [
                        TextBlock("Example usage:"),
                        CodeBlock(
                            "python",
                            "import module\nmodule.function()"
                        )
                    ]
                ),
                Section(
                    "Implementation",
                    [
                        TextBlock("Implementation details..."),
                        CodeBlock(
                            "python",
                            "def internal_function():\n    pass"
                        )
                    ]
                )
            ]
        )

    @patch('tlc.specification_document.parse_markdown')
    def test_load_specification_document(self, mock_parse_markdown):
        """Test loading a specification document."""
        # Setup
        mock_parse_markdown.return_value = [self.mock_spec]
        
        # Execute
        result = load_specification_document("test_spec.md")
        
        # Verify
        mock_parse_markdown.assert_called_once_with("test_spec.md")
        self.assertEqual(result.title, "Test Specification")
        self.assertEqual(len(result.children), 4)

    @patch('tlc.specification_document.SimpleChat')
    def test_list_imports_regex(self, mock_simple_chat):
        """Test listing imports using regex."""
        # Execute
        imports = list_imports(self.mock_spec)
        
        # Verify
        self.assertEqual(len(imports), 3)
        self.assertIn("test-dependency.md", imports)
        self.assertIn("dependency1.md", imports)
        self.assertIn("dependency2.md", imports)
        
        # Ensure the LLM wasn't called since regex found all imports
        mock_simple_chat.assert_not_called()

    @patch('tlc.specification_document.SimpleChat')
    def test_list_imports_llm_fallback(self, mock_simple_chat):
        """Test listing imports using LLM fallback."""
        # Setup
        mock_chat_instance = MagicMock()
        mock_chat_instance.call.return_value = "dependency3.md\ndependency4.md"
        mock_simple_chat.return_value = mock_chat_instance
        
        # Create a spec with no regex-detectable imports
        spec = Section(
            "Test Specification",
            [
                TextBlock("This references dependency3 and dependency4"),
            ]
        )
        
        # Execute
        imports = list_imports(spec)
        
        # Verify
        mock_simple_chat.assert_called_once()
        mock_chat_instance.call.assert_called_once()
        self.assertEqual(len(imports), 2)
        self.assertIn("dependency3.md", imports)
        self.assertIn("dependency4.md", imports)

    @patch('tlc.specification_document.SimpleChat')
    @patch('tlc.specification_document.load_specification_document')
    @patch('tlc.specification_document.list_imports')
    @patch('os.path.exists')
    def test_describe_interface(self, mock_exists, mock_list_imports, 
                               mock_load_spec, mock_simple_chat):
        """Test describing the interface of a specification."""
        # Setup
        mock_chat_instance = MagicMock()
        # Make the "Usage" section be identified as an interface section
        mock_chat_instance.call.return_value = "yes"
        mock_simple_chat.return_value = mock_chat_instance
        
        # No dependencies for simplicity
        mock_list_imports.return_value = []
        mock_exists.return_value = True
        
        # Execute
        interface = describe_interface(self.mock_spec)
        
        # Verify
        self.assertEqual(interface.title, "Test Specification")
        # Should only include the "Usage" section
        self.assertEqual(len(interface.children), 1)
        self.assertEqual(interface.children[0].title, "Usage")

    @patch('tlc.specification_document.SimpleChat')
    @patch('tlc.specification_document.load_specification_document')
    @patch('tlc.specification_document.list_imports')
    @patch('os.path.exists')
    def test_describe_interface_with_dependencies(self, mock_exists, 
                                                mock_list_imports, 
                                                mock_load_spec, 
                                                mock_simple_chat):
        """Test describing the interface with dependencies."""
        # Setup
        mock_chat_instance = MagicMock()
        # Make the "Usage" section be identified as an interface section
        mock_chat_instance.call.return_value = "yes"
        mock_simple_chat.return_value = mock_chat_instance
        
        # Setup a dependency
        mock_list_imports.return_value = ["dependency1.md"]
        mock_exists.return_value = True
        
        # Create a mock dependency spec
        dependency_spec = Section(
            "Dependency1",
            [
                Section(
                    "Interface",
                    [TextBlock("Dependency interface")]
                )
            ]
        )
        
        # Setup the dependency interface
        dependency_interface = Section(
            "Dependency1",
            [Section("Interface", [TextBlock("Dependency interface")])]
        )
        
        mock_load_spec.return_value = dependency_spec
        
        # Make describe_interface return the dependency interface when called recursively
        with patch('tlc.specification_document.describe_interface', 
                  side_effect=[dependency_interface, interface]) as mock_describe:
            # Execute
            interface = describe_interface(self.mock_spec)
            
            # Verify
            self.assertEqual(interface.title, "Test Specification")
            # Should include the "Usage" section and the dependency section
            self.assertEqual(len(interface.children), 2)
            self.assertEqual(interface.children[0].title, "Dependency: dependency1.md")
            self.assertEqual(interface.children[1].title, "Usage")


if __name__ == '__main__':
    unittest.main() 