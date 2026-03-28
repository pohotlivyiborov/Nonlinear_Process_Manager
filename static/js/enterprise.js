window.appConfig = {
    YMAPS_API_KEY: '{{ config.YMAPS_API_KEY }}',
    YMAPS_LANG: '{{ config.YMAPS_LANG }}',
    YWEATHER_API_KEY: '{{ config.YWEATHER_API_KEY }}',
};

let map = null;
let paramsUpdateTimeout = null;

const state = {
    sources: [],
    sourceToDelete: null,
    heatmapVisible: true,
    windSpeed: 2.4,
    windDirection: 180,
    stabilityClass: 'D',
    showWindVectors: true,
    currentSubstanceId: null // Текущее выбранное вещество
};

window.requestDeleteSource = function(sourceId) {
    state.sourceToDelete = state.sources.find(s => s.id === sourceId);
    if (state.sourceToDelete) {
        document.getElementById('confirm-modal').style.display = 'block';
    }
};

window.toggleDebugInfo = function() {
    const debugInfo = document.getElementById('debug-info');
    if (debugInfo) debugInfo.style.display = debugInfo.style.display === 'block' ? 'none' : 'block';
};

window.resetWindSettings = function() {
    state.windSpeed = 2.4;
    state.windDirection = 180;

    const windSpeedEl = document.getElementById('wind-speed');
    const windDirectionEl = document.getElementById('wind-direction');
    if (windSpeedEl) windSpeedEl.value = state.windSpeed;
    if (windDirectionEl) windDirectionEl.value = state.windDirection;

    updateWindDisplay();
    if (state.showWindVectors) MapGraphics.drawWindVectors(map, state.sources, state.windDirection);
    saveSimulationParamsAndRefresh();
};

window.updateHeatmapData = function() {
    MapGraphics.refreshPollutionLayer(map, state.currentSubstanceId);
};

// --- Работа с API и БД ---

async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const text = await response.text();
        return text ? JSON.parse(text) : { success: true };
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

// Загрузка веществ
async function loadSubstances() {
    const substances = await apiCall('/api/substances');
    const select = document.getElementById('substance-select');

    if (substances && select) {
        select.innerHTML = '';
        substances.forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.id;
            option.textContent = `${sub.name} (${sub.short_name})`;
            select.appendChild(option);
        });

        if (substances.length > 0) {
            state.currentSubstanceId = substances[0].id;
        }

        select.addEventListener('change', (e) => {
            state.currentSubstanceId = parseInt(e.target.value);
            loadSourcesFromDB();
            MapGraphics.refreshPollutionLayer(map, state.currentSubstanceId);
        });
    }
}

async function loadSourcesFromDB() {
    const allSources = await apiCall('/api/sources');
    if (allSources) {
        state.sources = allSources
            .filter(source => source.substance_id === state.currentSubstanceId)
            .map(source => ({
                ...source,
                id: source.id,
                lat: source.latitude,
                lng: source.longitude,
                emissionRate: source.emission_rate,
                height: source.height,
                type: source.type
            }));

        updateSourcesList();

        MapGraphics.drawSources(map, state.sources);
        if (state.showWindVectors) MapGraphics.drawWindVectors(map, state.sources, state.windDirection);

        MapGraphics.refreshPollutionLayer(map, state.currentSubstanceId);
    }
}

async function addSourceToDB(sourceData) {
    return await apiCall('/api/sources', { method: 'POST', body: JSON.stringify(sourceData) });
}

async function deleteSourceFromDB(sourceId) {
    return await apiCall(`/api/sources/${sourceId}`, { method: 'DELETE' });
}

async function saveSimulationParamsAndRefresh() {
    updateDebugStatus("Обновление параметров и перерисовка...");
    const paramsData = {
        wind_speed: state.windSpeed,
        wind_direction: state.windDirection,
        stability_class: state.stabilityClass
    };

    try {
        const result = await apiCall('/api/simulation_params/', {
            method: 'POST',
            body: JSON.stringify(paramsData)
        });
        if (result) MapGraphics.refreshPollutionLayer(map, state.currentSubstanceId);
    } catch (e) {
        console.error("Ошибка сохранения параметров", e);
    }
}

// --- Логика карты ---

function initMap() {
    try {
        document.getElementById('loading-indicator').style.display = 'block';
        updateDebugStatus("Инициализация карты...");

        map = new ymaps.Map('map', {
            center: [55.7558, 37.6173],
            zoom: 13,
            controls: ['zoomControl', 'typeSelector', 'fullscreenControl']
        });

        updateDebugStatus("Карта загружена");
        setTimeout(() => document.getElementById('loading-indicator').style.display = 'none', 500);

        init(); // Грузим вещества, затем слой, затем источники
    } catch (error) {
        console.error("Ошибка при инициализации карты:", error);
        showErrorMessage("Ошибка загрузки карты: " + error.message);
    }
}

function updateDebugStatus(status) {
    const debugStatus = document.getElementById('debug-status');
    if (debugStatus) debugStatus.textContent = status;
}

function showErrorMessage(message) {
    const errorMessage = document.getElementById('error-message');
    if (errorMessage) {
        errorMessage.innerHTML = `<p>${message}</p><button onclick="location.reload()">Перезагрузить</button>`;
        errorMessage.style.display = 'block';
    }
}

