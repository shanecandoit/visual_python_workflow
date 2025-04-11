import re
import logging

logger = logging.getLogger(__name__)

def parse_markdown_file(file_path: str) -> dict:
    """
    Parses a workflow Markdown file to extract boxes, connections, and layout.

    Args:
        file_path: The path to the Markdown file.

    Returns:
        A dictionary containing parsed 'boxes', 'connections', and 'layout'.
        Returns an empty dict with lists/dicts if parsing fails or file not found.
    """
    logger.info(f"Attempting to parse Markdown file: {file_path}")
    parsed_data = {'boxes': [], 'connections': [], 'layout': {}}
    current_section = None
    current_box = None
    in_code_block = False
    code_buffer = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, original_line in enumerate(f, 1):
                # Keep original line for code blocks, use stripped line for logic
                line = original_line.strip()
                line = line.strip()

                # Section Headers
                if line.startswith("## BOX:"):
                    if current_box: # Save previous box before starting new one
                        current_box['code'] = "\n".join(code_buffer).strip()
                        parsed_data['boxes'].append(current_box)
                    current_section = "box"
                    box_name = line.split(":", 1)[1].strip()
                    if not box_name:
                        logger.warning(f"Line {line_num}: Found '## BOX:' without a name. Skipping.")
                        current_box = None
                        continue
                    current_box = {'id': box_name, 'description': '', 'inputs': [], 'code': ''}
                    code_buffer = []
                    in_code_block = False
                    logger.debug(f"Line {line_num}: Started parsing box '{box_name}'")
                elif line.startswith("## CONNECTIONS"):
                    if current_box: # Save the last box before switching section
                         current_box['code'] = "\n".join(code_buffer).strip()
                         parsed_data['boxes'].append(current_box)
                         current_box = None
                    current_section = "connections"
                    in_code_block = False
                    logger.debug(f"Line {line_num}: Switched to CONNECTIONS section")
                elif line.startswith("## VISUAL_LAYOUT"):
                     if current_box: # Save the last box before switching section
                         current_box['code'] = "\n".join(code_buffer).strip()
                         parsed_data['boxes'].append(current_box)
                         current_box = None
                     current_section = "layout"
                     in_code_block = False
                     logger.debug(f"Line {line_num}: Switched to VISUAL_LAYOUT section")
                elif line.startswith("##"): # Any other H2 resets section
                    if current_box: # Save the last box before switching section
                         current_box['code'] = "\n".join(code_buffer).strip()
                         parsed_data['boxes'].append(current_box)
                         current_box = None
                    current_section = None
                    in_code_block = False

                # Parsing within sections
                if current_section == "box" and current_box:
                    if line.startswith("**Inputs:**"):
                        inputs_str = line.removeprefix("**Inputs:**").strip()
                        # Simple split and strip for clean input lines like "input1, input2"
                        cleaned_inputs = [inp.strip() for inp in inputs_str.split(',') if inp.strip()]
                        current_box['inputs'] = cleaned_inputs
                        logger.debug(f"Line {line_num}: Found inputs for '{current_box['id']}': {current_box['inputs']}")
                    elif line.startswith("```python"):
                        in_code_block = True
                        code_buffer = [] # Reset buffer for new code block
                    elif line.startswith("```") and in_code_block:
                        in_code_block = False
                        # Code is processed when the next box starts or file ends
                    elif in_code_block:
                        # Append the original line, but maybe rstrip() to remove trailing whitespace?
                        # Let's keep the full original line for now to preserve all formatting.
                        code_buffer.append(original_line.rstrip('\n\r')) # Use original_line, remove only trailing newline
                    elif not line.startswith("##") and not in_code_block and not line.startswith("**Inputs:**") and not current_box.get('description'):
                         # Capture the first non-empty line after BOX as description (optional)
                         if line:
                             current_box['description'] = line
                             logger.debug(f"Line {line_num}: Found description for '{current_box['id']}': {line}")


                elif current_section == "connections":
                    # Example: source_box.output -> target_box.input_name
                    match = re.match(r"^\s*([\w_]+)\.output\s*->\s*([\w_]+)\.([\w_]+)\s*$", line)
                    if match:
                        source_box, target_box, target_input = match.groups()
                        connection = {'source': source_box, 'target': target_box, 'target_input': target_input}
                        parsed_data['connections'].append(connection)
                        logger.debug(f"Line {line_num}: Found connection: {source_box} -> {target_box}.{target_input}")
                    elif line:
                         logger.warning(f"Line {line_num}: Invalid connection format: '{line}'")

                elif current_section == "layout":
                    # Example: box_name: {"x": 100, "y": 100}
                    match = re.match(r"^\s*([\w_]+)\s*:\s*(\{.*?\})\s*$", line)
                    if match:
                        box_name, layout_json_str = match.groups()
                        try:
                            # Basic validation for json-like structure
                            layout_data = eval(layout_json_str) # Use eval carefully, assumes trusted input format
                            if isinstance(layout_data, dict) and 'x' in layout_data and 'y' in layout_data:
                                parsed_data['layout'][box_name] = {'x': int(layout_data['x']), 'y': int(layout_data['y'])}
                                logger.debug(f"Line {line_num}: Found layout for '{box_name}': {parsed_data['layout'][box_name]}")
                            else:
                                logger.warning(f"Line {line_num}: Invalid layout format for '{box_name}': {layout_json_str}")
                        except Exception as e:
                            logger.warning(f"Line {line_num}: Could not parse layout JSON for '{box_name}': {e}")
                    elif line:
                        logger.warning(f"Line {line_num}: Invalid layout line format: '{line}'")

            # Add the last parsed box if it exists
            if current_box:
                current_box['code'] = "\n".join(code_buffer).strip()
                parsed_data['boxes'].append(current_box)
                logger.debug(f"Finished parsing last box '{current_box['id']}'")

        logger.info(f"Successfully parsed {file_path}. Found {len(parsed_data['boxes'])} boxes, {len(parsed_data['connections'])} connections, {len(parsed_data['layout'])} layout entries.")

    except FileNotFoundError:
        logger.error(f"Markdown file not found: {file_path}")
        return {'boxes': [], 'connections': [], 'layout': {}} # Return empty structure
    except Exception as e:
        logger.exception(f"An unexpected error occurred while parsing {file_path}: {e}")
        return {'boxes': [], 'connections': [], 'layout': {}} # Return empty structure

    return parsed_data

