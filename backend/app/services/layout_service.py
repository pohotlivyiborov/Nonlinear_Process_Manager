import numpy as np
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
import time
import math
import logging

from .simulation_params_service import SimulationParamsService
from .substance_service import SubstanceService
from ..core.emissions_calculation_math.coloring import colorize_tile_numpy
from backend.app.core.emissions_calculation_math.ml_data.ml_inference import ml_inference
from ..core.emissions_calculation_math.state import pollution_state

logger = logging.getLogger("uvicorn")


class LayoutService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.params_service = SimulationParamsService(db)
        self.substance_service = SubstanceService(db)

    def tile_to_latlon(self, tx, ty, zoom):
        """Конвертация координат тайла в Широту и Долготу"""
        n = 2.0 ** zoom
        lon_deg = tx / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ty / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    async def render_tile(self, substance_id: int, tx: int, ty: int, tz: int):
        if tz < 5:  # Не рендерим на слишком высоком зуме (для экономии ресурсов)
            return Image.new("RGBA", (256, 256), (0, 0, 0, 0))

        res = 256

        # Получаем параметры симуляции (с кэшированием)
        current_time = time.time()
        if pollution_state.cached_params is not None and (current_time - pollution_state.params_time < 2):
            params = pollution_state.cached_params
        else:
            params_list = await self.params_service.get_simulation_params()
            params = params_list[-1] if params_list else None
            pollution_state.cached_params = params
            pollution_state.params_time = current_time

        # Дефолтные значения, пока БД пуста
        wind_speed = float(params.wind_speed) if params else 3.0
        wind_dir = float(params.wind_direction) if params else 180.0
        temp = float(params.temperature) if params else 20.0
        humidity = float(params.humidity) if params else 0.6

        # Получаем ПДК вещества для раскраски
        substance = await self.substance_service.get_substance_by_id(substance_id)
        mcl = substance.mcl if substance else 0.008

        # --- ГЕНЕРАЦИЯ СЕТКИ КООРДИНАТ ---
        # Находим координаты углов тайла в Lat/Lon
        lat_top, lon_left = self.tile_to_latlon(tx, ty, tz)
        lat_bottom, lon_right = self.tile_to_latlon(tx, ty + 1, tz)

        # Внимание: для следующего тайла по X (вправо)
        _, lon_right = self.tile_to_latlon(tx + 1, ty, tz)

        # Создаем линейные массивы координат пикселей
        # lon идет слева направо
        lons = np.linspace(lon_left, lon_right, res, dtype=np.float32)
        # lat идет сверху вниз (поэтому от top до bottom)
        lats = np.linspace(lat_top, lat_bottom, res, dtype=np.float32)

        # Создаем 2D сетку
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        # --- ML ИНФЕРЕНС ---
        # Вызываем предсказание нейросети
        grid_conc = ml_inference.predict_grid(
            lat_grid=lat_grid,
            lon_grid=lon_grid,
            temp=temp,
            humidity=humidity,
            wind_speed=wind_speed,
            wind_dir=wind_dir
        )

        # --- РАСКРАСКА ---
        img_data = colorize_tile_numpy(grid_conc, pdk=mcl, alpha_bg=110)

        return Image.fromarray(img_data, 'RGBA')