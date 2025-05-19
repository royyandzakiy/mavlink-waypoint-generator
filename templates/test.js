let map;
let currentMode = null;
let creationInProgress = false;
let centerPoint = null;
let tempMarker = null;
let tempShape = null;
let tempPolyLine = null;
let polygonPoints = [];
const shapes = [];
let lastClickTime = 0;

function initMap() {
    map = L.map('map').setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    
    map.on('click', handleMapClick);
    map.on('dblclick', handleMapDoubleClick);
    map.on('mousemove', handleMapMove);
    map.on('contextmenu', handleRightClick);
}

function handleRightClick(e) {
    e.originalEvent.preventDefault();
    cancelAllOperations();
}

function cancelAllOperations() {
    currentMode = null;
    creationInProgress = false;
    centerPoint = null;
    polygonPoints = [];
    
    if (tempMarker) tempMarker.remove();
    if (tempShape) tempShape.remove();
    if (tempPolyLine) tempPolyLine.remove();
    
    tempMarker = null;
    tempShape = null;
    tempPolyLine = null;
    
    setButtonStates();
    updateShapeList();
}

function handleMapDoubleClick(e) {
    if (currentMode === 'polygon' && creationInProgress) {
        e.originalEvent.preventDefault();
        if (polygonPoints.length >= 3) {
            finalizePolygon();
        } else {
            cancelAllOperations();
        }
    }
}

function handleMapClick(e) {
    if (!currentMode) return;

    if (currentMode === 'polygon') {
        const now = Date.now();
        if (now - lastClickTime < 300) return; // Ignore double-click component
        lastClickTime = now;

        if (!creationInProgress) {
            polygonPoints = [e.latlng];
            creationInProgress = true;
            addPolygonPoint(e.latlng);
        } else {
            addPolygonPoint(e.latlng);
        }
        return;
    }

    if (!creationInProgress) {
        centerPoint = e.latlng;
        creationInProgress = true;
        
        tempMarker = L.circleMarker(centerPoint, {
            radius: 5,
            color: '#ff0000'
        }).addTo(map);
    } else {
        creationInProgress = false;
        tempMarker.remove();
        
        if (tempShape) {
            const finalizedShape = createFinalShape();
            if (finalizedShape) {
                shapes.push(finalizedShape);
                addShapeToMap(finalizedShape);
                updateShapeList();
            }
            
            tempShape.remove();
            tempShape = null;
        }
        
        centerPoint = null;
    }
}

function handlePolygonClick(e) {
    if (!creationInProgress) {
        // Start new polygon
        polygonPoints = [e.latlng];
        creationInProgress = true;
        addPolygonPoint(e.latlng);
    } else {
        // Check if clicking first point
        const firstPoint = polygonPoints[0];
        const distance = e.latlng.distanceTo(firstPoint);
        
        if (distance < 10 && polygonPoints.length >= 3) {
            // Complete polygon
            finalizePolygon();
        } else {
            // Add new point
            addPolygonPoint(e.latlng);
        }
    }
}

function addPolygonPoint(point) {
    polygonPoints.push(point);
    
    // Update temp shapes
    if (tempPolyLine) tempPolyLine.remove();
    if (tempShape) tempShape.remove();
    
    // Create polyline
    tempPolyLine = L.polyline(polygonPoints, {
        color: '#ff0000',
        weight: 2,
        dashArray: '5,5'
    }).addTo(map);
    
    // Create polygon preview
    if (polygonPoints.length >= 3) {
        tempShape = L.polygon(polygonPoints, {
            color: '#ff0000',
            weight: 2,
            fillOpacity: 0.2
        }).addTo(map);
    }
}

function finalizePolygon() {
    if (polygonPoints.length >= 3) {
        const finalizedShape = {
            type: 'polygon',
            points: polygonPoints,
            layer: L.polygon(polygonPoints, { color: '#3388ff', weight: 2 })
        };
        
        shapes.push(finalizedShape);
        addShapeToMap(finalizedShape);
        updateShapeList();
    }
    
    cancelAllOperations();
}

