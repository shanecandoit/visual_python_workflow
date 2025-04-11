
Okay, let's outline a detailed plan focusing on simplicity and using Python `pywebview` with vanilla JS and a dark Bootstrap theme.

**Project Goal:** Create a desktop application using `pywebview` to visualize and run Python workflows defined in a Markdown file.

**Core Technologies:**

* **Backend/Logic:** Python 3.x
* **Frontend:** HTML, Vanilla JavaScript, Bootstrap 5 (Dark Theme)
* **Bridge:** `pywebview` (allows calling Python from JS and JS from Python)
* **Workflow Definition:** Custom Markdown format

**Project Structure (Simple):**

```
workflow-app/
├── main.py                 # Main application entry point, pywebview setup
├── markdown_parser.py      # Parses the workflow.md file
├── workflow_graph.py       # Builds and manages the workflow graph (using NetworkX implicitly)
├── code_executor.py        # Executes Python code snippets from boxes
├── cache_manager.py        # Handles caching of box inputs/outputs
├── workflow_runner.py      # Orchestrates running the workflow or single boxes
├── logger_config.py        # Basic logging setup
├── workflow.md             # Example workflow definition file
└── frontend/
    ├── index.html          # Main HTML file for the UI
    ├── app.js              # Frontend JavaScript logic
    └── style.css           # Custom CSS (optional, primarily Bootstrap)
```

---

**Phase 1: Core Python Logic & Setup**

**1. `logger_config.py`**

* **Responsibility:** Configure basic logging.
* **Methods:**
    * `setup_logger()`: Configures a logger (e.g., `logging.basicConfig`) to output INFO level messages to the console with a simple format (timestamp, level, message). Returns the logger instance.

**2. `markdown_parser.py`**

* **Responsibility:** Parse the `workflow.md` file according to the defined structure.
* **Methods:**
    * `parse_markdown_file(file_path: str) -> dict`:
        * Reads the content of the specified Markdown file.
        * Uses regex or string manipulation to find `## BOX:`, `## CONNECTIONS`, `## VISUAL_LAYOUT` sections.
        * Extracts box details (name, description, input names list, code string).
        * Extracts connection pairs (`source_box.output -> target_box.input_name`).
        * Extracts layout info (`box_name: {x: val, y: val}`).
        * Returns a dictionary like: `{'boxes': [{'id': 'box_name', 'code': '...', 'inputs': ['in1'], ...}], 'connections': [{'source': 'box_a', 'target': 'box_b', 'target_input': 'in1'}], 'layout': {'box_name': {'x': ..., 'y': ...}}}`. Logs progress and potential parsing errors.

**3. `workflow_graph.py`**

* **Responsibility:** Represent the workflow structure and dependencies.
* **Methods:**
    * `build_graph(parsed_data: dict) -> object`:
        * Takes the dictionary from `parse_markdown_file`.
        * Creates a graph representation (e.g., using `networkx.DiGraph` is highly recommended, even if kept internal to this module).
        * Adds nodes (boxes) with their data (code, inputs) as attributes.
        * Adds edges based on the connections. Logs graph details.
        * Returns the graph object.
    * `get_execution_order(graph: object) -> list`:
        * Performs a topological sort on the graph.
        * Returns a list of box IDs in the order they should be executed. Logs the order or errors (e.g., cycles).
    * `get_node_data(graph: object, box_id: str) -> dict`:
        * Retrieves the attributes (code, input names, etc.) stored for a given node in the graph.
    * `get_upstream_connections(graph: object, box_id: str) -> list`:
        * Finds all incoming edges to `box_id`.
        * Returns a list of tuples/dicts like `[{'source_box': 'box_a', 'target_input': 'in1'}, ...]`.

**4. `code_executor.py`**

* **Responsibility:** Execute a single box's Python code safely.
* **Methods:**
    * `execute_code(box_id: str, code_string: str, input_data_dict: dict) -> dict`:
        * Logs the execution attempt with box ID and input keys.
        * Constructs a temporary execution namespace.
        * Uses `exec(code_string, temp_namespace)` to define the `execute` function within that namespace.
        * Calls `result = temp_namespace['execute'](**input_data_dict)`.
        * **Crucially:** Validates that `result` is a dictionary with string keys (JSON serializable).
        * Logs success and the output keys, or logs the specific exception if execution fails.
        * Returns `{'success': True, 'output': result}` or `{'success': False, 'error': str(exception)}`. Catches exceptions during exec or function call.

