 // Wait for pywebview to be ready
window.addEventListener('pywebviewready', () => {
    console.log("pywebview ready, initializing app.js");
    initializeApp();
});

// --- Global State ---
let currentWorkflow = null; // Holds { nodes: [], edges: [], layout: {} }
let selectedNodeId = null;
// click and drag
let isDragging = false;
let dragTarget = null;
let dragOffsetX = 0;
let dragOffsetY = 0;

// --- DOM Element References ---
let domRefs = {};

// --- Initialization ---
async function initializeApp() { // Keep async for ping and load
    // Test the API bridge first
    try {
        const pong = await pywebview.api.ping();
        console.log(`API Ping successful: ${pong}`);
        // Clear any previous error messages if ping succeeds now
        clearError();
    } catch (err) {
        console.error("API Ping failed:", err);
        // Try to show error using the function, hoping domRefs are available or fallback works
        showError(`Critical Error: Cannot communicate with backend API. ${err.message || err}`);
        // Attempt to get errorArea ref just for this message if needed
        if (!domRefs.errorArea) domRefs.errorArea = document.getElementById('error-area');
        if (domRefs.errorArea) domRefs.errorArea.textContent = `Critical Error: Cannot communicate with backend API. ${err.message || err}`;
        else alert(`Critical Error: Cannot communicate with backend API. ${err.message || err}`);
        return; // Stop initialization if API fails
    }

    domRefs = {
        loadButton: document.getElementById('load-button'),
        runAllButton: document.getElementById('run-all-button'),
        runSelectedButton: document.getElementById('run-selected-button'),
        canvasContainer: document.getElementById('workflow-canvas-container'),
        canvas: document.getElementById('workflow-canvas'),
        connectionsSvg: document.getElementById('connections-svg'),
        sidebar: document.getElementById('sidebar'),
        nodeDetailsHeader: document.getElementById('selected-node-id'),
        nodeDetailsContent: document.getElementById('node-details'),
        errorArea: document.getElementById('error-area')
    };

    // Add event listeners
    domRefs.loadButton.addEventListener('click', handleLoadClick);
    domRefs.runAllButton.addEventListener('click', handleRunAllClick);
    domRefs.runSelectedButton.addEventListener('click', handleRunSingleClick);

    // Set up global mouse event handlers for dragging
    document.addEventListener('mousemove', handleCanvasMouseMove);
    document.addEventListener('mouseup', handleCanvasMouseUp);

    // Expose functions to be called by Python
    window.app = {
        updateNodeStatus: updateNodeStatus
    };

    console.log("App initialized, refs obtained, listeners added.");

    // Initialize button states (disabled until workflow loaded)
    setRunButtonsState(false);
    domRefs.loadButton.disabled = false; // Keep load button enabled initially

    // Attempt to load the default workflow now that ping succeeded
    await loadDefaultWorkflow(); // Use await here
}

// --- Workflow Loading Logic ---
async function loadWorkflowByPath(filePath) {
    if (!filePath) {
        console.log("No file path provided to loadWorkflowByPath.");
        return;
    }
    console.log(`Attempting to load workflow from path: ${filePath}`);
    clearError();
    showLoadingState("Loading workflow...");
    try {
        const result = await pywebview.api.load_workflow(filePath);
        hideLoadingState();
        if (result && result.success) {
            console.log("Workflow loaded successfully from Python:", result);
            renderGraph(result);
        } else {
            const errorMsg = result?.error || "Unknown error loading workflow.";
            console.error("Error loading workflow:", errorMsg);
            showError(`Failed to load workflow: ${errorMsg}`);
            resetUI();
        }
    } catch (error) {
        hideLoadingState();
        console.error(`Error loading workflow from path ${filePath}:`, error);
        showError(`Error loading workflow: ${error.message || error}`);
        resetUI();
    }
}

// Restore loadDefaultWorkflow function
async function loadDefaultWorkflow() {
    console.log("Attempting to load default workflow 'workflow.md'");
    try {
        // Use the get_absolute_path API function
        const absPath = await pywebview.api.get_absolute_path('workflow.md');
        if (absPath) {
            await loadWorkflowByPath(absPath);
        } else {
            console.warn("Could not get absolute path for default workflow.md. UI will remain empty.");
            showError("Could not find default workflow.md file.");
            // Ensure buttons remain disabled if default load fails
             setRunButtonsState(false);
             domRefs.loadButton.disabled = false; // Keep load button enabled
        }
    } catch(error) {
        console.error("Error getting absolute path for default workflow:", error);
        // Check if the specific API function is missing
        if (error instanceof TypeError && error.message.includes("get_absolute_path is not a function")) {
             showError("Error: Backend API missing 'get_absolute_path' function.");
        } else {
             showError(`Error finding default workflow: ${error.message || error}`);
        }
         // Ensure buttons remain disabled if default load fails
         setRunButtonsState(false);
         domRefs.loadButton.disabled = false; // Keep load button enabled
    }
}


