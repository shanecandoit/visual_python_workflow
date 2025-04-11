import networkx as nx
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Define type aliases for clarity
GraphObject = nx.DiGraph
ParsedData = Dict[str, Any]
NodeData = Dict[str, Any]
ConnectionInfo = Dict[str, str]

def build_graph(parsed_data: ParsedData) -> Optional[GraphObject]:
    """
    Builds a directed graph from parsed Markdown data.

    Args:
        parsed_data: The dictionary output from markdown_parser.parse_markdown_file.

    Returns:
        A networkx.DiGraph object representing the workflow, or None if input is invalid.
    """
    if not parsed_data or 'boxes' not in parsed_data or 'connections' not in parsed_data:
        logger.error("Invalid parsed_data received for building graph.")
        return None

    graph = nx.DiGraph()
    box_ids = set()

    # Add nodes (boxes)
    # Add nodes first, initialize input_sources
    for box in parsed_data.get('boxes', []):
        box_id = box.get('id')
        if not box_id:
            logger.warning("Found a box without an ID in parsed_data. Skipping.")
            continue
        if box_id in graph: # Use graph.has_node or 'in'
             logger.warning(f"Duplicate box ID '{box_id}' found. Overwriting node data.")
        # Initialize input_sources map for each node
        box_data = box.copy() # Avoid modifying original parsed_data dict
        box_data['input_sources'] = {}
        # Store all box data (including input_sources) as node attributes
        graph.add_node(box_id, **box_data)
        # box_ids set is no longer needed as we check 'in graph'
        logger.debug(f"Added node '{box_id}' to graph with data: {box}")

    # Add edges (connections)
    for connection in parsed_data.get('connections', []):
        source = connection.get('source')
        target = connection.get('target')
        target_input = connection.get('target_input')

        if not all([source, target, target_input]):
            logger.warning(f"Invalid connection format found: {connection}. Skipping.")
            continue

        if source not in graph: # Check graph directly
            logger.error(f"Connection source '{source}' not found in defined boxes. Skipping edge.")
            continue
        if target not in graph: # Check graph directly
            logger.error(f"Connection target '{target}' not found in defined boxes. Skipping edge.")
            continue

        # Check if target box actually expects the target_input (still useful warning)
        target_node_data = graph.nodes[target] # Get the node data we just added/updated
        if target_input not in target_node_data.get('inputs', []):
             logger.warning(f"Connection target '{target}' does not list '{target_input}' as an input in its definition. Check workflow definition.")

        # Store the input source mapping on the *target* node
        target_node_data['input_sources'][target_input] = source
        logger.debug(f"Mapped input '{target_input}' of node '{target}' to source '{source}'")

        # Add a simple edge for dependency, no attributes needed here
        graph.add_edge(source, target)
        logger.debug(f"Added edge from '{source}' to '{target}' (input: '{target_input}')")

    logger.info(f"Graph built successfully with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    return graph

def get_execution_order(graph: GraphObject) -> Optional[List[str]]:
    """
    Performs a topological sort to get the execution order of boxes.

    Args:
        graph: The networkx.DiGraph object.

    Returns:
        A list of box IDs in execution order, or None if the graph has cycles.
    """
    if not isinstance(graph, nx.DiGraph):
        logger.error("Invalid graph object provided to get_execution_order.")
        return None

    if not nx.is_directed_acyclic_graph(graph):
        cycles = list(nx.simple_cycles(graph))
        logger.error(f"Workflow graph contains cycles! Cannot determine execution order. Cycles found: {cycles}")
        return None

    try:
        # Topological sort gives an iterator of nodes in order
        execution_order = list(nx.topological_sort(graph))
        logger.info(f"Determined execution order: {execution_order}")
        return execution_order
    except nx.NetworkXUnfeasible as e:
        # This shouldn't happen if is_directed_acyclic_graph passed, but handle defensively
        logger.error(f"Could not determine execution order (unexpected error): {e}")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred during topological sort: {e}")
        return None


def get_node_data(graph: GraphObject, box_id: str) -> Optional[NodeData]:
    """
    Retrieves the data associated with a specific node (box).

    Args:
        graph: The networkx.DiGraph object.
        box_id: The ID of the box (node) to retrieve data for.

    Returns:
        A dictionary containing the node's attributes, or None if the node doesn't exist.
    """
    if not isinstance(graph, nx.DiGraph):
        logger.error("Invalid graph object provided to get_node_data.")
        return None
    if box_id not in graph:
        logger.error(f"Node '{box_id}' not found in the graph.")
        return None

    try:
        node_data = graph.nodes[box_id]
        logger.debug(f"Retrieved data for node '{box_id}': {node_data}")
        return node_data
    except Exception as e:
        logger.exception(f"An unexpected error occurred while retrieving data for node '{box_id}': {e}")
        return None

def get_upstream_connections(graph: GraphObject, box_id: str) -> List[ConnectionInfo]:
    """
    Finds all incoming connections (dependencies) for a given box.

    Args:
        graph: The networkx.DiGraph object.
        box_id: The ID of the box (node) whose upstream connections are needed.

    Returns:
        A list of dictionaries, each representing an incoming connection
        with 'source_box' and 'target_input' keys. Returns empty list if node
        doesn't exist or has no incoming edges.
    """
    connections = []
    if not isinstance(graph, nx.DiGraph):
        logger.error("Invalid graph object provided to get_upstream_connections.")
        return connections
    if box_id not in graph:
        logger.error(f"Node '{box_id}' not found in the graph for upstream connection check.")
        return connections

    try:
        for u, v, data in graph.in_edges(box_id, data=True):
            # u is the source_box, v is the target_box (box_id)
            # data contains edge attributes, including 'target_input'
            target_input = data.get('target_input')
            if target_input:
                connection_info = {'source_box': u, 'target_input': target_input}
                connections.append(connection_info)
                logger.debug(f"Found upstream connection for '{box_id}': {connection_info}")
            else:
                logger.warning(f"Edge from '{u}' to '{box_id}' is missing 'target_input' attribute.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred while getting upstream connections for '{box_id}': {e}")

    return connections


if __name__ == '__main__':
    # Example Usage (requires markdown_parser and a dummy workflow)
    import markdown_parser
    import os
    import json

    # Configure logger for example
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # Use the same dummy workflow from markdown_parser example
    dummy_md_content = """
## BOX: load_data
Loads the initial dataset.
**Inputs:** file_path
```python
def execute(file_path):
    print(f"Loading data from {file_path}...")
    data = {"col1": [1, 2], "col2": [3, 4]}
    return {"dataframe": json.dumps(data)}
```

## BOX: process_data
Processes the loaded data.
**Inputs:** dataframe
```python
import json
def execute(dataframe):
    print("Processing data...")
    loaded_data = json.loads(dataframe)
    processed = {k: [v * 2 for v in vals] for k, vals in loaded_data.items()}
    return {"processed_data": json.dumps(processed)}
```

## BOX: summarize_data
Summarizes processed data.
**Inputs:** processed_data
```python
import json
def execute(processed_data):
    print("Summarizing data...")
    loaded_data = json.loads(processed_data)
    summary = {"count": len(loaded_data.get("col1", []))}
    return {"summary": json.dumps(summary)}
```

## CONNECTIONS
load_data.output -> process_data.dataframe
process_data.output -> summarize_data.processed_data

## VISUAL_LAYOUT
load_data: {"x": 100, "y": 50}
process_data: {"x": 300, "y": 50}
summarize_data: {"x": 500, "y": 50}
"""
    dummy_file_path = "temp_workflow_graph_test.md"
    with open(dummy_file_path, "w", encoding="utf-8") as f:
        f.write(dummy_md_content)

    print(f"\n--- Parsing {dummy_file_path} ---")
    parsed = markdown_parser.parse_markdown_file(dummy_file_path)

    if parsed and parsed['boxes']: # Check if parsing was successful
        print("\n--- Building Graph ---")
        workflow_graph = build_graph(parsed)

        if workflow_graph:
            print(f"\nGraph Nodes: {list(workflow_graph.nodes(data=True))}")
            print(f"Graph Edges: {list(workflow_graph.edges(data=True))}")

            print("\n--- Getting Execution Order ---")
            order = get_execution_order(workflow_graph)
            print(f"Execution Order: {order}")

            if order:
                print("\n--- Getting Node Data (process_data) ---")
                node_info = get_node_data(workflow_graph, 'process_data')
                print(json.dumps(node_info, indent=2))

                print("\n--- Getting Upstream Connections (process_data) ---")
                upstream = get_upstream_connections(workflow_graph, 'process_data')
                print(upstream)

                print("\n--- Getting Upstream Connections (summarize_data) ---")
                upstream_summary = get_upstream_connections(workflow_graph, 'summarize_data')
                print(upstream_summary)

                print("\n--- Getting Upstream Connections (load_data) ---")
                upstream_load = get_upstream_connections(workflow_graph, 'load_data')
                print(upstream_load) # Should be empty
        else:
            print("Failed to build graph.")
    else:
        print("Failed to parse markdown file.")


    # Clean up the dummy file
    os.remove(dummy_file_path)
    print(f"\n--- Cleaned up {dummy_file_path} ---")

    # Example with cycle
    cyclic_md_content = """
## BOX: A
**Inputs:** input_b
```python
def execute(input_b): return {"out_a": 1}
```
## BOX: B
**Inputs:** input_a
```python
def execute(input_a): return {"out_b": 2}
```
## CONNECTIONS
A.output -> B.input_a
B.output -> A.input_b
"""
    cyclic_file_path = "temp_cyclic_test.md"
    with open(cyclic_file_path, "w", encoding="utf-8") as f:
        f.write(cyclic_md_content)

    print(f"\n--- Parsing {cyclic_file_path} ---")
    parsed_cyclic = markdown_parser.parse_markdown_file(cyclic_file_path)
    if parsed_cyclic and parsed_cyclic['boxes']:
        print("\n--- Building Cyclic Graph ---")
        cyclic_graph = build_graph(parsed_cyclic)
        if cyclic_graph:
            print("\n--- Getting Execution Order (Cyclic) ---")
            order_cyclic = get_execution_order(cyclic_graph) # Should log error and return None
            print(f"Execution Order (Cyclic): {order_cyclic}")
        else:
            print("Failed to build cyclic graph.")
    else:
        print("Failed to parse cyclic markdown file.")

    os.remove(cyclic_file_path)
    print(f"\n--- Cleaned up {cyclic_file_path} ---")