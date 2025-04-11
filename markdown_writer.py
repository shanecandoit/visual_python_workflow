import json
import logging
import os

logger = logging.getLogger(__name__)

def write_markdown_file(file_path, parsed_data):
    """
    Writes the parsed data structure back to a Markdown file.
    
    Args:
        file_path: The path to the Markdown file to write
        parsed_data: Dictionary containing the workflow data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure we have the minimum required data
        if not parsed_data or 'boxes' not in parsed_data:
            logger.error("Cannot write markdown: Missing required data")
            return False
            
        # Create backup of the original file
        backup_path = f"{file_path}.bak"
        try:
            if os.path.exists(file_path):
                import shutil
                shutil.copy2(file_path, backup_path)
                logger.info(f"Created backup at {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            
        # Start building the markdown content
        md_content = []
        
        # Add metadata section if it exists
        if 'metadata' in parsed_data:
            md_content.append("---")
            for key, value in parsed_data['metadata'].items():
                md_content.append(f"{key}: {value}")
            md_content.append("---\n")
            
        # Add layout as a JSON comment if it exists
        if 'layout' in parsed_data and parsed_data['layout']:
            layout_json = json.dumps(parsed_data['layout'], indent=2)
            md_content.append("<!-- Layout")
            md_content.append(layout_json)
            md_content.append("-->\n")
            
        # Add boxes
        for box in parsed_data['boxes']:
            # Handle required fields
            box_id = box.get('id', 'unknown')
            code = box.get('code', '')
            
            md_content.append(f"## {box_id}")
            md_content.append("```python")
            md_content.append(code)
            md_content.append("```\n")
            
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
            
        logger.info(f"Successfully wrote markdown to {file_path}")
        return True
            
    except Exception as e:
        logger.exception(f"Error writing markdown file: {e}")
        return False