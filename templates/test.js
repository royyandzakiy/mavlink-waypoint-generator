// test.js

// ===============================================================
// MapManager Class
// Handles Leaflet map initialization and layer management
// ===============================================================
class MapManager {
    constructor(mapId, defaultView = [51.505, -0.09], defaultZoom = 13) {
        this.mapId = mapId;
        this.defaultView = defaultView;
        this.defaultZoom = defaultZoom;
        this.map = null;
        this.shapes = []; // Central storage for finalized shapes
    }

    init() {
        this.map = L.map(this.mapId).setView(this.defaultView, this.defaultZoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(this.map);
        return this.map; // Return map instance for other classes
    }

    addShapeLayer(shapeData) {
        // Add the shape layer to the map
        shapeData.layer.addTo(this.map);

        // Add click listener for the shape on the map
        shapeData.layer.on('click', () => {
             // Use getShapeInfoText from the instance
            alert(`Clicked ${shapeData.type}!\n${this.getShapeInfoText(shapeData)}`);
        });

        this.shapes.push(shapeData); // Add to central storage
    }

    removeShapeLayer(index) {
        if (index >= 0 && index < this.shapes.length) {
            // Ensure the layer exists before attempting to remove
            if (this.shapes[index].layer && this.map.hasLayer(this.shapes[index].layer)) {
                this.shapes[index].layer.remove();
            }
            this.shapes.splice(index, 1); // Remove from central storage
        }
    }

    getShapes() {
        return this.shapes;
    }

    // Helper to get shape info text (kept here, uses shape data properties)
    getShapeInfoText(shape) {
        if (shape.type === 'box') {
             // Use the stored bounds property
            const bounds = shape.bounds;
            if (!bounds) return 'Bounds data missing'; // Add a check
            const ne = bounds.getNorthEast();
            const sw = bounds.getSouthWest();
            return `
                NW: ${ne.lat.toFixed(4)}, ${sw.lng.toFixed(4)}<br>
                NE: ${ne.lat.toFixed(4)}, ${ne.lng.toFixed(4)}<br>
                SE: ${sw.lat.toFixed(4)}, ${ne.lng.toFixed(4)}<br>
                SW: ${sw.lat.toFixed(4)}, ${sw.lng.toFixed(4)}
            `;
        } else if (shape.type === 'circle') {
             // Use the stored center and radius properties
            const center = shape.center;
            const radius = shape.radius;
            if (!center || radius === null) return 'Center/Radius data missing'; // Add a check
            return `
                Center: ${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}<br>
                Radius: ${radius.toFixed(2)} meters
            `;
        } else if (shape.type === 'polygon') {
             // Use the stored points array
            const points = shape.points;
            if (!points || points.length === 0) return 'Polygon points data missing'; // Add a check
            return points.map((point, i) =>
                {
                    if (!point || typeof point.lat === 'undefined' || typeof point.lng === 'undefined') {
                         return `Point ${i + 1}: Invalid Data`; // Check individual points
                    }
                    return `Point ${i + 1}: ${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`;
                }
            ).join('<br>');
        }
        return '';
    }
}

// ===============================================================
// ShapeCreator Class
// Handles the interactive process of drawing shapes on the map
// ===============================================================
class ShapeCreator {
    constructor(map, onShapeFinalized, onCreationCancelled) {
        this.map = map;
        this.onShapeFinalized = onShapeFinalized; // Callback when a shape is done
        this.onCreationCancelled = onCreationCancelled; // Callback when creation is cancelled

        this.currentMode = null;
        this.creationInProgress = false;
        this.centerPoint = null; // For box/circle start point
        this.tempMarker = null; // Temp marker for center point
        this.tempShape = null; // Temp preview shape (box/circle/polygon)
        this.tempPolyLine = null; // For polygon drawing preview
        this.polygonPoints = []; // For polygon points
        this.lastClickTime = 0; // To help debounce polygon double-click
    }

    activate() {
        // Pass 'this' as the context for the event handlers
        this.map.on('click', this.handleMapClick, this);
        this.map.on('dblclick', this.handleMapDoubleClick, this);
        this.map.on('mousemove', this.handleMapMove, this);
        this.map.on('contextmenu', this.handleRightClick, this);
    }