// --- Event Handlers ---
async function handleLoadClick() {
    console.log("Load button clicked");
    clearError();
    try {
        // Use pywebview's file dialog API
        const filePath = await pywebview.api.request_file_dialog();
        if (filePath) {
             await loadWorkflowByPath(filePath); // Use the common loading function
        } else {
            console.log("File selection cancelled.");
        }
    } catch (error) {
        console.error("Error requesting file dialog or loading workflow:", error);
        // Check if the error is the specific one about request_file_dialog
        if (error instanceof TypeError && error.message.includes("request_file_dialog is not a function")) {
             showError("Error: File dialog function not available in the backend API.");
        } else {
             showError(`Error loading file: ${error.message || error}`);
        }
        // Don't reset UI here, might have a workflow loaded already
    }
}

function handleRunAllClick() {
    console.log("Run All button clicked");
    if (!currentWorkflow) {
        showError("No workflow loaded to run.");
        return;
    }
    clearError();
    setRunButtonsState(false); // Disable buttons during run
    // Reset node statuses visually before run
    resetNodeStatuses();
    // Clear previous output displays
    clearOutputDisplays();
    console.log("Requesting full workflow run...");
    pywebview.api.request_run_all()
        .then(response => console.log("Run all request sent:", response))
        .catch(err => {
            console.error("Error sending run all request:", err);
            showError(`Error starting workflow: ${err.message || err}`);
            setRunButtonsState(true); // Re-enable buttons on error
        });
}

function handleRunSingleClick() {
    console.log("Run Selected button clicked");
    if (!selectedNodeId) {
        showError("No node selected to run.");
        return;
    }
    if (!currentWorkflow) {
        showError("No workflow loaded.");
        return;
    }
    clearError();
    setRunButtonsState(false); // Disable buttons during run
    // Reset status only for the selected node
    const nodeElement = document.querySelector(`.workflow-node[data-box-id="${selectedNodeId}"]`);
    if (nodeElement) {
        nodeElement.classList.remove('success', 'error', 'running');
    }
    console.log(`Requesting single run for node: ${selectedNodeId}`);
    pywebview.api.request_run_single(selectedNodeId)
        .then(response => console.log(`Single run request for ${selectedNodeId} sent:`, response))
        .catch(err => {
            console.error(`Error sending single run request for ${selectedNodeId}:`, err);
            showError(`Error starting single run: ${err.message || err}`);
            setRunButtonsState(true); // Re-enable buttons on error
        });
}

