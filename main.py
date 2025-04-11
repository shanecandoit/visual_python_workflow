import webview
import threading
import json
import logging
import os
from typing import Optional, Dict, Any

# Import project modules
import logger_config
import markdown_parser
import workflow_graph
import code_executor
from cache_manager import CacheManager
from workflow_runner import WorkflowRunner, UpdateCallback # Import class and type alias
from markdown_writer import write_markdown_file

# Setup logger first
logger = logger_config.setup_logger(logging.INFO)

class Api:
    """
    API class exposed to the JavaScript frontend via pywebview.
    Handles requests from the frontend and calls the appropriate backend logic.
    """
    def __init__(self, parser, graph_module, cache, runner, window_ref_func, update_callback_func):
        # Store components directly, avoid passing controller
        self.parser = parser
        self.graph_module = graph_module
        self.cache = cache
        self.runner = runner
        self._get_window = window_ref_func # Function to get window object later
        self._update_callback = update_callback_func # Function to send updates to JS
        self._graph = None # Internal storage for the current graph
        logger.debug("Refactored API class initialized.")

    def ping(self) -> str:
        """Simple test function for the API bridge."""
        logger.info("API received ping request.")
        return "pong"

    def load_workflow(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Loads and parses a workflow file, storing the graph internally."""
        logger.info(f"API received request to load workflow: {file_path}")
        if not file_path or not isinstance(file_path, str):
            logger.error("Invalid file path received from frontend.")
            return {"error": "Invalid file path provided."}

        try:
            parsed_data = self.parser.parse_markdown_file(file_path)
            if not parsed_data or 'boxes' not in parsed_data:
                logger.error(f"Failed to parse Markdown file: {file_path}")
                return {"error": f"Failed to parse {os.path.basename(file_path)}."}

            graph = self.graph_module.build_graph(parsed_data)
            if not graph:
                logger.error("Failed to build graph from parsed data.")
                return {"error": "Failed to build workflow graph from the Markdown file."}

            self._graph = graph # Store graph internally in API instance
            self.current_workflow_path = file_path  # Store the path for future use
            logger.info(f"Stored graph internally in API. Nodes: {self._graph.number_of_nodes()}, Edges: {self._graph.number_of_edges()}")

            self.cache.clear_cache()
            logger.info("Cache cleared for newly loaded workflow.")

            nodes_for_js = [{'id': node_id, **data} for node_id, data in graph.nodes(data=True)]
            edges_for_js = [{'source': u, 'target': v, **data} for u, v, data in graph.edges(data=True)]
            layout_for_js = parsed_data.get('layout', {})

            response = {
                "success": True,
                "nodes": nodes_for_js,
                "edges": edges_for_js,
                "layout": layout_for_js
            }
            logger.debug("Prepared graph data for frontend.")
            return response
        
        except Exception as e:
            logger.exception(f"Error during workflow loading: {e}")
            return {"error": f"An unexpected error occurred: {e}"}

    def request_run_all(self):
        """Triggers a full workflow run using the stored graph and runner."""
        logger.info("API received request to run all.")
        if not self._graph:
            logger.warning("Run all requested but no graph is loaded.")
            return {"error": "No workflow loaded."}

        # Run in a separate thread, calling the runner directly
        threading.Thread(
            target=self.runner.run_workflow,
            args=(self._graph, self._update_callback), # Pass stored graph and callback
            daemon=True
        ).start()
        return {"status": "Workflow run requested."}


    def request_run_single(self, box_id: str):
        """Called by JS to trigger a single box run."""
        logger.info(f"API received request to run single box: {box_id}")
        if not self._graph:
            logger.warning("Run single requested but no graph is loaded.")
            return {"error": "No workflow loaded."}
        if not box_id or not isinstance(box_id, str):
            logger.error(f"Invalid box_id received for single run: {box_id}")
            return {"error": "Invalid box ID provided."}

        # Run in a separate thread
        # Run in a separate thread, calling the runner directly
        threading.Thread(
            target=self.runner.run_single_box,
            args=(self._graph, box_id, self._update_callback),
            daemon=True
        ).start()
        return {"status": f"Single run requested for box '{box_id}'."}

    def get_cached_data(self, box_id: str) -> Optional[Dict[str, Any]]:
        """Called by JS to get cached output for a specific box."""
        logger.debug(f"API received request for cached data for box: {box_id}")
        if not box_id or not isinstance(box_id, str):
             logger.error(f"Invalid box_id received for getting cache: {box_id}")
             return None # Or return an error object?

        # Use self.cache directly (already correct from previous diff)
        cached_output = self.cache.get_cached_output(box_id) # Already correct
        # Return the output directly, JS will handle None case
        return cached_output

    def get_absolute_path(self, relative_path: str) -> Optional[str]:
        """Converts a relative path (to main.py) to an absolute path."""
        try:
            base_dir = os.path.dirname(__file__)
            abs_path = os.path.abspath(os.path.join(base_dir, relative_path))
            logger.debug(f"Resolved '{relative_path}' to '{abs_path}'")
            # Basic check if it exists, helps debugging but not strictly necessary
            # if not os.path.exists(abs_path):
            #     logger.warning(f"Resolved path does not seem to exist: {abs_path}")
            return abs_path
        except Exception as e:
            logger.exception(f"Error resolving path '{relative_path}': {e}")
            return None

    def request_file_dialog(self) -> Optional[str]:
        """Called by JS to open a native file dialog."""
        logger.debug("API received request to open file dialog.")
        try:
            window = self._get_window() # Get window via lambda
            if not window:
                logger.error("Cannot open file dialog: Window reference not available.")
                return None
            result = window.create_file_dialog( # Call method on window object
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=('Markdown Files (*.md)',)
            )
            logger.info(f"File dialog returned: {result}")
            return result[0] if result else None
        except Exception as e:
            logger.exception(f"Error opening file dialog: {e}")
            return None
    
    def save_workflow_layout(self, layout):
        """Save the updated workflow layout to persistent storage."""
        # This is broken right now, fix it later
        return
        try:
            if not hasattr(self, '_graph') or not self._graph:
                return {"success": False, "error": "No workflow is currently loaded"}
            
            # Track where the current workflow came from
            workflow_path = getattr(self, 'current_workflow_path', None)
            if not workflow_path:
                return {"success": False, "error": "Current workflow path unknown"}
            
            try:
                # Parse the existing file to get the full content
                parsed_data = self.parser.parse_markdown_file(workflow_path)
                if not parsed_data:
                    return {"success": False, "error": "Could not parse current workflow file"}
                
                # Update the layout in the parsed data
                parsed_data['layout'] = layout
                
                # Write back to the file using the imported write_markdown_file function
                success = write_markdown_file(workflow_path, parsed_data)
                
                if success:
                    logger.info(f"Successfully saved layout to {workflow_path}")
                    return {"success": True}
                else:
                    return {"success": False, "error": "Failed to write updated layout to file"}
            except ImportError as e:
                logger.warning(f"markdown_writer module error: {e}")
                # At least store in memory for this session
                if not hasattr(self, 'current_workflow_path'):
                    self.current_workflow_path = workflow_path
                return {"success": True, "warning": "Layout saved in memory only, not persisted to file"}
        except Exception as e:
            logger.exception(f"Error saving workflow layout: {e}")
            return {"success": False, "error": str(e)}


class MainController:
    """Holds the main application state and orchestrates components."""
    def __init__(self):
        self.graph: Optional[workflow_graph.GraphObject] = None
        self.parser = markdown_parser # Use the module directly for its functions
        self.executor = code_executor # Use the module directly
        self.cache = CacheManager()
        self.graph_module = workflow_graph # Keep reference to the module
        self.runner = WorkflowRunner(self.graph_module, self.executor, self.cache)
        self.window: Optional[webview.Window] = None
        logger.info("MainController initialized.")

    def _send_update_to_js(self, box_id: str, status: str, data: Optional[Dict[str, Any]]):
        """Safely sends status updates to the JavaScript frontend."""
        if not self.window:
            logger.warning("Cannot send update to JS: Window not available.")
            return

        try:
            # Ensure data is JSON serializable before sending
            # Convert non-serializable items or handle errors gracefully
            js_data_string = "null" # Default to null if data is None or empty
            if data:
                try:
                    # Use default=str to handle potential non-serializable types crudely
                    js_data_string = json.dumps(data, default=str)
                except TypeError as json_error:
                    logger.warning(f"Data for box '{box_id}' status '{status}' is not JSON serializable: {json_error}. Sending error message instead.")
                    error_data = {"error": f"Result data not JSON serializable: {json_error}"}
                    js_data_string = json.dumps(error_data)
                    status = "error" # Mark status as error if data couldn't be sent

            # Escape backticks, backslashes, and ${} sequences for JS template literal safety
            safe_box_id = box_id.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
            safe_status = status.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
            # js_data_string is already JSON, which is safe for JS eval

            js_command = f'window.app.updateNodeStatus(`{safe_box_id}`, `{safe_status}`, {js_data_string});'
            logger.debug(f"Sending JS command: {js_command}")
            self.window.evaluate_js(js_command)

        except Exception as e:
            # Catch potential errors during JS evaluation (e.g., window closed)
            logger.exception(f"Failed to send update to JS for box '{box_id}': {e}")

    def run_full_workflow_async(self):
        """Runs the full workflow in the background."""
        if not self.graph:
            logger.error("Attempted to run full workflow, but no graph is loaded.")
            return
        logger.info("Starting asynchronous full workflow run...")
        self.runner.run_workflow(self.graph, self._send_update_to_js)
        logger.info("Asynchronous full workflow run finished.")

    def run_single_box_async(self, box_id: str):
        """Runs a single box in the background."""
        if not self.graph:
            logger.error(f"Attempted to run single box '{box_id}', but no graph is loaded.")
            return
        logger.info(f"Starting asynchronous single run for box '{box_id}'...")
        self.runner.run_single_box(self.graph, box_id, self._send_update_to_js)
        logger.info(f"Asynchronous single run for box '{box_id}' finished.")


# Direct ping function removed, Api class will be used

def main():
    """Main function to initialize and start the application."""
    logger.info("Application starting...")

    # Restore Controller and Api class instantiation
    controller = MainController()
    # Pass components to Api, including lambdas for window and callback
    api_instance = Api(
        parser=controller.parser,
        graph_module=controller.graph_module,
        cache=controller.cache,
        runner=controller.runner,
        window_ref_func=lambda: controller.window,
        update_callback_func=controller._send_update_to_js # Pass the callback method
    )

    # Determine path to frontend files (assuming 'frontend' is in the same dir as main.py)
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    index_html_path = os.path.join(frontend_dir, 'index.html')

    # Check if index.html exists
    if not os.path.exists(index_html_path):
        logger.critical(f"Frontend entry point not found: {index_html_path}")
        print(f"Error: Frontend file not found at {index_html_path}. Cannot start application.")
        return # Exit if frontend is missing

    # Create the pywebview window
    try:
        controller.window = webview.create_window( # Assign to controller.window
            'Python Markdown Workflow Visualizer',
            f'file:///{index_html_path}', # Use file:// protocol
            js_api=api_instance, # Pass the Api class instance
            width=1200,
            height=800,
            resizable=True,
            confirm_close=True # Ask user before closing
        )
        logger.info("pywebview window created.")
        # Assign window to controller instance
        # (This line was modified above, just removing the old comment placeholder)

        # Start the pywebview event loop
        webview.start(debug=True) # debug=True enables right-click inspect element

    except Exception as e:
        logger.critical(f"Failed to create or start pywebview window: {e}", exc_info=True)
        print(f"Fatal Error: Could not start the application window. Error: {e}")

    logger.info("Application finished.")


if __name__ == '__main__':
    main()