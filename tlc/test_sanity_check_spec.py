import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from .sanity_check_spec import read_spec_file, read_qa_file, write_qa_file, main

@pytest.fixture
def mock_spec_file():
    spec_content = """# Test Spec
This is a test specification file.
"""
    return spec_content

@pytest.fixture
def mock_qa_file():
    qa_content = """**Question**: Test question?
  **Assumption**: Test assumption
"""
    return qa_content

@pytest.fixture
def mock_chat_responses():
    return {
        "sanity_check": "The spec looks good but has some questions.",
        "info_check": "We need more information about X and Y.",
        "build_check": "no",
        "questions_check": "yes",
        "qa_generation": """**Question**: What is X?
  **Assumption**: X is a number.
"""
    }

def test_read_spec_file(mock_spec_file):
    with patch('builtins.open', mock_open(read_data=mock_spec_file)):
        content = read_spec_file("test.md")
        assert content == mock_spec_file

def test_read_qa_file_exists(mock_qa_file):
    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=mock_qa_file)):
            content = read_qa_file("test")
            assert content == mock_qa_file

def test_read_qa_file_not_exists():
    with patch('pathlib.Path.exists', return_value=False):
        content = read_qa_file("test")
        assert content is None

def test_write_qa_file(tmp_path):
    qa_content = "Test Q&A content"
    with patch('pathlib.Path', return_value=tmp_path):
        write_qa_file("test", qa_content)
        qa_file = tmp_path / "test.questions.md"
        assert qa_file.read_text() == qa_content

@patch('tlc.sanity_check_spec.SimpleChat')
@patch('tlc.sanity_check_spec.setup_logging')
@patch('tlc.sanity_check_spec.read_spec_file')
@patch('tlc.sanity_check_spec.read_qa_file')
def test_main_build_failed(mock_read_qa, mock_read_spec, mock_logging, mock_chat_class, 
                          mock_spec_file, mock_chat_responses):
    # Setup mocks
    mock_read_spec.return_value = mock_spec_file
    mock_read_qa.return_value = None
    
    mock_chat = mock_chat_class.return_value
    mock_chat.call.side_effect = [
        mock_chat_responses["sanity_check"],
        mock_chat_responses["info_check"],
        mock_chat_responses["build_check"],
        mock_chat_responses["questions_check"],
        mock_chat_responses["qa_generation"]
    ]
    
    # Run with test arguments
    with patch('sys.argv', ['sanity-check-spec', 'test.md']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1  # Build failed

@patch('tlc.sanity_check_spec.SimpleChat')
@patch('tlc.sanity_check_spec.setup_logging')
@patch('tlc.sanity_check_spec.read_spec_file')
@patch('tlc.sanity_check_spec.read_qa_file')
def test_main_build_success(mock_read_qa, mock_read_spec, mock_logging, mock_chat_class,
                           mock_spec_file, mock_chat_responses):
    # Setup mocks
    mock_read_spec.return_value = mock_spec_file
    mock_read_qa.return_value = None
    
    mock_chat = mock_chat_class.return_value
    mock_chat.call.side_effect = [
        mock_chat_responses["sanity_check"],
        mock_chat_responses["info_check"],
        "yes",  # Build should proceed
        "no"    # No questions
    ]
    
    # Run with test arguments
    with patch('sys.argv', ['sanity-check-spec', 'test.md']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0  # Build succeeded

def test_main_invalid_args():
    with patch('sys.argv', ['sanity-check-spec']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

def test_main_invalid_file_extension():
    with patch('sys.argv', ['sanity-check-spec', 'test.txt']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1 