**5. `cache_manager.py`**

* **Responsibility:** In-memory caching of box inputs and outputs.
* **Data:** Internal dictionary `_cache = {}` structured as `{'box_id': {'output': {...}, 'inputs': {...}}}`.
* **Methods:**
    * `get_cached_output(box_id: str) -> dict | None`: Returns output for `box_id` or `None`. Logs cache hit/miss.
    * `get_cached_inputs(box_id: str) -> dict | None`: Returns the *inputs* that led to the cached output for `box_id` or `None`. Logs cache hit/miss.
    * `update_cache(box_id: str, output_data: dict, input_data: dict)`: Stores/updates the output and corresponding inputs for `box_id`. Logs the update.
    * `clear_cache(box_id: str | None = None)`: Clears cache for a specific box or all boxes if `box_id` is `None`. Logs the action.

**Phase 2: Workflow Orchestration & Main Application**

**6. `workflow_runner.py`**

* **Responsibility:** Manage the execution flow using other components.
* **Dependencies:** Needs instances of `code_executor`, `cache_manager`, and `workflow_graph` utilities. Needs a way to send updates back (callback function).
* **Methods:**
    * `run_workflow(graph: object, executor: object, cache: object, update_callback: callable)`:
        * Logs start of full workflow run. Calls `cache.clear_cache()`.
        * Gets execution order from `workflow_graph.get_execution_order`.
        * Iterates through `box_id` in order:
            * Gets upstream connections using `workflow_graph.get_upstream_connections`.
            * Builds `input_data` dict by fetching required inputs from `cache.get_cached_output` (outputs of upstream nodes).
            * Gets node data (code) using `workflow_graph.get_node_data`.
            * Calls `executor.execute_code(box_id, code, input_data)`.
            * Calls `update_callback(box_id, status, result)` to send progress to UI.
            * If successful, calls `cache.update_cache(box_id, result['output'], input_data)`.
            * If fails, logs error, potentially stops, calls callback with error status.
        * Logs end of workflow run. Returns overall status.
    * `run_single_box(graph: object, executor: object, cache: object, box_id: str, update_callback: callable)`:
        * Logs start of single box run for `box_id`.
        * Gets `input_data` from `cache.get_cached_inputs(box_id)`. If not found, logs error and returns failure status via callback.
        * Gets node data (code).
        * Calls `executor.execute_code(box_id, code, input_data)`.
        * Calls `update_callback(box_id, status, result)`.
        * If successful, calls `cache.update_cache(box_id, result['output'], input_data)`.
        * Logs end of single box run. Returns status.

**7. `main.py`**

* **Responsibility:** Entry point, `pywebview` setup, Python<->JS communication bridge.
* **Internal State:** Holds the current workflow graph, instances of runner, cache, executor.
* **API Class (for JS):** Define an internal class `Api`:
    * `def __init__(self, main_controller): self.main = main_controller`
    * `load_workflow(self, file_path: str) -> dict`: Calls parser, builds graph (stores graph in `main_controller`), clears cache, logs action. Returns initial graph structure (nodes, edges, layout) for JS rendering. Handles errors.
    * `request_run_all(self)`: Logs request. Triggers `main_controller.run_full_workflow_async()` (runs in a separate thread to avoid blocking UI).
    * `request_run_single(self, box_id: str)`: Logs request. Triggers `main_controller.run_single_box_async(box_id)` (runs in a thread).
    * `get_cached_data(self, box_id: str) -> dict | None`: Logs request. Calls `cache_manager.get_cached_output(box_id)`.
* **Main Controller Logic:**
    * Holds instances: `self.graph`, `self.parser`, `self.executor`, `self.cache`, `self.runner`, `self.logger`, `self.window` (pywebview window).
    * `run_full_workflow_async()`: Runs `self.runner.run_workflow` in a `threading.Thread`, passing `self._send_update_to_js` as the callback.
    * `run_single_box_async(box_id)`: Runs `self.runner.run_single_box` in a `threading.Thread`, passing `self._send_update_to_js`.
    * `_send_update_to_js(self, box_id, status, data)`: Uses `self.window.evaluate_js(f'updateNodeStatus("{box_id}", "{status}", {json.dumps(data)})')` to send data/status to the frontend JS. Handles potential JSON serialization issues. Logs the update being sent.