    deactivate() {
        this.map.off('click', this.handleMapClick, this);
        this.map.off('dblclick', this.handleMapDoubleClick, this);
        this.map.off('mousemove', this.handleMapMove, this);
        this.map.off('contextmenu', this.handleRightClick, this);
    }

    setMode(mode) {
        // Only change mode if it's different or no creation is in progress
        if (this.currentMode !== mode || !this.creationInProgress) {
             this.cancelCreation(); // Cancel previous creation process
             this.currentMode = mode;
             console.log(`Creation mode set to: ${this.currentMode}`);
             // The UI Manager will update buttons based on this.currentMode
        } else {
            // Clicking the same button while in progress cancels the current operation
            console.log(`Clicked button for current mode (${mode}). Cancelling creation.`);
            this.cancelCreation();
        }
    }

    getMode() {
        return this.currentMode;
    }

    isCreationInProgress() {
        return this.creationInProgress;
    }

    cancelCreation() {
        const wasInProgress = this.creationInProgress;
        const wasModeActive = this.currentMode !== null; // Check if a mode was active

        this.currentMode = null; // Reset mode
        this.creationInProgress = false;
        this.centerPoint = null;
        this.polygonPoints = [];

        // Remove temporary layers
        if (this.tempMarker) {
            this.tempMarker.remove();
            this.tempMarker = null;
        }
        if (this.tempShape) {
            this.tempShape.remove();
            this.tempShape = null;
        }
        if (this.tempPolyLine) {
            this.tempPolyLine.remove();
            this.tempPolyLine = null;
        }

        console.log("Creation cancelled.");
        // Notify listener (UIManager) if creation was actually in progress or a mode was set
        if (wasInProgress || wasModeActive) {
             if (this.onCreationCancelled) {
                 this.onCreationCancelled();
            }
        }
    }

    handleRightClick(e) {
        e.originalEvent.preventDefault(); // Prevent default context menu
        this.cancelCreation();
    }

    handleMapDoubleClick(e) {
         if (this.currentMode === 'polygon' && this.creationInProgress) {
            e.originalEvent.preventDefault(); // Prevent zoom on dblclick
             // Finalize polygon on double-click if enough points
             if (this.polygonPoints.length >= 3) {
                 // Add the final click point before finalizing
                 // Check if the last point was already added by a quick click
                 const lastPoint = this.polygonPoints[this.polygonPoints.length - 1];
                 if (!e.latlng.equals(lastPoint)) {
                     this.addPolygonPoint(e.latlng); // Add the last point if it's new
                 }
                 this.finalizePolygon();
             } else {
                 // Not enough points for a valid polygon, cancel
                 console.warn("Double-clicked, but not enough points for a polygon. Cancelling.");
                 this.cancelCreation();
             }
         }
    }


    handleMapClick(e) {
        if (!this.currentMode) return; // Ignore clicks if no mode is set

        if (this.currentMode === 'polygon') {
            const now = Date.now();
            // Basic debounce against the DBLCLICK event.
            // If a click happens shortly after the last one AND creation is in progress,
            // it might be part of a double-click to finalize. Check distance to first point.
            if (this.creationInProgress && now - this.lastClickTime < 300) {
                 const firstPoint = this.polygonPoints[0];
                 const distance = e.latlng.distanceTo(firstPoint);
                 if (distance < 20 && this.polygonPoints.length >= 3) { // Increased tolerance slightly
                     console.log("Clicked near start point, finalizing polygon.");
                      // Add the closing point and finalize
                      this.addPolygonPoint(e.latlng);
                      this.finalizePolygon();
                      return; // Stop processing this click after finalization
                 }
                 // Ignore rapid clicks that are not closing
                 return;
            }
             this.lastClickTime = now; // Update last click time for debouncing

            if (!this.creationInProgress) {
                // Start a new polygon
                this.polygonPoints = [e.latlng];
                this.creationInProgress = true;
                 console.log("Starting polygon creation");
                 // Add the first point, which will trigger polyline/shape preview updates
                 this.addPolygonPoint(e.latlng); // Add the first point to the array
            } else {
                 // Add subsequent point
                 this.addPolygonPoint(e.latlng);
            }
            return; // Stop processing after handling polygon click
        }

        // Box or Circle creation
        if (!this.creationInProgress) {
            // First click: set center/start point
            this.centerPoint = e.latlng;
            this.creationInProgress = true;

            // Add a temporary marker for the center point
            this.tempMarker = L.circleMarker(this.centerPoint, {
                radius: 5,
                color: '#ff0000'
            }).addTo(this.map);
             console.log(`${this.currentMode} creation started.`);

        } else {
            // Second click: finalize the shape
            this.creationInProgress = false;
            this.tempMarker.remove(); // Remove the temporary center marker
            this.tempMarker = null; // Clear the reference

            // *** FIX: Reset mode BEFORE calling the finalize callback ***
            const completedMode = this.currentMode; // Capture mode before resetting
            this.currentMode = null; // Reset mode

            // Pass the final click position to createFinalShape
            const finalizedShape = this.createFinalShape(e.latlng, completedMode); // Pass mode to helper
            if (finalizedShape) {
                if (this.onShapeFinalized) {
                    // Call the callback with the finalized shape data
                    this.onShapeFinalized(finalizedShape); // This callback calls uiManager.updateButtonStates()
                }
            }

            // Remove the temporary preview shape after getting its data
            if (this.tempShape) {
                 this.tempShape.remove();
                 this.tempShape = null; // Clear the reference
            }

            this.centerPoint = null; // Reset center point
             console.log(`${completedMode} creation finalized.`);
             // currentMode is already null
        }
    }