// --- Core Rendering and UI Functions ---
// Update your renderGraph function to make sure initial positioning is clean
function renderGraph(workflowData) {
    console.log("Rendering graph with data:", workflowData);
    currentWorkflow = workflowData; // Store the loaded workflow data
    selectedNodeId = null; // Reset selection

    // Clear previous graph elements
    domRefs.canvas.innerHTML = ''; // Clear nodes
    domRefs.connectionsSvg.innerHTML = ''; // Clear lines
    clearOutputDisplays(); // Clear previous output displays
    resetNodeStatuses();
    clearNodeDetails();
    clearError();

    // Clear canvas and connections first
    domRefs.canvas.innerHTML = '';
    if (domRefs.connectionsSvg) {
        // Keep only the defs element if it exists
        const defs = domRefs.connectionsSvg.querySelector('defs');
        domRefs.connectionsSvg.innerHTML = '';
        if (defs) domRefs.connectionsSvg.appendChild(defs);
    }

    if (!workflowData || !workflowData.nodes || workflowData.nodes.length === 0) {
        console.log("No nodes to render.");
        domRefs.nodeDetailsContent.innerHTML = '<p class="text-muted">Workflow loaded, but it contains no boxes.</p>';
        setRunButtonsState(false); // Disable run buttons if no nodes
        return;
    }

    // Store the workflow data
    currentWorkflow = workflowData;

    // Render nodes
    workflowData.nodes.forEach(node => {
        const nodeElement = document.createElement('div');
        nodeElement.classList.add('workflow-node');
        nodeElement.dataset.boxId = node.id;
        nodeElement.textContent = node.id;

        // Apply layout position if available, with safe parsing
        const layout = workflowData.layout?.[node.id];
        if (layout && 
            typeof layout.x !== 'undefined' && 
            typeof layout.y !== 'undefined') {
            
            // Ensure we're working with numbers
            const x = parseInt(layout.x);
            const y = parseInt(layout.y);
            
            // Apply position if valid
            if (!isNaN(x) && !isNaN(y)) {
                nodeElement.style.left = `${x}px`;
                nodeElement.style.top = `${y}px`;
                console.log(`Positioned node ${node.id} at ${x},${y}`);
            } else {
                console.warn(`Invalid position for node ${node.id}: ${layout.x},${layout.y}`);
                // Use fallback positioning
                nodeElement.style.left = `50px`;
                nodeElement.style.top = `${50 + workflowData.nodes.indexOf(node) * 80}px`;
            }
        } else {
            // Basic fallback positioning
            nodeElement.style.left = `50px`;
            nodeElement.style.top = `${50 + workflowData.nodes.indexOf(node) * 80}px`;
        }

        // Add event listeners
        nodeElement.addEventListener('click', handleNodeClick);
        nodeElement.addEventListener('mousedown', handleNodeMouseDown);
        
        domRefs.canvas.appendChild(nodeElement);
    });

    // Render edges (connections) as SVG lines
    // Need a slight delay to ensure nodes are in the DOM for position calculation
    setTimeout(() => renderConnections(workflowData.edges), 50);


    setRunButtonsState(true); // Enable run buttons now that workflow is loaded
    console.log("Graph rendering complete.");
}

function renderConnections(edges) {
    if (!edges || !domRefs.connectionsSvg) {
        console.warn("No edges or SVG container to render connections.");
        return;
    }
    
    // Clear previous connections
    // Keep only definitions (markers)
    const defs = domRefs.connectionsSvg.querySelector('defs');
    domRefs.connectionsSvg.innerHTML = '';
    
    // Re-add the defs if they were removed
    if (defs) {
        domRefs.connectionsSvg.appendChild(defs);
    } else {
        // Create defs if they don't exist
        const newDefs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        
        // Standard arrowhead
        const arrowhead = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        arrowhead.setAttribute('id', 'arrowhead');
        arrowhead.setAttribute('markerWidth', '10');
        arrowhead.setAttribute('markerHeight', '7');
        arrowhead.setAttribute('refX', '10');
        arrowhead.setAttribute('refY', '3.5');
        arrowhead.setAttribute('orient', 'auto');
        
        const arrowheadPath = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrowheadPath.setAttribute('points', '0 0, 10 3.5, 0 7');
        arrowheadPath.setAttribute('fill', '#999');
        
        arrowhead.appendChild(arrowheadPath);
        
        // Output arrowhead
        const outputArrowhead = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        outputArrowhead.setAttribute('id', 'output-arrowhead');
        outputArrowhead.setAttribute('markerWidth', '10');
        outputArrowhead.setAttribute('markerHeight', '7');
        outputArrowhead.setAttribute('refX', '10');
        outputArrowhead.setAttribute('refY', '3.5');
        outputArrowhead.setAttribute('orient', 'auto');
        
        const outputArrowheadPath = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        outputArrowheadPath.setAttribute('points', '0 0, 10 3.5, 0 7');
        outputArrowheadPath.setAttribute('fill', '#00a0ff');
        
        outputArrowhead.appendChild(outputArrowheadPath);
        
        newDefs.appendChild(arrowhead);
        newDefs.appendChild(outputArrowhead);
        domRefs.connectionsSvg.appendChild(newDefs);
    }
    
    // Draw each edge
    edges.forEach(edge => {
        const sourceNode = document.querySelector(`.workflow-node[data-box-id="${edge.source}"]`);
        const targetNode = document.querySelector(`.workflow-node[data-box-id="${edge.target}"]`);
        
        if (!sourceNode || !targetNode) {
            console.warn(`Cannot draw edge: Node not found ${edge.source} -> ${edge.target}`);
            return;
        }
        
        // Get node positions
        const sourceRect = sourceNode.getBoundingClientRect();
        const targetRect = targetNode.getBoundingClientRect();
        const canvasRect = domRefs.canvasContainer.getBoundingClientRect();
        
        // Account for scroll
        const scrollLeft = domRefs.canvasContainer.scrollLeft;
        const scrollTop = domRefs.canvasContainer.scrollTop;
        
        // Calculate connection points
        const sourceX = sourceRect.left + sourceRect.width / 2 - canvasRect.left + scrollLeft;
        const sourceY = sourceRect.top + sourceRect.height / 2 - canvasRect.top + scrollTop;
        const targetX = targetRect.left + targetRect.width / 2 - canvasRect.left + scrollLeft;
        const targetY = targetRect.top + targetRect.height / 2 - canvasRect.top + scrollTop;
        
        // Create line element
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', sourceX);
        line.setAttribute('y1', sourceY);
        line.setAttribute('x2', targetX);
        line.setAttribute('y2', targetY);
        line.setAttribute('class', 'workflow-connection');
        line.setAttribute('marker-end', 'url(#arrowhead)');
        
        domRefs.connectionsSvg.appendChild(line);
    });
}


