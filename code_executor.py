import logging
import traceback
from typing import Dict, Any

logger = logging.getLogger(__name__)

def execute_code(box_id: str, code_string: str, input_data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the Python code string associated with a workflow box.

    Args:
        box_id: The ID of the box being executed (for logging).
        code_string: The Python code string (should contain an 'execute' function).
        input_data_dict: A dictionary of input names and their values.

    Returns:
        A dictionary with:
        - 'success': True or False.
        - 'output': The dictionary returned by the user's 'execute' function (if successful).
        - 'error': A string describing the error (if failed).
    """
    logger.info(f"Executing code for box '{box_id}' with input keys: {list(input_data_dict.keys())}")

    # Prepare a namespace for execution
    execution_namespace = {}
    result = {'success': False, 'error': 'Execution did not complete.', 'output': None} # Default result

    try:
        # Execute the provided code string to define the 'execute' function
        # in the temporary namespace.
        exec(code_string, execution_namespace)

        # Check if the 'execute' function was defined
        if 'execute' not in execution_namespace or not callable(execution_namespace['execute']):
            error_msg = f"Box '{box_id}': Code does not define a callable function named 'execute'."
            logger.error(error_msg)
            result['error'] = error_msg
            return result

        # Call the defined 'execute' function with the provided inputs
        logger.debug(f"Calling execute(**{input_data_dict}) for box '{box_id}'")
        output_data = execution_namespace['execute'](**input_data_dict)

        # Validate the output type
        if not isinstance(output_data, dict):
            error_msg = f"Box '{box_id}': 'execute' function did not return a dictionary. Returned type: {type(output_data)}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result

        # Optional: Add validation for JSON serializability here if needed,
        # but the roadmap suggests runner/main might handle JSON aspects later.
        # For now, just check it's a dict.

        logger.info(f"Box '{box_id}' executed successfully. Output keys: {list(output_data.keys())}")
        result['success'] = True
        result['output'] = output_data
        result['error'] = None # Explicitly set error to None on success

    except Exception as e:
        error_msg = f"Box '{box_id}': Execution failed. Error: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        result['success'] = False
        result['error'] = f"Error during execution: {e}" # Return a simpler error message
        result['output'] = None

    return result

if __name__ == '__main__':
    # Example Usage
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- Test Case 1: Successful Execution ---
    print("\n--- Test Case 1: Success ---")
    code_success = """
import json

def execute(input1, multiplier):
    print(f"Executing success case with input1={input1}, multiplier={multiplier}")
    output = {"result": input1 * multiplier, "original": input1}
    print(f"Returning: {output}")
    return output
"""
    inputs_success = {"input1": 10, "multiplier": 5}
    result_success = execute_code("test_box_success", code_success, inputs_success)
    print(f"Result: {result_success}")
    assert result_success['success'] is True
    assert result_success['output'] == {"result": 50, "original": 10}

    # --- Test Case 2: Execution Error ---
    print("\n--- Test Case 2: Execution Error (ZeroDivisionError) ---")
    code_error = """
def execute(value):
    print(f"Executing error case with value={value}")
    result = value / 0 # This will raise ZeroDivisionError
    return {"result": result}
"""
    inputs_error = {"value": 100}
    result_error = execute_code("test_box_error", code_error, inputs_error)
    print(f"Result: {result_error}")
    assert result_error['success'] is False
    assert "division by zero" in result_error['error']
    assert result_error['output'] is None

    # --- Test Case 3: Missing 'execute' function ---
    print("\n--- Test Case 3: Missing 'execute' function ---")
    code_missing_func = """
def run_this(data):
    return {"processed": data}
"""
    inputs_missing_func = {"data": "abc"}
    result_missing_func = execute_code("test_box_missing", code_missing_func, inputs_missing_func)
    print(f"Result: {result_missing_func}")
    assert result_missing_func['success'] is False
    assert "does not define a callable function named 'execute'" in result_missing_func['error']

    # --- Test Case 4: Incorrect Return Type ---
    print("\n--- Test Case 4: Incorrect Return Type (returns list) ---")
    code_wrong_type = """
def execute(items):
    return [item * 2 for item in items] # Returns a list, not a dict
"""
    inputs_wrong_type = {"items": [1, 2, 3]}
    result_wrong_type = execute_code("test_box_wrong_type", code_wrong_type, inputs_wrong_type)
    print(f"Result: {result_wrong_type}")
    assert result_wrong_type['success'] is False
    assert "did not return a dictionary" in result_wrong_type['error']

    # --- Test Case 5: Syntax Error in Code String ---
    print("\n--- Test Case 5: Syntax Error in Code String ---")
    code_syntax_error = """
def execute(a, b) # Missing colon
    return {"sum": a + b}
"""
    inputs_syntax_error = {"a": 1, "b": 2}
    # The error occurs during the `exec` call itself
    result_syntax_error = execute_code("test_box_syntax", code_syntax_error, inputs_syntax_error)
    print(f"Result: {result_syntax_error}")
    assert result_syntax_error['success'] is False
    assert "SyntaxError" in result_syntax_error['error'] or "invalid syntax" in result_syntax_error['error'].lower() # Error message might vary slightly

    print("\n--- All tests finished ---")