function updateWindDisplay() {
    const windDirectionArrow = document.getElementById('wind-direction-arrow');
    const windSpeedValue = document.getElementById('wind-speed-value');
    const windDirectionValue = document.getElementById('wind-direction-value');

    if (windDirectionArrow) windDirectionArrow.style.transform = `translateX(-50%) rotate(${state.windDirection}deg)`;
    if (windSpeedValue) windSpeedValue.textContent = `${state.windSpeed.toFixed(1)} м/с`;

    if (windDirectionValue) {
        const dirs = ['С', 'СВ', 'В', 'ЮВ', 'Ю', 'ЮЗ', 'З', 'СЗ'];
        const idx = Math.round(state.windDirection / 45) % 8;
        windDirectionValue.textContent = `${state.windDirection}° (${dirs[idx]})`;
    }
}

function updateSourcesList() {
    const sourcesList = document.getElementById('sources-list');
    if (!sourcesList) return;

    sourcesList.innerHTML = '';
    state.sources.forEach(source => {
        const sourceEl = document.createElement('div');
        sourceEl.className = 'enterprise-source-item';
        sourceEl.innerHTML = `
            <div>${source.name} (${source.type})<br><small>${source.emissionRate} г/с</small></div>
            <button class="btn-delete" onclick="requestDeleteSource(${source.id})">Удалить</button>`;
        sourcesList.appendChild(sourceEl);
    });
}

async function init() {
    await loadSubstances();
    MapGraphics.initPollutionLayer(map, state.currentSubstanceId);
    setupEventListeners();
    loadSourcesFromDB();
}

function handleWindChange() {
    updateWindDisplay();
    if (state.showWindVectors) MapGraphics.drawWindVectors(map, state.sources, state.windDirection);

    if (paramsUpdateTimeout) clearTimeout(paramsUpdateTimeout);
    paramsUpdateTimeout = setTimeout(() => {
        saveSimulationParamsAndRefresh();
    }, 500);
}

function setupEventListeners() {
    const heatmapToggle = document.getElementById('heatmap-toggle');
    if (heatmapToggle) {
        heatmapToggle.addEventListener('change', function() {
            state.heatmapVisible = this.checked;
            if (map && MapGraphics.pollutionLayer) {
                if (state.heatmapVisible) map.layers.add(MapGraphics.pollutionLayer);
                else map.layers.remove(MapGraphics.pollutionLayer);
            }
        });
    }

    const windSpeedEl = document.getElementById('wind-speed');
    if (windSpeedEl) windSpeedEl.addEventListener('input', function() { state.windSpeed = parseFloat(this.value); handleWindChange(); });

    const windDirectionEl = document.getElementById('wind-direction');
    if (windDirectionEl) windDirectionEl.addEventListener('input', function() { state.windDirection = parseInt(this.value); handleWindChange(); });

    const showWindVectorsEl = document.getElementById('show-wind-vectors');
    if (showWindVectorsEl) {
        showWindVectorsEl.addEventListener('change', function() {
            state.showWindVectors = this.checked;
            if (this.checked) MapGraphics.drawWindVectors(map, state.sources, state.windDirection);
            else MapGraphics.windVectors.forEach(pm => map.geoObjects.remove(pm));
        });
    }

    const addSourceBtn = document.getElementById('add-source-btn');
    if (addSourceBtn) {
        addSourceBtn.addEventListener('click', () => {
            if (!state.currentSubstanceId) {
                alert("Сначала выберите или создайте вещество!");
                return;
            }

            const typeSelect = document.getElementById('source-type');
            const sourceType = typeSelect ? typeSelect.value : 'point';

            if (MapGraphics.drawMode) {
                MapGraphics.disableDrawing(map);
                addSourceBtn.textContent = 'Добавить источник';
            } else {
                addSourceBtn.textContent = sourceType === 'point' ? 'Кликните на карту' : 'Рисуйте (Двойной клик)';

                MapGraphics.enableDrawing(map, sourceType, async (type, centerCoords, fullCoords) => {
                    const heightInput = document.getElementById('source-height');
                    const rateInput = document.getElementById('emission-rate');
                    const h = heightInput ? parseFloat(heightInput.value) : 40;
                    const rate = rateInput ? parseFloat(rateInput.value.replace(',', '.')) : 3.7;

                    await addSourceToDB({
                        name: `Источник ${Date.now() % 1000}`,
                        type: type,
                        latitude: centerCoords[0],
                        longitude: centerCoords[1],
                        coordinates: fullCoords,
                        height: h,
                        emission_rate: rate,
                        substance_id: state.currentSubstanceId
                    });

                    addSourceBtn.textContent = 'Добавить источник';
                    loadSourcesFromDB();
                });
            }
        });
    }

    const updateHeatmapBtn = document.getElementById('update-heatmap-btn');
    if (updateHeatmapBtn) updateHeatmapBtn.addEventListener('click', () => MapGraphics.refreshPollutionLayer(map, state.currentSubstanceId));

    document.querySelectorAll('.close').forEach(el => el.addEventListener('click', () => document.getElementById('confirm-modal').style.display = 'none'));
    const cancelDelete = document.getElementById('cancel-delete');
    if (cancelDelete) cancelDelete.addEventListener('click', () => document.getElementById('confirm-modal').style.display = 'none');
    const confirmDelete = document.getElementById('confirm-delete');
    if (confirmDelete) confirmDelete.addEventListener('click', confirmDeleteSource);

    updateWindDisplay();
}

async function confirmDeleteSource() {
    if (!state.sourceToDelete) return;
    const result = await deleteSourceFromDB(state.sourceToDelete.id);
    if (result) {
        await loadSourcesFromDB();
        MapGraphics.refreshPollutionLayer(map, state.currentSubstanceId);
    }
    document.getElementById('confirm-modal').style.display = 'none';
    state.sourceToDelete = null;
}

ymaps.ready(initMap);