    addPolygonPoint(point) {
         // Prevent adding the exact same point consecutively (can happen with rapid clicks/dblclick)
         if (this.polygonPoints.length > 0 && point.equals(this.polygonPoints[this.polygonPoints.length - 1])) {
             console.log("Ignoring duplicate polygon point.");
             return;
         }

        this.polygonPoints.push(point);
        console.log(`Added point ${this.polygonPoints.length}:`, point.lat, point.lng);

        // Update temporary shapes
        if (this.tempPolyLine) this.tempPolyLine.remove();
        if (this.tempShape) this.tempShape.remove();

        // Create polyline preview (always update with the mouse position in handleMapMove)
        // Here we just redraw based on committed points for visual confirmation after click
        this.tempPolyLine = L.polyline(this.polygonPoints, {
            color: '#ff0000',
            weight: 2,
            dashArray: '5,5'
        }).addTo(this.map);

        // Create polygon preview (if enough points)
        if (this.polygonPoints.length >= 2) { // Need at least 2 committed points to show a preview polygon with the mouse point
             // Create the polygon preview based on committed points + mouse position
             const previewPoints = [...this.polygonPoints, this.map.mouseEventToLatLng(event)]; // 'event' is potentially flaky, relying on handleMapMove is better
             // Let's rely on handleMapMove to create/update the preview polygon more reliably
             // This click handler just updates the committed points and the polyline based on them.
             // The actual polygon preview shape is handled in handleMapMove.
        }
    }

     // This method is primarily for updating the preview shape on mouse move
    handleMapMove(e) {
        if (!this.creationInProgress || !this.currentMode) return;

        if (this.currentMode === 'polygon') {
             if (this.polygonPoints.length > 0) {
                 // Update the polyline preview with the current mouse position
                 const currentPoints = [...this.polygonPoints, e.latlng];
                 if (this.tempPolyLine) {
                     this.tempPolyLine.setLatLngs(currentPoints);
                 } else {
                      // If tempPolyLine got removed somehow, recreate it
                       this.tempPolyLine = L.polyline(currentPoints, {
                            color: '#ff0000',
                            weight: 2,
                            dashArray: '5,5'
                        }).addTo(this.map);
                 }


                 // Update the polygon preview (if enough points)
                 if (this.polygonPoints.length >= 2) { // Need at least 2 existing points + mouse = 3
                      // Remove old preview if it exists
                     if (this.tempShape) this.tempShape.remove();

                     // Create new preview polygon including the mouse position
                     this.tempShape = L.polygon([...this.polygonPoints, e.latlng], {
                             color: '#ff0000',
                             weight: 2,
                             fillOpacity: 0.2
                         }).addTo(this.map);
                 } else {
                     // If less than 2 points, ensure polygon preview is removed
                     if (this.tempShape) {
                         this.tempShape.remove();
                         this.tempShape = null;
                     }
                 }
             }
             return;
        }

        // Box or Circle preview on mouse move
        // Only create preview if centerPoint is set (first click happened)
        if (!this.centerPoint) return;

        const currentPos = e.latlng;

        // Remove previous temporary shape preview
        if (this.tempShape) {
            this.tempShape.remove();
            this.tempShape = null;
        }

        // Create new temporary shape preview based on mode
        if (this.currentMode === 'box') {
            const bounds = L.latLngBounds([this.centerPoint, currentPos]);
            this.tempShape = L.rectangle(bounds, {
                color: '#ff0000',
                weight: 2,
                fillOpacity: 0.2,
                dashArray: '5,5'
            }).addTo(this.map);
        }
        else if (this.currentMode === 'circle') {
            const radius = this.centerPoint.distanceTo(currentPos);
            this.tempShape = L.circle(this.centerPoint, {
                radius: radius,
                color: '#ff0000',
                weight: 2,
                fillOpacity: 0.2,
                dashArray: '5,5'
            }).addTo(this.map);
        }
    }


