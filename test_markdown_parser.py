import pytest
import os
from markdown_parser import parse_markdown_file

# Define the path to the workflow file relative to the test file
WORKFLOW_FILE_PATH = os.path.join(os.path.dirname(__file__), 'workflow.md')

# Make sure the workflow.md file exists before running tests
@pytest.fixture(scope="module", autouse=True)
def check_workflow_file():
    if not os.path.exists(WORKFLOW_FILE_PATH):
        pytest.fail(f"Required test file not found: {WORKFLOW_FILE_PATH}")

def test_parse_valid_workflow_md():
    """Tests parsing the standard workflow.md file."""
    parsed_data = parse_markdown_file(WORKFLOW_FILE_PATH)

    # --- Assertions for Boxes ---
    assert 'boxes' in parsed_data
    assert isinstance(parsed_data['boxes'], list)
    assert len(parsed_data['boxes']) == 2, "Should find 2 boxes"

    # Find boxes by ID for easier assertions
    boxes_by_id = {box['id']: box for box in parsed_data['boxes']}
    assert 'generate_numbers' in boxes_by_id
    assert 'add_numbers' in boxes_by_id

    # Box 1: generate_numbers
    gen_box = boxes_by_id['generate_numbers']
    assert gen_box['id'] == 'generate_numbers'
    assert 'seed' in gen_box.get('inputs', []), "generate_numbers should have 'seed' input"
    assert len(gen_box.get('inputs', [])) == 1
    assert 'import random' in gen_box.get('code', '')
    assert 'def execute(seed=None):' in gen_box.get('code', '')
    assert 'return {"number1": num1, "number2": num2}' in gen_box.get('code', '')
    assert gen_box.get('description') == 'Generates two random integers between 1 and 100.'


    # Box 2: add_numbers
    add_box = boxes_by_id['add_numbers']
    assert add_box['id'] == 'add_numbers'
    assert 'input_data' in add_box.get('inputs', []), "add_numbers should now have 'input_data' input"
    assert len(add_box.get('inputs', [])) == 1, "add_numbers should now have only 1 input"
    assert 'def execute(input_data):' in add_box.get('code', ''), "Code should reflect the new input name"
    assert 'return {"sum": total}' in add_box.get('code', '')
    assert add_box.get('description') == 'Adds the two numbers received as input.'

    # --- Assertions for Connections ---
    assert 'connections' in parsed_data
    assert isinstance(parsed_data['connections'], list)
    assert len(parsed_data['connections']) == 1, "Should find 1 connection now"

    # Check connection details
    expected_connection = {'source': 'generate_numbers', 'target': 'add_numbers', 'target_input': 'input_data'}
    # Simple check: convert to tuple of items for comparison
    parsed_conn_tuple = tuple(sorted(parsed_data['connections'][0].items()))
    expected_conn_tuple = tuple(sorted(expected_connection.items()))
    assert parsed_conn_tuple == expected_conn_tuple, "Connection details should match the updated workflow"

    # --- Assertions for Layout ---
    assert 'layout' in parsed_data
    assert isinstance(parsed_data['layout'], dict)
    assert len(parsed_data['layout']) == 2, "Should find 2 layout entries"

    assert 'generate_numbers' in parsed_data['layout']
    assert parsed_data['layout']['generate_numbers'] == {'x': 100, 'y': 150}

    assert 'add_numbers' in parsed_data['layout']
    assert parsed_data['layout']['add_numbers'] == {'x': 400, 'y': 150}

def test_parse_non_existent_file():
    """Tests parsing a file that does not exist."""
    parsed_data = parse_markdown_file("non_existent_workflow.md")
    assert 'boxes' in parsed_data and not parsed_data['boxes']
    assert 'connections' in parsed_data and not parsed_data['connections']
    assert 'layout' in parsed_data and not parsed_data['layout']

# You could add more tests here for edge cases:
# - Empty file
# - File with only headers
# - File with incorrect formatting (e.g., bad connection string, invalid layout JSON)
# - File with duplicate box names (parser currently warns and overwrites, test this behavior)