async function handleNodeClick(event) {
    const targetNode = event.currentTarget; // The node div that was clicked
    const boxId = targetNode.dataset.boxId;
    console.log(`Node clicked: ${boxId}`);

    if (selectedNodeId === boxId) {
        // Optional: Deselect if clicked again? For now, just refresh details.
    }

    // Remove 'selected' class from previously selected node
    if (selectedNodeId) {
        const previousNode = document.querySelector(`.workflow-node[data-box-id="${selectedNodeId}"]`);
        if (previousNode) {
            previousNode.classList.remove('selected');
        }
    }

    // Add 'selected' class to the clicked node
    targetNode.classList.add('selected');
    selectedNodeId = boxId;

    // Update sidebar header
    domRefs.nodeDetailsHeader.textContent = `ID: ${boxId}`;
    domRefs.runSelectedButton.disabled = false; // Enable run selected button

    // Fetch and display cached data
    domRefs.nodeDetailsContent.innerHTML = '<p class="text-muted">Loading cached data...</p>';
    try {
        const cachedData = await pywebview.api.get_cached_data(boxId);
        displayNodeDetails(cachedData);
    } catch (error) {
        console.error(`Error fetching cached data for ${boxId}:`, error);
        domRefs.nodeDetailsContent.innerHTML = `<p class="text-danger">Error loading cached data: ${error.message || error}</p>`;
    }
}

function displayNodeDetails(cachedData) {
    if (cachedData !== null && typeof cachedData === 'object') {
        try {
            // Pretty print the JSON object
            const formattedJson = JSON.stringify(cachedData, null, 2); // Indent with 2 spaces
            domRefs.nodeDetailsContent.textContent = formattedJson;
        } catch (error) {
             console.error("Error stringifying cached data:", error);
             domRefs.nodeDetailsContent.textContent = `Error displaying data: ${error}\n\nRaw data: ${cachedData}`;
        }
    } else if (cachedData !== null) {
        // Handle cases where cached data might not be an object (though backend should ensure it is)
        domRefs.nodeDetailsContent.textContent = String(cachedData);
    }
    else {
        domRefs.nodeDetailsContent.innerHTML = '<p class="text-muted">No cached output available for this node.</p>';
    }
}

function updateNodeStatus(boxId, status, data) {
    console.log(`Received status update: Box=${boxId}, Status=${status}, Data=`, data);
    const nodeElement = document.querySelector(`.workflow-node[data-box-id="${boxId}"]`);
    if (!nodeElement) {
        console.warn(`Node element not found for status update: ${boxId}`);
        return;
    }

    // Remove previous status classes
    nodeElement.classList.remove('running', 'success', 'error');
    
    // Add the new status class
    if (status === 'running' || status === 'success' || status === 'error') {
        nodeElement.classList.add(status);
    }

    // If data is available, display it on the canvas
    if (data && status === 'success') {
        displayNodeOutputOnCanvas(boxId, data);
    }
    
    // Re-enable run buttons when a node finishes (success or error)
    if (status === 'success' || status === 'error') {
        setRunButtonsState(true);
    }

}

// --- Utility Functions ---

function setRunButtonsState(enabled) {
    domRefs.runAllButton.disabled = !enabled;
    // Only enable runSelected if a node is actually selected
    domRefs.runSelectedButton.disabled = !enabled || !selectedNodeId;
}

