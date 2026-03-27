window.appConfig = {
    YMAPS_API_KEY: '{{ config.YMAPS_API_KEY }}',
    YMAPS_LANG: '{{ config.YMAPS_LANG }}',
    YWEATHER_API_KEY: '{{ config.YWEATHER_API_KEY }}',
};

let monitoringMap = null;

const monitoringState = {
    sources: [],
    sourceToDelete: null,
    isHeatmapVisible: true,
    currentSubstanceId: null // Текущее выбранное вещество
};

document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('map');
    if (mapContainer && mapContainer.dataset.mapRole === 'monitoring') {
        initMonitoringMap();
    }
});

function initMonitoringMap() {
    if (typeof ymaps === 'undefined') return;

    ymaps.ready(async () => {
        monitoringMap = new ymaps.Map('map', {
            center: [55.7558, 37.6173],
            zoom: 13,
            controls: ['zoomControl', 'typeSelector', 'fullscreenControl']
        });

        // Сначала грузим вещества
        await loadSubstances();

        MapGraphics.initPollutionLayer(monitoringMap, monitoringState.currentSubstanceId);
        initMonitoring();
    });
}

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

// ЗАГРУЗКА ВЕЩЕСТВ ИЗ БД
async function loadSubstances() {
    const substances = await apiCall('/api/substances'); // Убедитесь, что этот эндпоинт есть в FastAPI
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
            monitoringState.currentSubstanceId = substances[0].id;
        }

        select.addEventListener('change', (e) => {
            monitoringState.currentSubstanceId = parseInt(e.target.value);
            loadSourcesFromDB(); // Перезагружаем маркеры
            MapGraphics.refreshPollutionLayer(monitoringMap, monitoringState.currentSubstanceId); // Перерисовываем карту
        });
    }
}

async function loadSourcesFromDB() {
    // Получаем ВСЕ источники (или можно сделать фильтрацию на бэке: /api/sources?substance_id=...)
    const allSources = await apiCall('/api/sources');

    if (allSources) {
        // Оставляем только те источники, которые относятся к текущему выбранному веществу
        monitoringState.sources = allSources
            .filter(source => source.substance_id === monitoringState.currentSubstanceId)
            .map(source => ({
                ...source,
                id: source.id,
                lat: source.latitude,
                lng: source.longitude,
                type: source.type,
                coordinates: source.coordinates,
                emissionRate: source.emission_rate
            }));

        MapGraphics.drawSources(monitoringMap, monitoringState.sources);
        updateSourcesList();
    }
}

async function addSourceToDB(sourceData) {
    return await apiCall('/api/sources', { method: 'POST', body: JSON.stringify(sourceData) });
}

async function deleteSourceFromDB(sourceId) {
    return await apiCall(`/api/sources/${sourceId}`, { method: 'DELETE' });
}

function initMonitoring() {
    setupMonitoringEventListeners();
    loadSourcesFromDB();
}