function createFinalShape() {
    if (!tempShape) return null;
    
    return {
        type: currentMode,
        center: centerPoint,
        bounds: tempShape.getBounds ? tempShape.getBounds() : null,
        radius: tempShape.getRadius ? tempShape.getRadius() : null,
        layer: currentMode === 'box' 
            ? L.rectangle(tempShape.getBounds(), { color: '#3388ff', weight: 2 })
            : L.circle(centerPoint, { radius: tempShape.getRadius(), color: '#3388ff', weight: 2 })
    };
}

function addShapeToMap(shape) {
    shape.layer.addTo(map);
    shape.layer.on('click', () => {
        alert(`Clicked ${shape.type}!\n${getShapeInfoText(shape)}`);
    });
}

function updateShapeList() {
    const listContainer = document.getElementById('shapeList');
    listContainer.innerHTML = '';
    
    shapes.forEach((shape, index) => {
        const div = document.createElement('div');
        div.className = 'p-2 bg-white rounded shadow text-sm';
        div.innerHTML = `
            <strong>${shape.type.charAt(0).toUpperCase() + shape.type.slice(1)} ${index + 1}</strong><br>
            ${getShapeInfoText(shape)}
        `;
        listContainer.appendChild(div);
    });
}

function getShapeInfoText(shape) {
    if (shape.type === 'box') {
        const bounds = shape.bounds;
        const ne = bounds.getNorthEast();
        const sw = bounds.getSouthWest();
        return `
            NW: ${ne.lat.toFixed(4)}, ${sw.lng.toFixed(4)}<br>
            NE: ${ne.lat.toFixed(4)}, ${ne.lng.toFixed(4)}<br>
            SE: ${sw.lat.toFixed(4)}, ${ne.lng.toFixed(4)}<br>
            SW: ${sw.lat.toFixed(4)}, ${sw.lng.toFixed(4)}
        `;
    } else if (shape.type === 'circle') {
        return `
            Center: ${shape.center.lat.toFixed(4)}, ${shape.center.lng.toFixed(4)}<br>
            Radius: ${shape.radius.toFixed(2)} meters
        `;
    } else if (shape.type === 'polygon') {
        return shape.points.map((point, i) => 
            `Point ${i+1}: ${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`
        ).join('<br>');
    }
    return '';
}

function handleMapMove(e) {
    if (!creationInProgress || !currentMode) return;

    if (currentMode === 'polygon') {
        if (polygonPoints.length > 0) {
            const currentPoints = [...polygonPoints, e.latlng];
            
            if (tempPolyLine) {
                tempPolyLine.setLatLngs(currentPoints);
            }
            
            if (polygonPoints.length >= 2 && tempShape) {
                tempShape.setLatLngs(currentPoints);
            }
        }
        return;
    }

    const currentPos = e.latlng;
    
    if (tempShape) {
        tempShape.remove();
        tempShape = null;
    }

    if (currentMode === 'box') {
        const bounds = L.latLngBounds([centerPoint, currentPos]);
        tempShape = L.rectangle(bounds, {
            color: '#ff0000',
            weight: 2,
            fillOpacity: 0.2,
            dashArray: '5,5'
        }).addTo(map);
    }
    else if (currentMode === 'circle') {
        const radius = centerPoint.distanceTo(currentPos);
        tempShape = L.circle(centerPoint, {
            radius: radius,
            color: '#ff0000',
            weight: 2,
            fillOpacity: 0.2,
            dashArray: '5,5'
        }).addTo(map);
    }
}

function setMode(mode) {
    currentMode = mode;
    setButtonStates();
    resetCreationState();
}

function setButtonStates() {
    const buttons = {
        box: document.getElementById('boxBtn'),
        circle: document.getElementById('circleBtn'),
        polygon: document.getElementById('polygonBtn')
    };

    Object.entries(buttons).forEach(([key, btn]) => {
        btn.classList.remove('bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-gray-300');
        btn.classList.add('bg-gray-300');
        
        if (currentMode === key) {
            const colorClass = {
                box: 'bg-blue-500',
                circle: 'bg-green-500',
                polygon: 'bg-purple-500'
            }[key];
            btn.classList.add(colorClass);
        }
    });
}

function resetCreationState() {
    creationInProgress = false;
    centerPoint = null;
    polygonPoints = [];
    if (tempMarker) tempMarker.remove();
    if (tempShape) tempShape.remove();
    if (tempPolyLine) tempPolyLine.remove();
    tempMarker = null;
    tempShape = null;
    tempPolyLine = null;
}

initMap();