* **`main()` function:**
    * Calls `logger_config.setup_logger()`.
    * Instantiates core components (parser, executor, cache, runner).
    * Instantiates the main controller.
    * Instantiates the `Api` class, passing the controller.
    * Creates the `pywebview` window: `window = webview.create_window('Workflow App', 'frontend/index.html', js_api=api_instance)`. Stores window in controller.
    * Starts `pywebview`: `webview.start(debug=True)` (debug=True enables right-click inspect).

**Phase 3: Frontend Development**

**8. `frontend/index.html`**

* **Structure:** Basic HTML5 boilerplate.
* **CSS:** Link to Bootstrap 5 CSS (CDN or local, dark theme). Link to `style.css`.
* **Layout:** Use Bootstrap containers, rows, columns.
    * Header/Navbar (optional, maybe just a title).
    * Main area:
        * A container div where the graph will be rendered (e.g., `<div id="workflow-canvas"></div>`).
        * A sidebar or panel to show selected node info/cached data (`<div id="node-details"></div>`).
        * Control buttons (`<button id="load-button">Load MD</button>`, `<button id="run-all-button">Run All</button>`, `<button id="run-selected-button">Run Selected</button>`). (Initially disable run buttons).
* **JS:** Link to `app.js` at the bottom of `<body>`.

**9. `frontend/style.css`**

* **Optional:** Add custom styles for nodes, edges, highlighting, canvas background if Bootstrap isn't sufficient.

**10. `frontend/app.js`**

* **Global State:** `let currentWorkflow = null; let selectedNodeId = null;`
* **Initialization (`window.addEventListener('pywebviewready', init);`):**
    * `init()`: Get references to DOM elements (canvas, buttons, details panel). Add event listeners to buttons. Log JS readiness.
* **Event Handlers:**
    * `handleLoadClick()`: (Needs file input or uses `pywebview`'s file dialog API) Gets file path, calls `pywebview.api.load_workflow(filePath).then(renderGraph).catch(showError);`.
    * `handleRunAllClick()`: Disables button, shows loading state. Calls `pywebview.api.request_run_all()`.
    * `handleRunSingleClick()`: If `selectedNodeId` is set, calls `pywebview.api.request_run_single(selectedNodeId)`.
* **Core Functions:**
    * `renderGraph(workflowData)`:
        * Stores `workflowData` in `currentWorkflow`. Clears the canvas.
        * Iterates through `workflowData.boxes` and `workflowData.layout` to draw nodes (simple `<div>` elements positioned absolutely within the canvas). Add data attributes (`data-box-id`). Add click listeners (`handleNodeClick`).
        * Iterates through `workflowData.connections` to draw edges (can use SVG lines or a library like `jsPlumb` or simple CSS lines if layout is grid-like).
        * Enables run buttons. Logs rendering completion.
    * `handleNodeClick(event)`: Gets `box_id` from `event.target.dataset.boxId`. Sets `selectedNodeId`. Updates UI to highlight the selected node. Calls `pywebview.api.get_cached_data(box_id).then(displayNodeDetails);`. Enables "Run Selected" button.
    * `displayNodeDetails(cachedData)`: Updates the `#node-details` panel with formatted JSON output.
    * `updateNodeStatus(box_id, status, data)`: **(Called BY Python)** Finds the node div by `box_id`. Updates its visual style (e.g., border color: green for success, red for error, yellow for running). Optionally displays status/short output on the node. Re-enables Run buttons if run finished. Logs update received.
    * `showError(error)`: Displays errors in a dedicated area or using `alert()`. Logs the error.

---

**Next Steps After Initial Build:**

1.  **Refine Parsing:** Make the Markdown parser more robust (handle edge cases, comments).
2.  **Improve Visualization:** Use a JS graph library (Cytoscape.js, Vis.js, GoJS - check licenses) for better rendering, layout, panning, zooming.
3.  **Enhance Caching:** Implement disk-based caching, add cache invalidation based on code changes (hash the code?).
4.  **Error Handling:** Provide more detailed error reporting from Python execution back to the user.
5.  **Async Handling:** Improve handling of async operations between Python/JS (e.g., progress indicators, cancellation).
6.  **Code Editor:** Embed a simple code editor (like Monaco Editor via CDN) to view/edit box code directly in the UI (requires saving changes back to the MD file).
7.  **File Dialog:** Use `pywebview`'s file dialog API for a native "Load Markdown" experience.

This detailed plan provides a clear path forward, starting simple and allowing for incremental feature additions. Remember to test each component individually where possible before integrating them.
