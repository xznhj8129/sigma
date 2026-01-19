var currentMode = "";
var change = true;
var pointCounter = 1;
var tgtCounter = 0;
var homeMarker = null;
var landMarker = null;
var surveyLines = [];
var pointMarkers = [];
var surveyMarkers = [];

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

var map = L.map('map', {
    center: [{{ location[0] }}, {{ location[1] }}],
    zoom: {{ zoom }},
    layers: [satelliteMap] // Set default layer here
});

var baseMaps = {
    "Street Map": streetMap,
    "Topo Map": topoMap,
    "Satellite": satelliteMap
};

L.control.layers(baseMaps).addTo(map);

var drawnItems = new L.FeatureGroup();
var drawControl = new L.Control.Draw({
    edit: {
        featureGroup: drawnItems,
        remove: true
    },
    draw: {
        polygon: {
            allowIntersection: false,
            showArea: true,
            shapeOptions: {
                color: '#97009c'
            }
        },
        rectangle: {
            shapeOptions: {
                color: '#3388ff'
            }
        },
        circle: {
            shapeOptions: {
                color: '#ff0000'
            }
        },
        polyline: false,
        marker: false,
        circlemarker: false
    }
});
map.addControl(drawControl);

var routeInPolyline = L.polyline([], {color: 'green'}).addTo(map);
var routeOutPolyline = L.polyline([], {color: 'green'}).addTo(map);

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('button').forEach(btn => btn.classList.remove('active-button'));
    var modebtn = "set-points-" + mode;
    document.getElementById(modebtn.replace('_', '-')).classList.add('active-button');
    var missionType = document.getElementById('missiontypemenu').value;
    fetch('/api/planner/set_mode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            mode: currentMode,
            type: missionType
        }),
    });
}


function updateMap() {
        var missionType = document.getElementById('missiontypemenu').value;
        if (missionType === "survey_area") {
            document.getElementById('set-points-survey').style.display = 'none';
            document.getElementById('set-points-route-out').style.display = 'block';
            document.getElementById('set-points-land').style.display = 'block';
            document.getElementById('set-points-survey-area').style.display = 'block';
        }
        else if (missionType === "one_way") {
            document.getElementById('set-points-route-out').style.display = 'none';
            document.getElementById('set-points-land').style.display = 'none';
            document.getElementById('set-points-survey').style.display = 'block';
            document.getElementById('set-points-survey-area').style.display = 'none';
        }
        else {
            document.getElementById('set-points-route-out').style.display = 'block';
            document.getElementById('set-points-land').style.display = 'block';
            document.getElementById('set-points-survey').style.display = 'block';
            document.getElementById('set-points-survey-area').style.display = 'none';
        }

        if (change) {
            fetch('/api/planner/map_data').then(response => response.json()).then(data => {
            if (data) {
                console.log('Map updated');

                map.eachLayer(function(layer) {
                    if (!(layer instanceof L.TileLayer)) {
                        map.removeLayer(layer);
                    }
                });
                
                map.addLayer(drawnItems);
                
                
                // pre-set points
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
                        /*
                        L.marker(point.pos, { icon: L.divIcon({
                            html: '<i class="fa-solid fa-file-lines" style="color: #ffffff;"></i>',
                            className: 'custom-div-icon'
                        }) }).addTo(map).bindPopup(popupContent);
                        */
                        
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

                if (data.home_pos) {
                    var homeMarker = L.marker(data.home_pos, { icon: L.divIcon({
                        html: '<i class="fa-solid fa-house" style="color: #0011ff;"></i>',
                        className: 'custom-div-icon'
                    }) }).addTo(map);
                    homeMarker.bindPopup("Home Position");
                }

                if (data.land_pos) {
                    var landMarker = L.marker(data.land_pos, { icon: L.divIcon({
                        html: '<i class="fa-solid fa-plane-arrival" style="color: #000000;"></i>',
                        className: 'custom-div-icon'
                    }) }).addTo(map);
                    landMarker.bindPopup("Landing Position");
                }

                if (data.route_in && data.route_in.length > 0) {
                    
                    var routeInCoords = data.route_in.map(point => point);
                    L.polyline(routeInCoords, {color: 'green'}).addTo(map);
                    data.route_in.forEach(point => {
                        L.marker(point, { icon: L.divIcon({
                            html: '<i class="fa-solid fa-arrow-right-to-bracket" style="color: #00ff2a;"></i>',
                            className: 'custom-div-icon'
                        }) }).addTo(map).bindPopup(`Route In Point ${point.num}`);
                    });
                            
                    if (data.home_pos) {
                        var homeCoords = data.home_pos;
                        var firstRouteInCoords = data.route_in[0];
                        L.polyline([homeCoords, firstRouteInCoords], { color: 'green'}).addTo(map);
                    }
                }
                
                if (missionType === "survey_area") {}
                else {
                    if (data.survey && data.survey.length > 0) {
                        if (data.route_in.length > 0) {
                            var lastRouteInCoords = data.route_in[data.route_in.length-1];
                        }
                        data.survey.forEach(point => {
                            L.marker(point, { icon: L.divIcon({
                                html: '<i class="fa-solid fa-bullseye" style="color: #ff0000;"></i>',
                                className: 'custom-div-icon'
                            }) }).addTo(map).bindPopup(`Survey Point ${point.num}`);
                            if (data.route_in.length > 0) {
                                L.polyline([lastRouteInCoords, point], { color: 'red'}).addTo(map);
                            }
                        });
                    }
                }

                if (data.route_out && data.route_out.length > 0) {
                    if (data.survey.length > 0) {
                        var firstRouteOutCoords = data.route_out[0];
                        data.survey.forEach(point => {
                            L.polyline([point, firstRouteOutCoords], { color: 'red'}).addTo(map);
                        });
                    }

                    var routeOutCoords = data.route_out.map(point => point);
                    L.polyline(routeOutCoords, {color: 'blue'}).addTo(map);
                    data.route_out.forEach(point => {
                        L.marker(point, { icon: L.divIcon({
                            html: '<i class="fa-solid fa-arrow-right-from-bracket" style="color: #00ff00;"></i>',
                            className: 'custom-div-icon'
                        }) }).addTo(map).bindPopup(`Route Out Point ${point.num}`);
                    });

                    if (data.land_pos) {
                        var lastRouteOutCoords = data.route_out[data.route_out.length-1];
                        L.polyline([data.land_pos, lastRouteOutCoords], { color: 'blue'}).addTo(map);
                    }


                }
                
            }
        });
        change = false;
    }
}

