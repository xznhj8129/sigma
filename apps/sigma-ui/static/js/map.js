

// Initialize variables
var currentMode = "";
var change = true;
var pointCounter = 1;
var tgtCounter = 0;
var homeMarker = null;
var landMarker = null;
var surveyLines = [];
var pointMarkers = [];
var surveyMarkers = [];
var map; // Global map variable
var drawnItems; // Declare drawnItems globally
var isDrawing = false; // Track if a draw operation is active
var unitMarkers = new Map();
var shapeTools = false;
var selectedUnitCode = null;
var selectedUnitName = null;
var selectedTaskPoint = null;
var waitingForTaskPoint = false;
var taskSidebarOpen = false;
var taskPointMarker = null;
var selectedGeometry = null;
var shapeLayers = new Map();
var unitTaskLines = new Map();
var activeTasksByUnit = new Map();
var latestUnits = [];
var takMarkers = new Map();
var latestTak = [];
var streamClient = null;

function isStreamOpen() {
    return streamClient && streamClient.ws && streamClient.ws.readyState === WebSocket.OPEN;
}

function setActiveTasks(tasks) {
    activeTasksByUnit.clear();
    (tasks || []).forEach(t => {
        if (!t.unit_code) return;
        const existing = activeTasksByUnit.get(t.unit_code);
        if (!existing) {
            activeTasksByUnit.set(t.unit_code, t);
            return;
        }
        const prevTs = existing.last_update || 0;
        const newTs = t.last_update || 0;
        if (newTs >= prevTs) {
            activeTasksByUnit.set(t.unit_code, t);
        }
    });
}


/**
 * Opens the Bootstrap modal to add or edit shape properties.
 * @param {L.Layer} layer - The Leaflet layer (shape) to edit.
 * @param {object|null} existingData - Null for new shapes, or object with existing data.
 */
function openShapeEditorModal(layer, existingData = null) {
    activeLayerForModal = layer;
    isNewShape = (existingData === null);

    const modalTitle = document.getElementById('shapeEditorModalLabel');
    const categoryEl = document.getElementById('shape-category');
    const descriptionEl = document.getElementById('shape-description');
    const datetimeEl = document.getElementById('shape-datetime');
    const colorEl = document.getElementById('shape-color');
    const nameEl = document.getElementById('shape-name');

    if (isNewShape) {
        modalTitle.textContent = "Add Shape Details";
        // Reset form to defaults
        categoryEl.value = 'Area of Interest';
        descriptionEl.value = '';
        datetimeEl.value = new Date().toISOString().slice(0, 16);
        if (colorEl) colorEl.value = '#97009c';
        if (nameEl) nameEl.value = '';
    } else {
        modalTitle.textContent = "Edit Shape Details";
        // Populate form with existing data
        categoryEl.value = existingData.properties.category || 'Area of Interest';
        descriptionEl.value = existingData.properties.description || '';
        datetimeEl.value = existingData.properties.datetime || new Date().toISOString().slice(0, 16);
        if (colorEl) colorEl.value = existingData.properties.color || '#97009c';
        if (nameEl) nameEl.value = existingData.properties.name || '';
    }

    shapeEditorModalInstance.show();
}


/**
 * Handles the logic when the 'Save' button in the modal is clicked.
 */
