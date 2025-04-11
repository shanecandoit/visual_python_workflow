import logging
import threading
import json # For callback data serialization
from typing import Callable, Dict, Any, Optional

# Assuming other modules are in the same directory or accessible via PYTHONPATH
import workflow_graph
import code_executor
from cache_manager import CacheManager # Import the class

logger = logging.getLogger(__name__)

# Define a type for the update callback function
# Arguments: box_id (str), status (str: 'running', 'success', 'error'), data (dict or None)
UpdateCallback = Callable[[str, str, Optional[Dict[str, Any]]], None]

class WorkflowRunner:
    """Orchestrates running the workflow or single boxes."""

    def __init__(self, graph_module, executor_module, cache_manager_instance: CacheManager):
        """
        Initializes the WorkflowRunner.

        Args:
            graph_module: The imported workflow_graph module.
            executor_module: The imported code_executor module.
            cache_manager_instance: An instance of the CacheManager.
        """
        self.graph_module = graph_module
        self.executor_module = executor_module
        self.cache = cache_manager_instance
        logger.info("WorkflowRunner initialized.")

    def run_workflow(self, graph: workflow_graph.GraphObject, update_callback: UpdateCallback) -> bool:
        """
        Runs the entire workflow sequentially based on dependencies.

        Args:
            graph: The workflow graph object (nx.DiGraph).
            update_callback: Function to call with status updates.

        Returns:
            True if the entire workflow completed successfully, False otherwise.
        """
        logger.info("Starting full workflow run.")
        overall_success = True
        self.cache.clear_cache() # Clear cache before a full run
        logger.debug("Cache cleared for full workflow run.")

        execution_order = self.graph_module.get_execution_order(graph)
        if execution_order is None:
            logger.error("Cannot run workflow: Failed to get execution order (check for cycles or graph errors).")
            # Send a general error update if possible? Or rely on graph module logs.
            # update_callback(None, "error", {"message": "Failed to determine execution order. Check logs."})
            return False

        logger.info(f"Execution order determined: {execution_order}")

        for box_id in execution_order:
            logger.info(f"--- Preparing box: {box_id} ---")
            update_callback(box_id, "running", None) # Notify UI that box is starting

            node_data = self.graph_module.get_node_data(graph, box_id)
            if not node_data:
                logger.error(f"Could not get node data for box '{box_id}'. Skipping.")
                update_callback(box_id, "error", {"message": f"Node data not found for {box_id}"})
                overall_success = False
                break # Stop workflow on critical error

            code_string = node_data.get('code')
            if not code_string:
                 logger.error(f"No code found for box '{box_id}'. Skipping.")
                 update_callback(box_id, "error", {"message": f"Code not found for {box_id}"})
                 overall_success = False
                 break

            # --- Gather inputs from cache using input_sources map ---
            input_data = {}
            # Get the mapping defined in the graph node data
            input_sources = node_data.get('input_sources', {})
            required_inputs = node_data.get('inputs', []) # Still useful to know what the box definition expects
            logger.debug(f"Box '{box_id}' requires inputs (defined in MD): {required_inputs}")
            logger.debug(f"Box '{box_id}' input sources (from connections): {input_sources}")

            inputs_met = True
            # Iterate through the sources defined by connections
            for target_input_name, source_box_id in input_sources.items():
                logger.debug(f"Attempting to gather input '{target_input_name}' for '{box_id}' from source '{source_box_id}'.")
                cached_output = self.cache.get_cached_output(source_box_id)

                if cached_output is None:
                    logger.error(f"Input '{target_input_name}' for '{box_id}' requires output from '{source_box_id}', but it's not in cache. Workflow cannot proceed reliably.")
                    update_callback(box_id, "error", {"message": f"Missing cached output from upstream box '{source_box_id}' for input '{target_input_name}'."})
                    inputs_met = False
                    break # Stop gathering inputs if one is missing

                # The connection source_box.output -> target_box.target_input_name means:
                # The 'execute' function of the target_box will receive an argument named 'target_input_name'.
                # The value of this argument should be the *entire output dictionary* from source_box.
                # The target_box's code is responsible for accessing the specific key(s) it needs from that dictionary.
                input_data[target_input_name] = cached_output
                logger.debug(f"Providing output of '{source_box_id}' as argument '{target_input_name}' for '{box_id}'. Value keys: {list(cached_output.keys())}")

            # Optional: Check if all required_inputs (from box definition) were actually supplied by connections
            if inputs_met:
                 supplied_inputs = set(input_sources.keys())
                 for req_input in required_inputs:
                     if req_input not in supplied_inputs:
                         logger.warning(f"Input '{req_input}' defined in box '{box_id}' was not supplied by any connection. Execution might fail if it's not optional.")
                         # We proceed anyway, assuming the execute function might handle optional args

            if not inputs_met: # If loop broke due to missing cache
                overall_success = False
                break # Stop workflow

            if not inputs_met:
                overall_success = False
                break # Stop workflow

            # --- Execute Code ---
            logger.debug(f"Executing box '{box_id}' with inputs: {list(input_data.keys())}")
            execution_result = self.executor_module.execute_code(box_id, code_string, input_data)

            # --- Process Result ---
            if execution_result.get('success'):
                logger.info(f"Box '{box_id}' executed successfully.")
                output_data = execution_result.get('output', {})
                self.cache.update_cache(box_id, output_data, input_data) # Cache result
                update_callback(box_id, "success", output_data) # Send success and output
            else:
                logger.error(f"Box '{box_id}' failed execution: {execution_result.get('error')}")
                update_callback(box_id, "error", {"message": execution_result.get('error', 'Unknown execution error')})
                overall_success = False
                break # Stop workflow on first failure

        if overall_success:
            logger.info("Workflow finished successfully.")
        else:
            logger.warning("Workflow finished with errors.")

        return overall_success


    def run_single_box(self, graph: workflow_graph.GraphObject, box_id: str, update_callback: UpdateCallback) -> bool:
        """
        Runs a single box using its previously cached inputs.

        Args:
            graph: The workflow graph object (nx.DiGraph).
            box_id: The ID of the box to run.
            update_callback: Function to call with status updates.

        Returns:
            True if the box executed successfully, False otherwise.
        """
        logger.info(f"Starting single box run for: {box_id}")
        update_callback(box_id, "running", None)

        node_data = self.graph_module.get_node_data(graph, box_id)
        if not node_data:
            logger.error(f"Could not get node data for box '{box_id}'. Cannot run.")
            update_callback(box_id, "error", {"message": f"Node data not found for {box_id}"})
            return False

        code_string = node_data.get('code')
        if not code_string:
             logger.error(f"No code found for box '{box_id}'. Cannot run.")
             update_callback(box_id, "error", {"message": f"Code not found for {box_id}"})
             return False

        # --- Get Cached Inputs ---
        # For single run, we use the inputs that were used the *last time this box succeeded*
        input_data = self.cache.get_cached_inputs(box_id)

        if input_data is None:
            logger.error(f"Cannot run single box '{box_id}': No cached inputs found. Run the full workflow or upstream dependencies first.")
            update_callback(box_id, "error", {"message": "No cached inputs available for single run."})
            return False

        logger.debug(f"Using cached inputs for box '{box_id}': {list(input_data.keys())}")

        # --- Execute Code ---
        execution_result = self.executor_module.execute_code(box_id, code_string, input_data)

        # --- Process Result ---
        if execution_result.get('success'):
            logger.info(f"Single box '{box_id}' executed successfully.")
            output_data = execution_result.get('output', {})
            # Re-cache the result using the *same inputs* it just ran with
            self.cache.update_cache(box_id, output_data, input_data)
            update_callback(box_id, "success", output_data)
            return True
        else:
            logger.error(f"Single box '{box_id}' failed execution: {execution_result.get('error')}")
            update_callback(box_id, "error", {"message": execution_result.get('error', 'Unknown execution error')})
            return False