function undoLast() {
    fetch('/api/planner/undo_last', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            type: currentMode,
        }),
    }).then(response => response.json()).then(data => {
        if (data.success) {
            if (currentMode === 'route_in' && pointCounter> -1 && routeInPolyline.getLatLngs().length > 0) {
                pointCounter--;
                const latlngs = routeInPolyline.getLatLngs();
                latlngs.pop();
                routeInPolyline.setLatLngs(latlngs);
            } else if (currentMode === 'survey' && pointCounter>-1 && surveyMarkers.length > 0) {
                tgtCounter++;
                const lastMarker = surveyMarkers.pop();
                map.removeLayer(lastMarker);
                const lastLine = surveyLines.pop();
                if (lastLine) {
                    map.removeLayer(lastLine);
                }
            } else if (currentMode === 'route_out' && pointCounter> -1 && routeOutPolyline.getLatLngs().length > 0) {
                pointCounter--;
                const latlngs = routeOutPolyline.getLatLngs();
                latlngs.pop();
                routeOutPolyline.setLatLngs(latlngs);
            }
        }
    });
    change = true;
}


function clearAll() {
    fetch('/api/planner/clear_all', { method: 'POST' });
    if (homeMarker) {
        map.removeLayer(homeMarker);
        homeMarker = null;
    }
    drawnItems.clearLayers();
    routeInPolyline.setLatLngs([]);
    routeOutPolyline.setLatLngs([]);
    surveyMarkers.forEach(marker => map.removeLayer(marker));
    surveyMarkers = [];
    pointMarkers.forEach(marker => map.removeLayer(marker));
    pointMarkers = [];
    surveyLines.forEach(line => map.removeLayer(line));
    surveyLines = [];
    pointCounter = 1;
    tgtCounter = 0;
    change = true;
}

function save() {
    // Get the value from the text input
    const textValue = document.getElementById('textInput').value;
    var missionType = document.getElementById('missiontypemenu').value;
    
    const drawnLayers = drawnItems.getLayers();
    const polygons = [];
    const rectangles = [];
    const circles = [];

    drawnLayers.forEach(layer => {
        if (layer instanceof L.Polygon && !(layer instanceof L.Rectangle)) {
            const latlngs = layer.getLatLngs();
            const coords = latlngs.map(ring => ring.map(latlng => [latlng.lat, latlng.lng]));
            polygons.push(coords);
        } else if (layer instanceof L.Rectangle) {
            const latlngs = layer.getLatLngs();
            const coords = latlngs[0].map(latlng => [latlng.lat, latlng.lng]);
            rectangles.push(coords);
        } else if (layer instanceof L.Circle) {
            const center = layer.getLatLng();
            const radius = layer.getRadius();
            circles.push({
                center: [center.lat, center.lng],
                radius: radius
            });
        }
    });

    // Prepare the data to send
    const data = {
        missiontype: missionType,
        text: textValue,
        polygons: polygons,
        rectangles: rectangles,
        circles: circles
    };

    // Send the data via POST
    fetch('/api/planner/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'  // If using CSRF protection
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
           // alert('Data saved successfully!');
           alert('Error saving data.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function generate() {
    fetch("{{ url_for('gen_plan') }}", {
        method: "POST"
    }).then(response => {
        if (response.redirected) {
            window.location.href = response.url; 
        }
    }).catch(error => console.error('Error:', error));
}

map.on('click', function(e) {
    if (currentMode != "survey-area") {
        let lat = e.latlng.lat;
        let lon = e.latlng.lng;
        console.log('Map clicked at:', lat, lon);

        fetch('/api/planner/add_point', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat: lat, lon: lon })
        }
        ).then(response => {
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

map.on('draw:created', function (e) {
    var type = e.layerType,
        layer = e.layer;
    
    var shape = {};
    if (type === 'polygon' || type === 'rectangle') {
        // For polygons and rectangles
        var coordinates = layer.getLatLngs();
        shape = coordinates;
    } else if (type === 'circle') {
        // For circles
        var center = layer.getLatLng();
        var radius = layer.getRadius();
        shape = [center,radius];
    }

    // Add the layer to the feature group
    drawnItems.addLayer(layer);
    fetch('/api/planner/add_shape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                type: type, 
                shape: shape
            })
        }
        ).then(response => {
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
});

map.on('draw:edited', function (e) {
    var layers = e.layers;
    layers.eachLayer(function (layer) {
        // Do something with the edited layer
        var coordinates = layer.getLatLngs();
        console.log('Edited polygon coordinates:', coordinates);

        // Update your data accordingly
    });
});

map.on('draw:deleted', function (e) {
    var layers = e.layers;
    layers.eachLayer(function (layer) {
        // Handle the deletion of the layer
        console.log('Polygon deleted:', layer);

        // Update your data accordingly
    });
});

setInterval(updateMap, 1000);