function handleSaveShape() {
    if (!activeLayerForModal) return;

    // 1. Gather form data
    const properties = {
        category: document.getElementById('shape-category').value,
        description: document.getElementById('shape-description').value,
        datetime: document.getElementById('shape-datetime').value,
        color: document.getElementById('shape-color').value,
        name: document.getElementById('shape-name').value,
    };

    // 2. Get the GeoJSON representation of the layer
    const shapeGeoJson = activeLayerForModal.toGeoJSON();
    shapeGeoJson.properties = shapeGeoJson.properties || {};
    
    // 3. Construct the payload
    const payload = {
        ...shapeGeoJson,
        properties: { ...shapeGeoJson.properties, ...properties } // Merge properties
    };
    
    let apiUrl, apiMethod;

    if (isNewShape) {
        apiUrl = '/api/map/add_shape';
        apiMethod = 'POST';
    } else {
        // Assumes existing shape data is stored in feature.id
        const shapeId = activeLayerForModal.feature.id;
        apiUrl = `/api/map/update_shape/${shapeId}`;
        apiMethod = 'PUT';
        payload.id = shapeId; // Ensure ID is in payload for update
    }

    // 4. Send to backend
    fetch(apiUrl, {
        method: apiMethod,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) throw new Error(`API request failed: ${response.statusText}`);
        return response.json();
    })
    .then(savedFeature => {
        // The API should return the saved feature, including its new/updated state and ID
        console.log('Shape saved successfully:', savedFeature);

        // Permanently add the layer to the map and store its data
        drawnItems.addLayer(activeLayerForModal);
        const featureData = savedFeature || {};
        featureData.properties = featureData.properties || payload.properties || {};
        activeLayerForModal.feature = featureData; // Update layer's feature data

        // Re-bind the click listener for future edits
        // Popup with edit and select controls
        const props = featureData.properties;
        const label = props.name || props.category || 'Shape';
        const popupContent = `
            <div>
              <strong>${label}</strong><br>${props.description || ''}
              <div class="mt-2 d-flex gap-1">
                <button class="btn btn-sm btn-primary" onclick="window._editShape('${featureData.id}')">Edit</button>
                <button class="btn btn-sm btn-secondary" onclick="window._selectShape('${featureData.id}')">Select</button>
              </div>
            </div>`;
        activeLayerForModal.bindPopup(popupContent);
        if (activeLayerForModal.setStyle && props.color) {
            activeLayerForModal.setStyle({ color: props.color, weight: 2, fillOpacity: 0.1 });
        }

        selectedGeometry = featureData;
        if (featureData.id) {
            shapeLayers.set(featureData.id, activeLayerForModal);
        }

        shapeEditorModalInstance.hide();
    })
    .catch(error => {
        console.error('Error saving shape:', error);
        alert('Error saving shape. See console for details.');
    });
}


function updateTaskPanel(tasks) {
    const currentTaskLabel = document.getElementById('current-task-label');
    const destLabel = document.getElementById('task-destination-label');
    if (!currentTaskLabel) {
        return;
    }

    if (!tasks || tasks.length === 0) {
        currentTaskLabel.textContent = 'None';
        if (destLabel) destLabel.textContent = 'None';
        clearTaskPointMarker();
        return;
    }

    const active = tasks.find(t => t.status !== 'complete') || tasks[0];
    if (active.task_type === 'move' && active.destination) {
        const dest = active.destination;
        currentTaskLabel.textContent = `${active.status}: Move to ${dest.lat.toFixed(5)}, ${dest.lon.toFixed(5)}`;
        if (destLabel) destLabel.textContent = `${dest.lat.toFixed(5)}, ${dest.lon.toFixed(5)}`;
        setTaskPointMarker({ lat: dest.lat, lng: dest.lon });
        return;
    }

    currentTaskLabel.textContent = `${active.status}: ${active.task_type}`;
    if (destLabel) destLabel.textContent = active.task_type;
}

function handleStreamMessage(type, data) {
    if (type === 'units') {
        latestUnits = data || [];
        drawUnits(latestUnits);
        return;
    }
    if (type === 'tasks') {
        setActiveTasks(data);
        drawUnits(latestUnits);
    }
}

function loadUnitTasks(unitCode) {
    fetch(`/api/map/tasks/${unitCode}`)
        .then(res => res.ok ? res.json() : Promise.reject(res.statusText))
        .then(updateTaskPanel)
        .catch(err => console.error('Failed to load tasks', err));
}

function selectUnit(unitCode, unitName) {
    selectedUnitCode = unitCode;
    selectedUnitName = unitName;
    selectedTaskPoint = null;
    waitingForTaskPoint = false;
    clearTaskPointMarker();
    openTaskSidebar();

    const unitLabel = document.getElementById('selected-unit-label');
    const destLabel = document.getElementById('task-destination-label');
    if (unitLabel) {
        unitLabel.textContent = `${unitName}`;
    }
    if (destLabel) {
        destLabel.textContent = 'None';
    }
    updateTaskPanel([]);
    loadUnitTasks(unitCode);
}

function beginTaskPointSelection() {
    waitingForTaskPoint = true;
}