    finalizePolygon() {
        // Ensure at least 3 points before finalizing
        if (this.polygonPoints.length >= 3) {
             // Capture the points array here
            const finalizedShapeData = {
                type: 'polygon',
                points: [...this.polygonPoints], // Store a copy of the points array
                layer: L.polygon(this.polygonPoints, { color: '#3388ff', weight: 2 }) // Create final layer from points
            };

            if (this.onShapeFinalized) {
                this.onShapeFinalized(finalizedShapeData);
            }

            console.log("Polygon finalized.");
            // Reset creation state after finalizing
            this.cancelCreation(); // This also removes temp layers and resets mode
        } else {
             console.warn("Not enough points to finalize polygon. Cancelling.");
             // If finalized with less than 3 points (e.g., by double-clicking too early), cancel.
             this.cancelCreation();
        }
    }

    // Accepts the final click position for box/circle calculation and the completed mode
    createFinalShape(finalLatlng, completedMode) {
         if (!this.centerPoint || !finalLatlng) return null; // Need both points

        let finalLayer = null;
        let shapeData = { type: completedMode }; // Use the captured completed mode

        if (completedMode === 'box') { // Use completedMode here
            const bounds = L.latLngBounds([this.centerPoint, finalLatlng]);
             // Store the bounds directly in shapeData
            shapeData.bounds = bounds;
            finalLayer = L.rectangle(bounds, { color: '#3388ff', weight: 2 });
        }
        else if (completedMode === 'circle') { // Use completedMode here
            const radius = this.centerPoint.distanceTo(finalLatlng);
             // Store center and radius directly in shapeData
            shapeData.center = this.centerPoint;
            shapeData.radius = radius;
            finalLayer = L.circle(this.centerPoint, { radius: radius, color: '#3388ff', weight: 2 });
        } else {
             // This method is not used for polygons, but handle defensively
             console.warn(`createFinalShape called for unexpected mode: ${completedMode}`);
             return null;
        }

         // Add the created layer to the shape data
         shapeData.layer = finalLayer;

        return shapeData;
    }
}

// ===============================================================
// ShapeListManager Class
// Manages the UI list of shapes in the sidebar
// ===============================================================
class ShapeListManager {
    constructor(listContainerId, mapManager) {
        this.listContainer = document.getElementById(listContainerId);
        this.mapManager = mapManager; // Needs access to MapManager to get shape data and remove layers
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Add a single event listener to the container and use delegation
        this.listContainer.addEventListener('click', (e) => {
            // Check if the clicked element or one of its ancestors is the delete button
            const deleteButton = e.target.closest('.delete-btn');
            if (deleteButton) {
                 // Get the index from the data attribute of the delete button
                const index = parseInt(deleteButton.dataset.index, 10);
                if (!isNaN(index)) { // Ensure index is a valid number
                    this.deleteShape(index);
                } else {
                     console.error("Could not get valid index from delete button data attribute.");
                }
            }
        });
    }