if __name__ == '__main__':
    # Example Usage (requires a dummy workflow.md)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create a dummy workflow.md for testing
    dummy_md_content = """
## BOX: load_data
Loads the initial dataset.
**Inputs:** file_path
```python
import json

def execute(file_path):
    # Dummy implementation
    print(f"Loading data from {file_path}...")
    data = {"col1": [1, 2], "col2": [3, 4]}
    return {"dataframe": json.dumps(data)} # Return JSON string for simplicity
```

## BOX: process_data
Processes the loaded data.
**Inputs:** dataframe
```python
import json

def execute(dataframe):
    # Dummy implementation
    print("Processing data...")
    loaded_data = json.loads(dataframe)
    processed = {k: [v * 2 for v in vals] for k, vals in loaded_data.items()}
    return {"processed_data": json.dumps(processed)}
```

## CONNECTIONS
load_data.output -> process_data.dataframe

## VISUAL_LAYOUT
load_data: {"x": 100, "y": 50}
process_data: {"x": 300, "y": 50}
"""
    dummy_file_path = "temp_workflow_test.md"
    with open(dummy_file_path, "w", encoding="utf-8") as f:
        f.write(dummy_md_content)

    print(f"\n--- Parsing {dummy_file_path} ---")
    parsed = parse_markdown_file(dummy_file_path)
    print("\n--- Parsed Data ---")
    import json
    print(json.dumps(parsed, indent=2))

    # Clean up the dummy file
    import os
    os.remove(dummy_file_path)
    print(f"\n--- Cleaned up {dummy_file_path} ---")

    print("\n--- Testing with non-existent file ---")
    parse_markdown_file("non_existent_file.md")