function useSelectedShapeAsTarget() {
    if (!selectedGeometry || !selectedGeometry.geometry) {
        console.warn('Select a shape first');
        return;
    }
    if (selectedGeometry.id) {
        highlightShape(selectedGeometry.id);
    }
    const center = L.geoJSON(selectedGeometry).getBounds().getCenter();
    selectedTaskPoint = center;
    const destLabel = document.getElementById('task-destination-label');
    if (destLabel) {
        const name = selectedGeometry.properties?.name || selectedGeometry.id || '';
        destLabel.textContent = `Shape ${name}: ${center.lat.toFixed(5)}, ${center.lng.toFixed(5)}`;
    }
    setTaskPointMarker(center);
}

function submitTask() {
    if (!selectedUnitCode) {
        console.warn('Select a unit before tasking');
        return;
    }
    if (!selectedTaskPoint) {
        console.warn('Pick a destination on the map before tasking');
        return;
    }

    const taskType = document.getElementById('task-type')?.value || 'move';
    if (taskType !== 'move') {
        console.warn('Only move tasks are supported');
        return;
    }

    const speedField = document.getElementById('task-speed');
    const speedValue = speedField && speedField.value ? parseFloat(speedField.value) : null;
    if (speedValue !== null && Number.isNaN(speedValue)) {
        console.warn('Speed must be numeric km/h');
        return;
    }

    const taskId = crypto.randomUUID ? crypto.randomUUID() : `TASK-${Date.now()}`;
    const payload = {
        task_id: taskId,
        task_type: taskType,
        unit_code: selectedUnitCode,
    };

    const pointPayload = {
        lat: selectedTaskPoint.lat,
        lon: selectedTaskPoint.lng,
        alt: selectedTaskPoint.alt || 0
    };

    if (speedValue !== null) {
        payload.speed_ms = speedValue / 3.6;
    }

    if (taskType === 'move') {
        payload.destination = pointPayload;
    } else if (taskType === 'attack') {
        payload.target_point = pointPayload;
        payload.destination = pointPayload;
    } else if (taskType === 'isr') {
        payload.area = { vertices: [pointPayload] };
        payload.destination = pointPayload;
    } else if (taskType === 'resupply') {
        payload.destination = pointPayload;
        payload.payload = {};
    } else if (taskType === 'hold') {
        payload.location = pointPayload;
        payload.radius_m = 25;
    }

    if (selectedGeometry && selectedGeometry.id) {
        payload.geometry_id = selectedGeometry.id;
    }

    fetch('/api/map/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(res.statusText);
        }
        return res.json();
    })
    .then(task => {
        selectedTaskPoint = null;
        const destLabel = document.getElementById('task-destination-label');
        if (destLabel) {
            destLabel.textContent = 'Queued';
        }
        updateTaskPanel([task]);
        loadUnitTasks(task.unit_code);
        clearTaskPointMarker();
    })
    .catch(err => {
        console.error('Failed to submit task', err);
    });
}

function openTaskSidebar() {
    const sidebar = document.getElementById('task-sidebar');
    if (!sidebar) return;
    sidebar.classList.add('open');
    taskSidebarOpen = true;
    if (map) {
        setTimeout(() => map.invalidateSize(), 200);
    }
}

function closeTaskSidebar() {
    const sidebar = document.getElementById('task-sidebar');
    if (!sidebar) return;
    sidebar.classList.remove('open');
    taskSidebarOpen = false;
    clearTaskPointMarker();
    if (map) {
        setTimeout(() => map.invalidateSize(), 200);
    }
}

function toggleTaskSidebar() {
    if (taskSidebarOpen) {
        closeTaskSidebar();
    } else {
        openTaskSidebar();
    }
}

function setTaskPointMarker(latlng) {
    if (!map) return;
    if (taskPointMarker) {
        map.removeLayer(taskPointMarker);
    }
    taskPointMarker = L.marker(latlng, { draggable: false, opacity: 0.9 });
    taskPointMarker.addTo(map);
}

function clearTaskPointMarker() {
    if (taskPointMarker && map) {
        map.removeLayer(taskPointMarker);
    }
    taskPointMarker = null;
}

function highlightShape(shapeId) {
    shapeLayers.forEach((layer, id) => {
        const props = layer.feature?.properties || {};
        const color = props.color || '#97009c';
        const style = (id === shapeId)
            ? { color: '#ffffff', weight: 3, fillOpacity: 0.2 }
            : { color: color, weight: 2, fillOpacity: 0.1 };
        if (layer.setStyle) {
            layer.setStyle(style);
        }
    });
}

