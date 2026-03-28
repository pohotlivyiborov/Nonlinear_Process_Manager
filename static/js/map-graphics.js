window.MapGraphics = {
    pollutionLayer: null,
    windVectors: [],
    sourceGeoObjects: [],
    drawMode: null,
    currentGeometry: [],
    tempGeoObject: null,
    currentSubstanceId: 1, // ID вещества по умолчанию

    initPollutionLayer(map, substanceId = 1) {
        this.currentSubstanceId = substanceId;
        const tileUrlTemplate = `/api/simulation/tiles/${this.currentSubstanceId}/%z/%x/%y.png?t=` + Date.now();
        this.pollutionLayer = new ymaps.Layer(tileUrlTemplate, {
            tileTransparent: true,
            zIndex: 5000,
            minZoom: 9,
            maxZoom: 19
        });
        map.layers.add(this.pollutionLayer);
    },

    refreshPollutionLayer(map, newSubstanceId = null) {
        if (!this.pollutionLayer) return;
        if (newSubstanceId) this.currentSubstanceId = newSubstanceId;

        map.layers.remove(this.pollutionLayer);

        const tileUrlTemplate = `/api/simulation/tiles/${this.currentSubstanceId}/%z/%x/%y.png?t=` + Date.now();
        this.pollutionLayer = new ymaps.Layer(tileUrlTemplate, {
            tileTransparent: true,
            zIndex: 5000,
            minZoom: 9,
            maxZoom: 19
        });

        map.layers.add(this.pollutionLayer);
    },

    drawWindVectors(map, sources, windDirection) {
        this.windVectors.forEach(pm => map.geoObjects.remove(pm));
        this.windVectors = [];

        sources.forEach(source => {
            if (source.type !== 'point' && !source.latitude) return;

            const plumeDir = (windDirection + 180) % 360;
            const dirRad = (plumeDir * Math.PI) / 180;
            const length = 1500;

            const dLat = (length * Math.cos(dirRad)) / 111000;
            const dLng = (length * Math.sin(dirRad)) / (111000 * Math.cos(source.lat * Math.PI / 180));

            const polyline = new ymaps.Polyline([
                [source.lat, source.lng],
                [source.lat + dLat, source.lng + dLng]
            ], {}, { strokeColor: '#3498db', strokeWidth: 3, strokeOpacity: 0.8 });

            map.geoObjects.add(polyline);
            this.windVectors.push(polyline);
        });
    },

    drawSources(map, sources) {
        this.sourceGeoObjects.forEach(obj => map.geoObjects.remove(obj));
        this.sourceGeoObjects = [];

        sources.forEach(source => {
            let geoObj;
            const balloonContent = `<b>${source.name}</b><br>Тип: ${source.type}<br>Выброс: ${source.emissionRate} г/с`;

            if (source.type === 'point' || !source.coordinates) {
                geoObj = new ymaps.Placemark([source.lat, source.lng], { balloonContent }, { preset: 'islands#redIcon' });
            } else if (source.type === 'line') {
                geoObj = new ymaps.Polyline(source.coordinates, { balloonContent }, {
                    strokeColor: '#2c3e50',
                    strokeWidth: 4,
                    strokeOpacity: 0.3
                });
            } else if (source.type === 'polygon') {
                geoObj = new ymaps.Polygon([source.coordinates], { balloonContent }, {
                    fillColor: '#2c3e50',
                    fillOpacity: 0.3,
                    strokeColor: '#2c3e50',
                    strokeWidth: 3,
                    strokeOpacity: 0.3
                });
            }

            if (geoObj) {
                map.geoObjects.add(geoObj);
                this.sourceGeoObjects.push(geoObj);
                source.placemark = geoObj;
            }
        });
    },

    enableDrawing(map, type, onFinishCallback) {
        this.drawMode = type;
        this.currentGeometry = [];
        map.cursors.push('crosshair');

        if (this._clickHandler) map.events.remove('click', this._clickHandler);

        this._clickHandler = (e) => {
            const coords = e.get('coords');
            this.currentGeometry.push(coords);

            if (this.tempGeoObject) map.geoObjects.remove(this.tempGeoObject);

            if (type === 'point') {
                onFinishCallback('point', coords, null);
                this.disableDrawing(map);
            }
            else if (type === 'line') {
                this.tempGeoObject = new ymaps.Polyline(this.currentGeometry, {}, { strokeColor: '#3498db', strokeWidth: 4, strokeOpacity: 0.8 });
                map.geoObjects.add(this.tempGeoObject);
            }
            else if (type === 'polygon') {
                this.tempGeoObject = new ymaps.Polygon([this.currentGeometry], {}, { fillColor: '#3498db', fillOpacity: 0.4, strokeColor: '#2980b9', strokeWidth: 3 });
                map.geoObjects.add(this.tempGeoObject);
            }
        };

        this._dblClickHandler = (e) => {
            e.preventDefault();
            if (type === 'line' || type === 'polygon') {
                onFinishCallback(type, this.currentGeometry[0], this.currentGeometry);
                this.disableDrawing(map);
            }
        };

        map.events.add('click', this._clickHandler);
        if (type !== 'point') map.events.add('dblclick', this._dblClickHandler);
    },

    disableDrawing(map) {
        this.drawMode = null;
        map.cursors.push('arrow');
        if (this._clickHandler) map.events.remove('click', this._clickHandler);
        if (this._dblClickHandler) map.events.remove('dblclick', this._dblClickHandler);
        if (this.tempGeoObject) map.geoObjects.remove(this.tempGeoObject);
        this.tempGeoObject = null;
    }
};