function setupMonitoringEventListeners() {
    const addSourceBtn = document.getElementById('add-source-btn');
    if (addSourceBtn) {
        addSourceBtn.addEventListener('click', () => {
            if (!monitoringState.currentSubstanceId) {
                alert("Сначала выберите или создайте вещество!");
                return;
            }

            const typeSelect = document.getElementById('source-type');
            const sourceType = typeSelect ? typeSelect.value : 'point';

            if (MapGraphics.drawMode) {
                MapGraphics.disableDrawing(monitoringMap);
                addSourceBtn.textContent = 'Добавить источник на карту';
            } else {
                addSourceBtn.textContent = sourceType === 'point' ? 'Кликните на карту' : 'Рисуйте (Двойной клик - завершить)';

                MapGraphics.enableDrawing(monitoringMap, sourceType, async (type, centerCoords, fullCoords) => {
                    const heightInput = document.getElementById('source-height');
                    const rateInput = document.getElementById('emission-rate');

                    await addSourceToDB({
                        name: `Источник ${Date.now() % 1000}`,
                        type: type,
                        latitude: centerCoords[0],
                        longitude: centerCoords[1],
                        coordinates: fullCoords,
                        height: heightInput ? parseFloat(heightInput.value) : 40,
                        emission_rate: rateInput ? parseFloat(rateInput.value.replace(',', '.')) : 3.7,
                        substance_id: monitoringState.currentSubstanceId // ПРИВЯЗЫВАЕМ К ВЕЩЕСТВУ
                    });

                    addSourceBtn.textContent = 'Добавить источник на карту';
                    loadSourcesFromDB();
                    MapGraphics.refreshPollutionLayer(monitoringMap, monitoringState.currentSubstanceId);
                });
            }
        });
    }

    const toggleHeatmapBtn = document.getElementById('toggle-heatmap-btn');
    if (toggleHeatmapBtn) {
        toggleHeatmapBtn.addEventListener('click', () => {
            monitoringState.isHeatmapVisible = !monitoringState.isHeatmapVisible;
            if (monitoringState.isHeatmapVisible) {
                monitoringMap.layers.add(MapGraphics.pollutionLayer);
                MapGraphics.refreshPollutionLayer(monitoringMap, monitoringState.currentSubstanceId);
            } else {
                monitoringMap.layers.remove(MapGraphics.pollutionLayer);
            }
        });
    }

    document.querySelectorAll('.close').forEach(el => el.addEventListener('click', () => document.getElementById('confirm-modal').style.display = 'none'));
    const cancelDeleteBtn = document.getElementById('cancel-delete');
    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener('click', () => document.getElementById('confirm-modal').style.display = 'none');
    const confirmDeleteBtn = document.getElementById('confirm-delete');
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', confirmDeleteSource);
}

function updateSourcesList() {
    const sourcesList = document.getElementById('sources-list');
    if (!sourcesList) return;

    sourcesList.innerHTML = monitoringState.sources.length === 0 ? '<p style="text-align: center;">Нет источников для этого вещества</p>' : '';

    monitoringState.sources.forEach(source => {
        const sourceEl = document.createElement('div');
        sourceEl.className = 'source-item';
        sourceEl.innerHTML = `
      <strong>${source.name} (${source.type})</strong><br>
      <small>Высота: ${source.height} м, выброс: ${source.emissionRate.toFixed(3)} г/с</small>
      <div class="source-actions">
        <button onclick="flyToSource(${source.id})">На карте</button>
        <button onclick="requestDeleteSource(${source.id})" class="danger">Удалить</button>
      </div>`;
        sourcesList.appendChild(sourceEl);
    });
}

function requestDeleteSource(sourceId) {
    monitoringState.sourceToDelete = monitoringState.sources.find(s => s.id === sourceId);
    if (monitoringState.sourceToDelete) {
        const modal = document.getElementById('confirm-modal');
        if (modal) modal.style.display = 'block';
    }
}

async function confirmDeleteSource() {
    if (!monitoringState.sourceToDelete) return;
    const result = await deleteSourceFromDB(monitoringState.sourceToDelete.id);
    if (result && result.success !== false) {
        await loadSourcesFromDB();
        MapGraphics.refreshPollutionLayer(monitoringMap, monitoringState.currentSubstanceId);
    }
    const modal = document.getElementById('confirm-modal');
    if (modal) modal.style.display = 'none';
    monitoringState.sourceToDelete = null;
}

function flyToSource(sourceId) {
    if (!monitoringMap) return;
    const source = monitoringState.sources.find(s => s.id === sourceId);
    if (source) {
        monitoringMap.panTo([source.lat, source.lng], { duration: 1000, flying: true }).then(() => {
            monitoringMap.setZoom(15, { duration: 500 });
            if (source.placemark) source.placemark.balloon.open();
        });
    }
}

window.requestDeleteSource = requestDeleteSource;
window.flyToSource = flyToSource;

// ==========================================
// АНИМАЦИЯ ПОГОДЫ
// ==========================================
let weatherData = { wind_speed: 3, wind_dir: 'n', prec_type: 0, prec_strength: 0 };
let isWindOn = true;
let isRainOn = true;

function dirToText(dir) {
    const map = { n:'С', ne:'СВ', e:'В', se:'ЮВ', s:'Ю', sw:'ЮЗ', w:'З', nw:'СЗ' };
    return map[dir] || 'С';
}