function cancelTasksForUnit() {
    if (!selectedUnitCode) {
        console.warn('No unit selected to cancel');
        return;
    }
    fetch(`/api/map/tasks/cancel/${selectedUnitCode}`, { method: 'POST' })
        .then(res => res.ok ? res.json() : Promise.reject(res.statusText))
        .then(() => {
            updateTaskPanel([]);
            clearTaskPointMarker();
        })
        .catch(err => console.error('Failed to cancel tasks', err));
}


function updateTaskLines(unitsData) {
    if (!Array.isArray(unitsData) || unitsData.length === 0) {
        return;
    }
    unitsData.forEach(u => {
        let latlon, unitCode;
        if (Array.isArray(u)) {
            [latlon,, , , unitCode] = u;
        } else if (u && typeof u === 'object' && u.position) {
            latlon = [u.position.lat, u.position.lon];
            unitCode = u.unit_code;
        } else {
            return;
        }
        if (!unitCode) return;
        const task = activeTasksByUnit.get(unitCode);
        if (!task || !task.destination || task.status === 'complete') {
            const existingLine = unitTaskLines.get(unitCode);
            if (existingLine) {
                map.removeLayer(existingLine);
                unitTaskLines.delete(unitCode);
            }
            return;
        }
        const start = L.latLng(latlon[0], latlon[1]);
        const dest = L.latLng(task.destination.lat, task.destination.lon);
        let line = unitTaskLines.get(unitCode);
        if (line) {
            line.setLatLngs([start, dest]);
        } else {
            line = L.polyline([start, dest], { color: '#00ff66', weight: 2, opacity: 0.6, dashArray: '4,4' });
            line.isTaskLine = true;
            line.addTo(map);
            unitTaskLines.set(unitCode, line);
        }
    });
}

function drawUnits(unitsData) {
    const bounds = map.getBounds();
    const visibleUnitCodes = new Set();
    latestUnits = unitsData || latestUnits;

    unitsData.forEach(u => {
        let latlon, sidc, callsign, unitName, unitCode;
        if (Array.isArray(u)) {
            [latlon, sidc, callsign, unitName, unitCode] = u;
        } else if (u && typeof u === 'object' && u.position) {
            if (u.position.lat === undefined || u.position.lon === undefined) {
                throw new Error('Bad unit position: ' + JSON.stringify(u));
            }
            latlon = [u.position.lat, u.position.lon];
            sidc = u.sidc;
            callsign = u.callsign || "";
            unitName = u.name || u.unit_name || u.unit_code;
            unitCode = u.unit_code;
        } else {
            throw new Error('Bad unit payload: ' + JSON.stringify(u));
        }
        if (!unitCode) {
            throw new Error('Unit code missing for ' + unitName);
        }
        const latLng = L.latLng(latlon[0], latlon[1]);
        if (!bounds.contains(latLng)) {
            return;
        }

        const popup = `
        <div style="width:200px">
          <strong>${unitName}</strong><br/>
          <em>${callsign} (${unitCode})</em>
        </div>`;

        const existing = unitMarkers.get(unitCode);
        if (existing) {
            existing.marker.setLatLng(latLng);
            if (existing.sidc !== sidc || existing.callsign !== callsign || existing.unitName !== unitName) {
                const updatedSymbol = new ms.Symbol(sidc, { uniqueDesignation: callsign }).setOptions({ size: 25 });
                const updatedAnchor = updatedSymbol.getAnchor();
                const updatedSize = updatedSymbol.getSize();
                const updatedIcon = L.divIcon({
                    html: updatedSymbol.asSVG(),
                    className: 'milsymbol-icon',
                    iconSize: [updatedSize.width, updatedSize.height],
                    iconAnchor: [updatedAnchor.x, updatedAnchor.y]
                });
                existing.marker.setIcon(updatedIcon);
                existing.marker.setPopupContent(popup);
                existing.sidc = sidc;
                existing.callsign = callsign;
                existing.unitName = unitName;
            }
            existing.marker.off('click').on('click', () => selectUnit(unitCode, unitName));
        } else {
            let symbol;
            try {
                symbol = new ms.Symbol(sidc, { uniqueDesignation: callsign }).setOptions({ size: 25 });
            } catch (err) {
                console.warn('Bad SIDC for', unitName, sidc, err);
                return;
            }

            const svg = symbol.asSVG();
            if (!svg.trim()) {
                console.warn('milsymbol produced empty SVG for', unitName);
                return;
            }

            const anchor = symbol.getAnchor();
            const size = symbol.getSize();

            const myIcon = L.divIcon({
                html: svg,
                className: 'milsymbol-icon',
                iconSize: [size.width, size.height],
                iconAnchor: [anchor.x, anchor.y]
            });

            const marker = L.marker(latLng, { icon: myIcon })
                            .addTo(map)
                            .bindPopup(popup);
            marker.isUnitMarker = true;
            marker.on('click', () => selectUnit(unitCode, unitName));
            unitMarkers.set(unitCode, {
                marker: marker,
                sidc: sidc,
                callsign: callsign,
                unitName: unitName
            });
        }

        visibleUnitCodes.add(unitCode);
    });

    for (const [code, entry] of unitMarkers.entries()) {
        if (!visibleUnitCodes.has(code)) {
            map.removeLayer(entry.marker);
            unitMarkers.delete(code);
        }
    }
    updateTaskLines(unitsData);
}

