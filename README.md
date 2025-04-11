
# Python Markdown Workflow Visualizer

**(Project Status: Initial Development)**

## Overview

This is a desktop application built with Python and `pywebview` that allows you to define simple Python workflows directly within a Markdown file. The application visualizes the workflow as a graph and lets you execute the entire workflow or individual steps (boxes) while leveraging caching.

The core idea is to combine the version-control-friendly nature of text-based definitions (Markdown) with a visual interface for execution and debugging.

## Features

* **Markdown-based Definition:** Define workflow boxes (containing Python code), their named inputs, and connections in a single `.md` file.
* **Visualizer:** Displays the workflow structure as a node-based graph.
* **Execution:**
    * Run the entire workflow sequentially based on dependencies.
    * Run individual boxes using cached inputs from the last successful run.
* **Caching:** Automatically caches the JSON output of each box upon successful execution.
* **Simple Interface:** Uses Bootstrap (Dark theme) and vanilla JavaScript for a clean UI within the `pywebview` window.
* **Debugging:** Basic logging implemented for tracking execution flow.

## Technology Stack

* **Backend/Core Logic:** Python 3.x
* **GUI Framework:** `pywebview`
* **Frontend:** HTML, Vanilla JavaScript, Bootstrap 5 (Dark Theme)
* **Graph Logic:** (Likely uses NetworkX internally)
* **Workflow Definition:** Custom Markdown Format

## Setup

**Prerequisites:**

* Python 3.8+
* `pip` (Python package installer)

**Installation:**

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <repository-folder-name>
    ```
2.  **Create `requirements.txt`:** Make sure you have a `requirements.txt` file including at least:
    ```txt
    pywebview
    networkx
    # Add other dependencies as needed
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Define your workflow:** Create or modify a `.md` file (see `workflow.md` for an example) following the specified format (details below).
2.  **Run the application:**
    ```bash
    python main.py
    ```
3.  **Interact with the UI:**
    * Use the "Load MD" button (or similar) to select your workflow Markdown file.
    * The workflow graph will be displayed.
    * Click on nodes (boxes) to view details or cached output (if available).
    * Use "Run All" to execute the entire workflow from the beginning.
    * Select a node and use "Run Selected" to execute only that box using its previously cached inputs.
    * Node borders will change color to indicate status (e.g., running, success, error).

## Workflow Markdown Format

Workflows are defined using specific Markdown sections:

* **Boxes:** Defined using `## BOX: box_name`. Must include a Python code block with an `execute(**inputs)` function that returns a JSON-serializable dictionary. Specify named inputs using `**Inputs:** input_name_1, input_name_2`.
* **Connections:** Defined under `## CONNECTIONS`. List connections as `source_box.output -> target_box.input_name`.
* **Layout (Optional):** Define node positions under `## VISUAL_LAYOUT` using `box_name: {"x": 100, "y": 100}`.

Refer to the `workflow.md` file in this repository for a concrete example.

## License

AGPL3