async function refreshWeather() {
    try {
        const res = await fetch('https://api.weather.yandex.ru/v2/forecast?lat=55.7558&lon=37.6173&limit=1', {
            headers: { 'X-Yandex-API-Key': window.appConfig.YWEATHER_API_KEY }
        });
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        const f = data.fact;

        weatherData = {
            wind_speed: f.wind_speed, wind_dir: f.wind_dir, pressure_mm: f.pressure_mm,
            humidity: f.humidity, visibility: f.visibility ? (f.visibility/1000).toFixed(1) : 10,
            prec_type: f.prec_type || 0, prec_strength: f.prec_strength || 0
        };

        const panel = document.querySelector('.map-meta');
        if (panel) panel.textContent = `Ветер: ${f.wind_speed} м/с, ${dirToText(f.wind_dir)}    Давление: ${f.pressure_mm} мм рт. ст.    Влажность: ${f.humidity}%    Дальность видимости: ${weatherData.visibility} км`;
    } catch (e) {
        weatherData = { wind_speed: 3, wind_dir: 'n', pressure_mm: 764, humidity: 61, visibility: '10', prec_type: 0, prec_strength: 0 };
    }
}

let canvas, ctx, particles = [], animationId;
function startWeatherAnimation() {
    if (!monitoringMap?.container) return;
    canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:absolute; top:0; left:0; pointer-events:none; z-index:1000;';
    const container = monitoringMap.container.getElement();
    container.style.position = 'relative';
    container.appendChild(canvas);

    function resize() { canvas.width = container.clientWidth; canvas.height = container.clientHeight; }
    resize(); window.addEventListener('resize', resize);
    monitoringMap.events.add('boundschange', resize);

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const ws = weatherData.wind_speed * 1.2;
        const angle = { n:0, ne:45, e:90, se:135, s:180, sw:225, w:270, nw:315 }[weatherData.wind_dir] || 0;
        const rad = angle * Math.PI / 180;

        if (isWindOn) {
            if (particles.length < 70) particles.push({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, life: 1 });
            particles.forEach((p, i) => {
                p.x += Math.cos(rad) * ws; p.y += Math.sin(rad) * ws; p.life -= 0.01;
                if (p.life > 0) {
                    ctx.strokeStyle = `rgba(52, 152, 219, ${p.life})`; ctx.lineWidth = 3;
                    ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x - Math.cos(rad)*30, p.y - Math.sin(rad)*30); ctx.stroke();
                } else particles.splice(i, 1);
            });
        }
        if (isRainOn && weatherData.prec_strength > 0) {
            for (let i = 0; i < 5 * weatherData.prec_strength; i++) particles.push({ x: Math.random() * canvas.width, y: -10, life: 1, isRain: true });
            particles.forEach((p, i) => {
                if (!p.isRain) return;
                p.y += 10; p.life -= 0.02;
                if (p.life > 0 && p.y < canvas.height) {
                    ctx.strokeStyle = weatherData.prec_type === 2 ? 'rgba(255,255,255,0.8)' : 'rgba(100,180,255,0.7)';
                    ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x, p.y + 12); ctx.stroke();
                } else if (p.y >= canvas.height) particles.splice(i, 1);
            });
        }
        animationId = requestAnimationFrame(animate);
    }
    ctx = canvas.getContext('2d'); animate();
}

setTimeout(() => {
    refreshWeather();
    setInterval(refreshWeather, 600000);
    if (monitoringMap) startWeatherAnimation();

    const toggleWindBtn = document.getElementById('toggleWind');
    if (toggleWindBtn) toggleWindBtn.addEventListener('click', () => { isWindOn = !isWindOn; toggleWindBtn.textContent = `Ветер: ${isWindOn ? 'Вкл' : 'Выкл'}`; });

    const togglePrecipBtn = document.getElementById('togglePrecip');
    if (togglePrecipBtn) togglePrecipBtn.addEventListener('click', () => { isRainOn = !isRainOn; togglePrecipBtn.textContent = `Осадки: ${isRainOn ? 'Вкл' : 'Выкл'}`; });
}, 1500);