function drawTakMarkers(takData) {
    const bounds = map.getBounds();
    const visible = new Set();
    (takData || []).forEach(m => {
        if (!m || m.lat === undefined || m.lon === undefined) {
            throw new Error('Bad tak marker payload: ' + JSON.stringify(m));
        }
        const uid = m.uid || m.callsign || m.cot;
        if (!uid) {
            throw new Error('Missing uid for tak marker: ' + JSON.stringify(m));
        }
        const latLng = L.latLng(m.lat, m.lon);
        if (!bounds.contains(latLng)) {
            return;
        }
        const name = m.callsign || m.cot || uid;
        const popup = `
        <div style="width:220px">
          <strong>${name}</strong><br/>
          <em>${m.cot || ''}</em><br/>
          Affiliation: ${m.affiliation || ''}<br/>
          How: ${m.how || ''}<br/>
          Time: ${m.time || ''}
        </div>`;
        const existing = takMarkers.get(uid);
        if (!m.sidc) {
            if (existing) {
                if (existing.marker.setLatLng) {
                    existing.marker.setLatLng(latLng);
                }
                existing.marker.setPopupContent(popup);
            } else {
                const marker = L.circleMarker(latLng, { radius: 6, color: '#00bcd4' }).addTo(map).bindPopup(popup);
                marker.isUnitMarker = true;
                takMarkers.set(uid, { marker: marker, sidc: null });
            }
        } else {
            const symbol = new ms.Symbol(m.sidc, { uniqueDesignation: name }).setOptions({ size: 25 });
            const svg = symbol.asSVG();
            if (!svg.trim()) {
                throw new Error('milsymbol empty svg for tak marker ' + uid);
            }
            const anchor = symbol.getAnchor();
            const size = symbol.getSize();
            const icon = L.divIcon({
                html: svg,
                className: 'milsymbol-icon',
                iconSize: [size.width, size.height],
                iconAnchor: [anchor.x, anchor.y]
            });

            if (existing) {
                existing.marker.setLatLng(latLng);
                existing.marker.setIcon(icon);
                existing.marker.setPopupContent(popup);
            } else {
                const marker = L.marker(latLng, { icon: icon }).addTo(map).bindPopup(popup);
                marker.isUnitMarker = true;
                takMarkers.set(uid, { marker: marker, sidc: m.sidc });
            }
        }
        visible.add(uid);
    });

    for (const [uid, entry] of takMarkers.entries()) {
        if (!visible.has(uid)) {
            map.removeLayer(entry.marker);
            takMarkers.delete(uid);
        }
    }
}

function activateDrawingTools() {
if (!shapeTools) {
    // Activate drawing tools

    drawControl = new L.Control.Draw({
    edit: { featureGroup: drawnItems, remove: true },
    draw: {
        polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: '#97009c' } },
        rectangle: { shapeOptions: { color: '#3388ff' } },
        circle: { shapeOptions: { color: '#ff0000' } },
        polyline: true,
        marker: true,
        circlemarker: false
    }
    });
    map.addControl(drawControl);
    shapeTools = true;
    console.log('Drawing tools enabled');
} else {
    // Deactivate drawing tools
    if (drawControl) map.removeControl(drawControl);
    shapeTools = false;
    console.log('Drawing tools disabled');
}
}