function resetUI() {
    currentWorkflow = null;
    selectedNodeId = null;
    domRefs.canvas.innerHTML = '';
    domRefs.connectionsSvg.innerHTML = '';
    clearNodeDetails();
    setRunButtonsState(false); // Disable run buttons
    domRefs.runSelectedButton.disabled = true; // Ensure run selected is disabled
}

function resetNodeStatuses() {
    const nodes = document.querySelectorAll('.workflow-node');
    nodes.forEach(node => {
        node.classList.remove('running', 'success', 'error', 'selected');
    });
}

function clearNodeDetails() {
     domRefs.nodeDetailsHeader.textContent = 'None Selected';
     domRefs.nodeDetailsContent.innerHTML = '<p class="text-muted">Load a workflow and click a node.</p>';
}

function showError(message, isWarning = false) { // Signature already updated, ensure logic below matches
    // Ensure errorArea exists before trying to set textContent
    if (domRefs.errorArea) {
        domRefs.errorArea.textContent = message;
        if (isWarning) {
            domRefs.errorArea.classList.remove('text-danger');
            domRefs.errorArea.classList.add('text-warning');
            console.warn("UI Warning:", message);
        } else {
            domRefs.errorArea.classList.add('text-danger');
            domRefs.errorArea.classList.remove('text-warning');
            console.error("UI Error:", message);
        }
    } else {
         // Fallback if called before DOM refs are ready (e.g., during early init failure)
         console.error(`UI Error (DOM not ready): ${message}`);
         alert(`Error: ${message}`); // Use alert as fallback
    }
}

function clearError() {
    if (domRefs.errorArea) {
        domRefs.errorArea.textContent = '';
        domRefs.errorArea.classList.remove('text-danger', 'text-warning');
    }
}

function showLoadingState(message = "Loading...") {
    // Simple implementation: show message in error area or a dedicated loading div
    domRefs.errorArea.textContent = message;
    if (domRefs.errorArea) {
        domRefs.errorArea.textContent = message;
        domRefs.errorArea.classList.remove('text-danger', 'text-warning'); // Make it look neutral
    }
    if (domRefs.loadButton) {
        // Keep load button enabled during loading unless specifically disabled elsewhere
        // domRefs.loadButton.disabled = true;
    }
}

function hideLoadingState() {
    clearError(); // Clear the loading message
    // Restore potential error styling possibility if needed after loading
    // if (domRefs.errorArea) domRefs.errorArea.classList.add('text-danger');
    // if (domRefs.loadButton) domRefs.loadButton.disabled = false;
}

console.log("app.js loaded");

// --- Output Display Functions ---