# --- Example Usage ---
if __name__ == '__main__':
    import time
    import markdown_parser # Need parser for the example

    # Configure logger for example
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # Dummy update callback function for testing
    def dummy_callback(box_id, status, data):
        print(f"CALLBACK -> Box: {box_id}, Status: {status}, Data: {json.dumps(data) if data else 'None'}")
        # Add a small delay to simulate UI updates or work
        time.sleep(0.1)

    # --- Setup ---
    # Use the workflow.md created earlier
    workflow_file = "workflow.md"
    parsed_data = markdown_parser.parse_markdown_file(workflow_file)
    if not parsed_data or not parsed_data['boxes']:
        logger.error("Failed to parse workflow.md for example run. Exiting.")
        exit()

    graph = workflow_graph.build_graph(parsed_data)
    if not graph:
        logger.error("Failed to build graph for example run. Exiting.")
        exit()

    cache = CacheManager()
    runner = WorkflowRunner(workflow_graph, code_executor, cache)

    # --- Test Full Workflow Run ---
    print("\n" + "="*20 + " TESTING FULL WORKFLOW RUN " + "="*20)
    success = runner.run_workflow(graph, dummy_callback)
    print(f"Full workflow run result: {'Success' if success else 'Failed'}")
    print(f"Cache keys after full run: {cache.get_all_cache_keys()}")
    cached_sum_output = cache.get_cached_output('add_numbers')
    print(f"Cached output for 'add_numbers': {cached_sum_output}")

    # --- Test Single Box Run (using cached inputs) ---
    print("\n" + "="*20 + " TESTING SINGLE BOX RUN (add_numbers) " + "="*20)
    # Should use the inputs cached from the full run
    single_success = runner.run_single_box(graph, 'add_numbers', dummy_callback)
    print(f"Single box run result: {'Success' if single_success else 'Failed'}")
    new_cached_sum_output = cache.get_cached_output('add_numbers')
    print(f"Cached output for 'add_numbers' after single run: {new_cached_sum_output}")
    # Verify output is likely the same (unless random seed wasn't fixed, but inputs were cached)
    assert cached_sum_output == new_cached_sum_output if cached_sum_output else single_success is False


    # --- Test Single Box Run (no cached inputs) ---
    print("\n" + "="*20 + " TESTING SINGLE BOX RUN (generate_numbers - no inputs needed, but test cache miss) " + "="*20)
    cache.clear_cache('generate_numbers') # Ensure no cached inputs exist
    print("Cleared cache for generate_numbers")
    single_gen_success = runner.run_single_box(graph, 'generate_numbers', dummy_callback)
    # This should FAIL because run_single_box REQUIRES cached inputs, even if the function takes none.
    print(f"Single box run result (generate_numbers): {'Success' if single_gen_success else 'Failed'}")
    assert single_gen_success is False # Expect failure due to missing cached inputs


    print("\n" + "="*20 + " EXAMPLE FINISHED " + "="*20)