// Initialize the map
function initMap() {
    // Check if map container exists
    if (!document.getElementById('map')) {
        console.error('Map container not found');
        return;
    }

    // Create base layers
    var streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    });

    var topoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenTopoMap contributors'
    });

    var satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Tiles © Esri'
    });

    // Initialize map
    map = L.map('map', {
        center: [36.530310,-83.21722],
        zoom: 12,
        layers: [satelliteMap],
        zoomControl: true
    });

    // Add base maps control
    var baseMaps = {
        "Street Map": streetMap,
        "Topo Map": topoMap,
        "Satellite": satelliteMap
    };
    L.control.layers(baseMaps).addTo(map);

    // drawn map items
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    const layersBtn = document.getElementById('layers-btn');
    const drawBtn = document.getElementById('draw-btn');
    const measureBtn = document.getElementById('measure-btn');
    const searchBtn = document.getElementById('search-btn');
    const routeBtn = document.getElementById('route-btn');
    const clearBtn = document.getElementById('clear-btn');
    const saveBtn = document.getElementById('save-btn');
    const pickTaskBtn = document.getElementById('pick-task-point');
    const shapeTaskBtn = document.getElementById('use-shape-target');
    const submitTaskBtn = document.getElementById('submit-task');
    const toggleTaskBtn = document.getElementById('toggle-task-sidebar');
    const cancelTaskBtn = document.getElementById('cancel-task');
    
    // Layers button functionality
    layersBtn.addEventListener('click', function() {
        console.log('Layers button clicked');
        // Example: Toggle layers panel
        // toggleLayersPanel();
        alert('Layers functionality would go here');
    });
    
    // Draw button functionality
    drawBtn.addEventListener('click', function() {
        console.log('Draw button clicked');
        activateDrawingTools();
    });
    
    // Measure button functionality
    measureBtn.addEventListener('click', function() {
        console.log('Measure button clicked');
        // Example: Start measuring distance
        // startMeasuring();
        alert('Measurement tool activated');
    });
    
    // Search button functionality
    searchBtn.addEventListener('click', function() {
        console.log('Search button clicked');
        const query = prompt('Enter search location:');
        if (query) {
            // Example: searchLocation(query);
            alert(`Searching for: ${query}`);
        }
    });
    
    // Route button functionality
    routeBtn.addEventListener('click', function() {
        console.log('Route button clicked');
        // Example: calculateRoute();
        alert('Route calculation would start here');
    });
    
    // Clear button functionality
    clearBtn.addEventListener('click', function() {
        console.log('Clear button clicked');
        if (confirm('Are you sure you want to clear the map?')) {
            // Example: clearMap();
            alert('Map cleared');
        }
    });
    
    // Save button functionality
    saveBtn.addEventListener('click', function() {
        console.log('Save button clicked');
        const fileName = prompt('Enter a name for your map:');
        if (fileName) {
            // Example: saveMap(fileName);
            alert(`Map saved as: ${fileName}`);
        }
    });

    if (pickTaskBtn) {
        pickTaskBtn.addEventListener('click', beginTaskPointSelection);
    }

    if (shapeTaskBtn) {
        shapeTaskBtn.addEventListener('click', useSelectedShapeAsTarget);
    }

    if (submitTaskBtn) {
        submitTaskBtn.addEventListener('click', submitTask);
    }

    if (toggleTaskBtn) {
        toggleTaskBtn.addEventListener('click', toggleTaskSidebar);
    }

    if (cancelTaskBtn) {
        cancelTaskBtn.addEventListener('click', cancelTasksForUnit);
    }


    // --- Setup Bootstrap Modal ---
    const shapeModalElement = document.getElementById('shapeEditorModal');
    shapeEditorModalInstance = new bootstrap.Modal(shapeModalElement);

    document.getElementById('save-shape-btn').addEventListener('click', handleSaveShape);
    
    // Add a listener to clean up when the modal is closed without saving
    shapeModalElement.addEventListener('hidden.bs.modal', () => {
        if (isNewShape && activeLayerForModal && !drawnItems.hasLayer(activeLayerForModal)) {
            // If it was a new shape and was NOT added to drawnItems (i.e., cancelled), remove it from the map.
            map.removeLayer(activeLayerForModal);
        }
        activeLayerForModal = null; // Clear the active layer reference
    });


    // --- Leaflet.Draw Event Listeners ---
    map.on('draw:drawstart', () => { isDrawing = true; });
    map.on('draw:drawstop', () => { isDrawing = false; });

    map.on('draw:created', (e) => {
        isDrawing = false;
        const layer = e.layer;
        const props = {
            color: document.getElementById('shape-color')?.value || '#97009c'
        };
        if (layer.setStyle) {
            layer.setStyle({ color: props.color, weight: 2, fillOpacity: 0.1 });
        }
        // Temporarily add to map to be visible while modal is open
        layer.addTo(map);
        openShapeEditorModal(layer, null); // Open modal for a new shape
    });

    map.on('draw:edited', (e) => {
        e.layers.eachLayer((layer) => {
            // When a shape is edited, we just re-open the modal with its existing data.
            // The user can then confirm/change properties and save.
            if (layer.feature && layer.feature.id) {
                openShapeEditorModal(layer, layer.feature);
            }
        });
    });

    map.on('draw:deleted', (e) => {
        e.layers.eachLayer((layer) => {
            if (layer.feature && layer.feature.id) {
                const id = layer.feature.id;
                if (confirm('Are you sure you want to permanently delete this shape?')) {
                    fetch(`/api/map/delete_shape/${id}`, { method: 'DELETE' })
                        .then(res => {
                            if (!res.ok) throw new Error('Failed to delete');
                            console.log('Shape deleted from backend.');
                            change = true; // Trigger refresh
                            shapeLayers.delete(id);
                        })
                        .catch(err => {
                            alert('Error deleting shape.');
                            drawnItems.addLayer(layer); // Add it back if delete fails
                        });
                } else {
                    drawnItems.addLayer(layer); // User cancelled, so add it back
                }
            }
        });
    });

    // Force map resize in case it's in a hidden container
    setTimeout(function() {
        map.invalidateSize();
    }, 100);

    // Initialize with an update
    updateMap();

    // Set up click event listener
    map.on('click', function(e) {
        console.log('Map clicked, currentMode:', currentMode);
        if (waitingForTaskPoint) {
            selectedTaskPoint = e.latlng;
            const destLabel = document.getElementById('task-destination-label');
            if (destLabel) {
                destLabel.textContent = `${selectedTaskPoint.lat.toFixed(5)}, ${selectedTaskPoint.lng.toFixed(5)}`;
            }
            setTaskPointMarker(selectedTaskPoint);
            waitingForTaskPoint = false;
            return;
        }
        if (!isDrawing && currentMode != "survey-area") {
            let lat = e.latlng.lat;
            let lon = e.latlng.lng;
            console.log('Map clicked at:', lat, lon);

            fetch('/api/map/add_point', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: lat, lon: lon })
            }).then(response => {
                if (!response.ok) {
                    console.error('Error with the POST request:', response.statusText);
                }
                return response.ok ? response.json() : {};
            }).then(data => {
                change = true;
                updateMap();
            }).catch(error => {
                console.error('Fetch error:', error);
            });

            updateMap();
            save();
        }
    });

      
    // fetch & draw once at init
    fetch('/api/map/units')
    .then(res => res.json())
    .then(drawUnits)
    .catch(err => console.error('Failed to load units:', err));
    fetch('/api/map/tak')
    .then(res => res.json())
    .then(drawTakMarkers)
    .catch(err => console.error('Failed to load tak markers:', err));
      

    // Set up interval for updates
    setInterval(updateMap, 1000);

    // Streaming setup
    if (window.StreamClient) {
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.hostname;
    const port = window.location.port ? parseInt(window.location.port, 10) : (window.location.protocol === "https:" ? 443 : 80);
    const wsPort = port + 1; // aiohttp runs on Flask port + 1
    const url = `${proto}://${host}:${wsPort}/ws/stream`;
        streamClient = new StreamClient(url, { reconnectDelay: 1500 });
        streamClient.subscribe(['units', 'tasks'], handleStreamMessage);
    }
}