function displayNodeOutputOnCanvas(boxId, outputData) {
    removeNodeOutputDisplay(boxId); // Remove previous if exists

    const nodeElement = document.querySelector(`.workflow-node[data-box-id="${boxId}"]`);
    if (!nodeElement || !outputData || typeof outputData !== 'object') {
        console.warn(`Cannot display output for ${boxId}: Node not found or output is not an object.`);
        return;
    }

    const outputDiv = document.createElement('div');
    outputDiv.classList.add('workflow-output-display');
    outputDiv.id = `output-${boxId}`;

    // Generate table HTML
    // let tableHtml = '<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>';
    // for (const key in outputData) {
    //     if (Object.hasOwnProperty.call(outputData, key)) {
    //         const value = outputData[key];
    //         // Attempt to pretty-print if value looks like JSON string, otherwise display as is
    //         let displayValue = '';
    //         if (typeof value === 'string') {
    //             try {
    //                 const parsedJson = JSON.parse(value);
    //                 // Check if it's actually an object/array after parsing
    //                 if (typeof parsedJson === 'object' && parsedJson !== null) {
    //                      displayValue = `<pre>${JSON.stringify(parsedJson, null, 2)}</pre>`;
    //                 } else {
    //                      // It was a simple string that happened to be valid JSON (e.g., '"hello"')
    //                      displayValue = escapeHtml(value);
    //                 }
    //             } catch (e) {
    //                 // Not a valid JSON string, display as plain text
    //                 displayValue = escapeHtml(value);
    //             }
    //         } else if (typeof value === 'object' && value !== null) {
    //              displayValue = `<pre>${JSON.stringify(value, null, 2)}</pre>`;
    //         }
    //          else {
    //             displayValue = escapeHtml(String(value));
    //         }

    //         tableHtml += `<tr><td>${escapeHtml(key)}</td><td>${displayValue}</td></tr>`;
    //     }
    // }
    // tableHtml += '</tbody></table>';
    // outputDiv.innerHTML = tableHtml;

    // // Position it to the right of the node
    // const nodeRect = nodeElement.getBoundingClientRect();
    // const canvasRect = domRefs.canvas.getBoundingClientRect(); // Relative to canvas

    // // Position relative to the #workflow-canvas div
    // const top = nodeElement.offsetTop;
    // const left = nodeElement.offsetLeft + nodeElement.offsetWidth + 10; // 10px spacing

    // outputDiv.style.top = `${top}px`;
    // outputDiv.style.left = `${left}px`;

    // domRefs.canvas.appendChild(outputDiv);
    // Generate table HTML
    let tableHtml = '<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>';
    for (const key in outputData) {
        if (Object.hasOwnProperty.call(outputData, key)) {
            const value = outputData[key];
            // Attempt to pretty-print if value looks like JSON string or is an object, otherwise display as is
            let displayValue = '';
            if (typeof value === 'string') {
                try {
                    const parsedJson = JSON.parse(value);
                    // Check if it's actually an object/array after parsing
                    if (typeof parsedJson === 'object' && parsedJson !== null) {
                         displayValue = `<pre>${JSON.stringify(parsedJson, null, 2)}</pre>`;
                    } else {
                         // It was a simple string that happened to be valid JSON (e.g., '"hello"')
                         displayValue = escapeHtml(value);
                    }
                } catch (e) {
                    // Not a valid JSON string, display as plain text
                    displayValue = escapeHtml(value);
                }
            } else if (typeof value === 'object' && value !== null) {
                 displayValue = `<pre>${JSON.stringify(value, null, 2)}</pre>`;
            }
             else {
                displayValue = escapeHtml(String(value));
            }

            tableHtml += `<tr><td>${escapeHtml(key)}</td><td>${displayValue}</td></tr>`;
        }
    }
    tableHtml += '</tbody></table>';
    outputDiv.innerHTML = tableHtml;

    // Position it to the right of the node
    const top = nodeElement.offsetTop;
    const left = nodeElement.offsetLeft + nodeElement.offsetWidth + 10; // 10px spacing

    outputDiv.style.top = `${top}px`;
    outputDiv.style.left = `${left}px`;

    domRefs.canvas.appendChild(outputDiv);
    
    // Draw the connection line after adding the output to the DOM
    // Need a slight delay to ensure the output's position is calculated
    setTimeout(() => drawOutputConnection(boxId), 10);
}

function removeNodeOutputDisplay(boxId) {
    const outputDiv = document.getElementById(`output-${boxId}`);
    if (outputDiv) {
        outputDiv.remove();
        removeOutputConnection(boxId);
    }
}

function clearOutputDisplays() {
    const displays = document.querySelectorAll('.workflow-output-display');
    displays.forEach(display => display.remove());
    console.log("Cleared all node output displays.");
}