    updateList() {
        const shapes = this.mapManager.getShapes(); // Get shapes from the central store
        this.listContainer.innerHTML = ''; // Clear current list

        shapes.forEach((shape, index) => {
            const div = document.createElement('div');
            div.className = 'p-2 bg-white rounded shadow text-sm flex justify-between items-center';

            // Use getShapeInfoText from the mapManager instance
            const shapeInfoHtml = this.mapManager.getShapeInfoText(shape);

            div.innerHTML = `
                <div>
                    <strong>${shape.type.charAt(0).toUpperCase() + shape.type.slice(1)} ${index + 1}</strong><br>
                    ${shapeInfoHtml}
                </div>
                <button class="delete-btn" data-index="${index}">×</button>
            `;
            this.listContainer.appendChild(div);
        });
    }

    deleteShape(index) {
        // Remove the shape from the map and the central storage via MapManager
        this.mapManager.removeShapeLayer(index);
        // Update the UI list after removal (MapManager already updated its array)
        this.updateList();
        console.log(`Deleted shape at index ${index}`);
    }
}

// ===============================================================
// UI Manager
// Handles button styling and interaction based on current mode
// ===============================================================
class UIManager {
    constructor(shapeCreator) {
        this.shapeCreator = shapeCreator;
        this.modeButtons = {
            box: document.getElementById('boxBtn'),
            circle: document.getElementById('circleBtn'),
            polygon: document.getElementById('polygonBtn')
        };
        this.setupEventListeners();
    }

    setupEventListeners() {
        Object.entries(this.modeButtons).forEach(([mode, btn]) => {
            btn.addEventListener('click', () => {
                // Set the mode in the ShapeCreator
                this.shapeCreator.setMode(mode);
                // Update the button states based on the new mode
                this.updateButtonStates();
            });
        });
    }

    updateButtonStates() {
        const currentMode = this.shapeCreator.getMode(); // Get the mode from ShapeCreator

        Object.entries(this.modeButtons).forEach(([mode, btn]) => {
            // Remove all potential mode colors first
            btn.classList.remove('bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-gray-300');

            if (currentMode === mode) {
                // Add the active color for the current mode
                const colorClass = {
                    box: 'bg-blue-500',
                    circle: 'bg-green-500',
                    polygon: 'bg-purple-500'
                }[mode];
                btn.classList.add(colorClass);
            } else {
                // Add the default color for inactive modes
                btn.classList.add('bg-gray-300');
            }
        });
    }

     // Call this when creation is cancelled from map interaction
     handleCreationCancelled() {
         // Reset the mode in the ShapeCreator
         // Note: cancelCreation already sets mode to null internally
         // Just need to update the UI state to reflect this.
         this.updateButtonStates();
     }
}

// ===============================================================
// App Initialization
// ===============================================================
let mapManager;
let shapeCreator;
let shapeListManager;
let uiManager;

function initializeApp() {
    // 1. Initialize the Map Manager
    mapManager = new MapManager('map');
    const map = mapManager.init(); // Get the Leaflet map instance

    // 2. Initialize the UI Manager (needs to exist before ShapeCreator might cancel creation)
     uiManager = new UIManager(shapeCreator); // Initialize UIManager here

    // 3. Initialize the Shape Creator
    // Pass callbacks to update the list and UI when shapes are finalized or cancelled
    shapeCreator = new ShapeCreator(
        map,
        (finalizedShapeData) => {
            // Callback when a shape is successfully created
            mapManager.addShapeLayer(finalizedShapeData); // Add to map and storage
            shapeListManager.updateList(); // Update the sidebar list
            uiManager.updateButtonStates(); // Update button state (should reset)
        },
        () => {
            // Callback for when creation is cancelled (e.g., right-click)
            uiManager.handleCreationCancelled(); // Update UI state (should reset buttons)
        }
    );
    shapeCreator.activate(); // Start listening to map events

    // Now that shapeCreator is created, link it to the uiManager
    // (Could pass shapeCreator to UIManager constructor initially, but this works too)
    uiManager.shapeCreator = shapeCreator; // Ensure uiManager has the correct shapeCreator instance

    // 4. Initialize the Shape List Manager (needs mapManager reference)
    shapeListManager = new ShapeListManager('shapeList', mapManager);
    shapeListManager.updateList(); // Render initial empty list

     // Set initial button states after everything is wired up
     uiManager.updateButtonStates();


    console.log("App initialized.");
}

// Initialize the application when the DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);