// Call initMap when window loads
window.addEventListener('load', initMap);

function updateMap() {
    const refreshTasksIfNeeded = () => {
        return fetch('/api/map/tasks_active')
            .then(res => res.json())
            .then(tasks => {
                if (Array.isArray(tasks)) {
                    if (tasks.length > 0 || activeTasksByUnit.size === 0) {
                        setActiveTasks(tasks);
                    }
                }
            })
            .catch(err => console.error('Failed to load tasks:', err));
    };

    const refreshUnits = () => {
        fetch('/api/map/units')
        .then(res => res.json())
        .then(units => {
            latestUnits = units;
            drawUnits(latestUnits);
        })
        .catch(err => console.error('Failed to load units:', err));
    };
    const refreshTak = () => {
        fetch('/api/map/tak')
        .then(res => res.json())
        .then(tak => {
            latestTak = tak;
            drawTakMarkers(latestTak);
        })
        .catch(err => console.error('Failed to load tak markers:', err));
    };

    if (change) {
        fetch('/api/map/markers')
        .then(response => response.json())
        .then(data => {
            if (!data) {
                return;
            }

            console.log('Map updated');

            map.eachLayer(function(layer) {
                if (layer instanceof L.TileLayer || layer.isUnitMarker || layer.isTaskLine) {
                    return;
                }
                map.removeLayer(layer);
            });
            
            map.addLayer(drawnItems);
            if (data.shapes && Array.isArray(data.shapes)) {
                data.shapes.forEach(feature => {
                    if (!feature.id) return;
                    const existing = shapeLayers.get(feature.id);
                    if (existing) {
                        existing.remove();
                    }
                    const layer = L.geoJSON(feature, { style: shapeStyleFromProps }).getLayers()[0];
                    if (!layer) return;
                    layer.feature = feature;
                    layer.addTo(map);
                    layer.on('click', (e) => {
                        if (waitingForTaskPoint) {
                            selectedTaskPoint = e.latlng;
                            const destLabel = document.getElementById('task-destination-label');
                            if (destLabel) {
                                destLabel.textContent = `${selectedTaskPoint.lat.toFixed(5)}, ${selectedTaskPoint.lng.toFixed(5)}`;
                            }
                            setTaskPointMarker(selectedTaskPoint);
                            waitingForTaskPoint = false;
                            return;
                        }
                        selectedGeometry = feature;
                        highlightShape(feature.id);
                        useSelectedShapeAsTarget();
                    });
                    shapeLayers.set(feature.id, layer);
                });
            }
            
            if (data.info_points && data.info_points.length > 0) {
                data.info_points.forEach(point => {
                    const popupContent = `
                            <div style="width: 250px;">
                                <h3>Info Point ${point.num}</h5>
                                <iframe src="${point.url}" style="width: 100%; height: 150px;" frameborder="0" sandbox></iframe>
                                <a href="${point.link}" target="_blank" class="btn btn-link mt-2">More Information</a>
                                <button onclick="handleButtonClick(${point.uuid})" class="btn btn-primary btn-sm mt-2">Action</button>
                            </div>
                        `;
                    //https://spatialillusions.com/unitgenerator/
                    var symbol = new ms.Symbol(
                        10031000000000000000, 
                        {uniqueDesignation: "test"});
                    symbol = symbol.setOptions({ size: 25 });
                    var myicon = L.divIcon({
                        className: '',
                        html: symbol.asSVG(),
                        iconAnchor: new L.Point(symbol.getAnchor().x, symbol.getAnchor().y)
                    });
                    L.marker(point.pos, { icon: myicon }).addTo(map).bindPopup(popupContent);
                });
            }
        })
        .catch(error => console.error('Error updating map:', error))
        .finally(() => {
            change = false;
            refreshTasksIfNeeded().finally(() => {
                refreshUnits();
                refreshTak();
            });
        });
        return;
    }

    refreshTasksIfNeeded().finally(() => {
        refreshUnits();
        refreshTak();
    });
}

    function undoLast() {
    }


    function clearAll() {
    }

    function save() {
    }


function initMapInGoldenLayout(containerElement) {
    if (!containerElement) {
        console.error('GoldenLayout container not provided');
        return;
    }

    // Create map div explicitly
    const mapDiv = document.createElement('div');
    mapDiv.id = 'map';
    mapDiv.style.width = '100%';
    mapDiv.style.height = '100%';
    containerElement.appendChild(mapDiv);

    // Call the existing init function
    initMap();
}
window._editShape = function(shapeId) {
    const layer = shapeLayers.get(shapeId);
    if (!layer) return;
    openShapeEditorModal(layer, layer.feature);
};

window._selectShape = function(shapeId) {
    const layer = shapeLayers.get(shapeId);
    if (!layer || !layer.feature) return;
    selectedGeometry = layer.feature;
    highlightShape(shapeId);
    useSelectedShapeAsTarget();
};

function shapeStyleFromProps(feature) {
    const color = feature?.properties?.color || '#97009c';
    return { color: color, weight: 2, fillOpacity: 0.1 };
}