function escapeHtml(unsafe) {
    if (unsafe === null || typeof unsafe === 'undefined') return '';
    return String(unsafe)
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Handle start of dragging
function handleNodeMouseDown(event) {
    // Only start drag on primary mouse button (left click)
    if (event.button !== 0) return;
    
    const node = event.currentTarget;
    dragTarget = node;
    isDragging = true;
    
    // Get current node position
    const nodeLeft = parseInt(node.style.left) || 0;
    const nodeTop = parseInt(node.style.top) || 0;
    
    // Calculate offset between mouse position and node position
    // This is the difference between where you clicked in the node and the node's origin
    dragOffsetX = event.clientX - node.getBoundingClientRect().left;
    dragOffsetY = event.clientY - node.getBoundingClientRect().top;
    
    // Add dragging indicator class
    node.classList.add('dragging');
    
    // Prevent default behavior to avoid text selection during drag
    event.preventDefault();
    
    console.log(`Drag started for ${node.dataset.boxId}. Initial position: ${nodeLeft},${nodeTop}`);
}

// Handle dragging motion
function handleCanvasMouseMove(event) {
    if (!isDragging || !dragTarget) return;
    
    const canvasContainer = domRefs.canvasContainer;
    const containerRect = canvasContainer.getBoundingClientRect();
    
    // Calculate the new position in the canvas coordinate space
    // Adjust for container scroll position and the original click offset
    const newLeft = event.clientX - containerRect.left - dragOffsetX + canvasContainer.scrollLeft;
    const newTop = event.clientY - containerRect.top - dragOffsetY + canvasContainer.scrollTop;
    
    // Apply the new position
    dragTarget.style.left = `${newLeft}px`;
    dragTarget.style.top = `${newTop}px`;
    
    // Move output display if it exists
    const boxId = dragTarget.dataset.boxId;
    const outputDisplay = document.getElementById(`output-${boxId}`);
    if (outputDisplay) {
        outputDisplay.style.left = `${newLeft + dragTarget.offsetWidth + 10}px`;
        outputDisplay.style.top = `${newTop}px`;
        
        // Update output connection line if it exists
        drawOutputConnection(boxId);
    }
    
    // Update workflow connections
    if (currentWorkflow && currentWorkflow.edges) {
        renderConnections(currentWorkflow.edges);
    }
}

// Handle end of dragging
function handleCanvasMouseUp(event) {
    if (isDragging && dragTarget) {
        // Log final position for debugging
        const finalLeft = parseInt(dragTarget.style.left) || 0;
        const finalTop = parseInt(dragTarget.style.top) || 0;
        console.log(`Drag ended for ${dragTarget.dataset.boxId}. Final position: ${finalLeft},${finalTop}`);
        
        // Remove dragging indicator class
        dragTarget.classList.remove('dragging');
        
        // If we have a workflow and it's a valid node, update the layout
        const boxId = dragTarget.dataset.boxId;
        if (currentWorkflow && currentWorkflow.layout && boxId) {
            // Ensure layout object exists for this node
            if (!currentWorkflow.layout[boxId]) {
                currentWorkflow.layout[boxId] = {};
            }
            
            // Store the new position
            currentWorkflow.layout[boxId].x = finalLeft;
            currentWorkflow.layout[boxId].y = finalTop;
            
            // Persist the layout changes to the backend
            saveWorkflowLayout();
        }
    }
    
    // Reset drag state
    isDragging = false;
    dragTarget = null;
}

// Save layout to backend
async function saveWorkflowLayout() {
    if (!currentWorkflow || !currentWorkflow.layout) return;
    
    try {
        console.log("Saving layout:", currentWorkflow.layout);
        const result = await pywebview.api.save_workflow_layout(currentWorkflow.layout);
        console.log("Layout saved:", result);
        
        if (result && !result.success) {
            console.warn("Layout save warning:", result.warning || result.error);
        }
    } catch (error) {
        console.error("Error saving workflow layout:", error);
        showError("Layout changes may not persist: " + (error.message || error), true);
    }
}

// Draw connections between nodes and their output displays
function drawOutputConnection(boxId) {
    const nodeElement = document.querySelector(`.workflow-node[data-box-id="${boxId}"]`);
    const outputDisplay = document.getElementById(`output-${boxId}`);
    
    if (!nodeElement || !outputDisplay) {
        return;
    }
    
    // Remove any existing connection for this output
    const existingLine = document.getElementById(`output-connection-${boxId}`);
    if (existingLine) {
        existingLine.remove();
    }
    
    // Create SVG line
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.id = `output-connection-${boxId}`;
    line.classList.add('output-connection-line');
    
    // Get positions relative to canvas container
    const canvasContainer = domRefs.canvasContainer;
    const containerRect = canvasContainer.getBoundingClientRect();
    const nodeRect = nodeElement.getBoundingClientRect();
    const outputRect = outputDisplay.getBoundingClientRect();
    
    // Account for scroll
    const scrollLeft = canvasContainer.scrollLeft;
    const scrollTop = canvasContainer.scrollTop;
    
    // Calculate connection points (right of node to left of output)
    const x1 = nodeRect.right - containerRect.left + scrollLeft;
    const y1 = nodeRect.top + (nodeRect.height / 2) - containerRect.top + scrollTop;
    const x2 = outputRect.left - containerRect.left + scrollLeft;
    const y2 = outputRect.top + (outputRect.height / 2) - containerRect.top + scrollTop;
    
    // Set attributes
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    line.setAttribute('marker-end', 'url(#output-arrowhead)');
    
    // Add to SVG
    domRefs.connectionsSvg.appendChild(line);
}

// Remove output connection when an output is removed
function removeOutputConnection(boxId) {
    const connectionLine = document.getElementById(`output-connection-${boxId}`);
    if (connectionLine) {
        connectionLine.remove();
    }
}