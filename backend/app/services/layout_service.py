import numpy as np
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
import time
import logging

from .source_service import SourceService
from .simulation_params_service import SimulationParamsService
from backend.app.core.emissions_calculation_math.math_numba import calculate_concentration_chunk
from ..core.emissions_calculation_math.state import pollution_state
from ..core.emissions_calculation_math.discretization import discretize_sources
from ..core.emissions_calculation_math.coloring import colorize_tile_numpy

logger = logging.getLogger("uvicorn")


class LayoutService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.source_service = SourceService(db)
        self.params_service = SimulationParamsService(db)

    def get_tile_bounds(self, tx, ty, zoom):
        equator = 40075016.685578488
        tile_size = equator / (2 ** zoom)
        origin = equator / 2.0
        min_x = tx * tile_size - origin
        max_x = (tx + 1) * tile_size - origin
        max_y = origin - ty * tile_size
        min_y = origin - (ty + 1) * tile_size
        return min_x, min_y, max_x, max_y

    async def _get_prepared_sources(self):
        current_time = time.time()

        # Если данные есть в кэше и они свежие — отдаем их
        if pollution_state.cached_sources is not None and (current_time - pollution_state.sources_time < 2):
            return pollution_state.cached_sources

        # Иначе — берем из БД и дискретизируем
        sources_db = await self.source_service.get_all_sources()
        prepared_data = discretize_sources(sources_db)

        # Обновляем кэш
        pollution_state.cached_sources = prepared_data
        pollution_state.sources_time = current_time
        return pollution_state.cached_sources

    async def render_tile(self, tx, ty, tz):
        if tz < 9:  # Отключаем рендер при сильном отдалении
            return Image.new("RGBA", (256, 256), (0, 0, 0, 0))

        min_x, min_y, max_x, max_y = self.get_tile_bounds(tx, ty, tz)
        res = 256
        px_size = (max_x - min_x) / res

        # Получаем параметры симуляции (ветер)
        current_time = time.time()
        if pollution_state.cached_params is not None and (current_time - pollution_state.params_time < 2):
            params = pollution_state.cached_params
        else:
            params_list = await self.params_service.get_simulation_params()
            params = params_list[-1] if params_list else None
            pollution_state.cached_params = params
            pollution_state.params_time = current_time

        u = float(params.wind_speed) if params else 3.0
        wind_dir = float(params.wind_direction) if params else 180.0
        wind_math_rad = np.radians((270 - wind_dir) % 360)

        # Получаем подготовленные массивы источников
        src_xs, src_ys, src_rates, src_heights, src_sy0, src_sz0 = await self._get_prepared_sources()

        BUFFER = 200000
        mask = (src_xs > min_x - BUFFER) & (src_xs < max_x + BUFFER) & \
               (src_ys > min_y - BUFFER) & (src_ys < max_y + BUFFER)

        PDK = 0.008

        if not np.any(mask):
            return Image.new("RGBA", (256, 256), (46, 204, 113, 110))

        s_xs, s_ys = src_xs[mask], src_ys[mask]
        s_rates, s_heights = src_rates[mask], src_heights[mask]
        s_sy0, s_sz0 = src_sy0[mask], src_sz0[mask]  # Фильтруем новые массивы

        px_half = px_size / 2.0
        xs = np.linspace(min_x + px_half, max_x - px_half, res, dtype=np.float32)
        ys = np.linspace(max_y - px_half, min_y + px_half, res, dtype=np.float32)
        xv, yv = np.meshgrid(xs, ys)

        # Расчет в Numba
        conc_flat = calculate_concentration_chunk(
            xv.ravel(), yv.ravel(),
            s_xs, s_ys, s_rates, s_heights,
            s_sy0, s_sz0,  # Передаем новые параметры
            u, wind_math_rad
        )

        # Окрашивание
        grid_conc = conc_flat.reshape((res, res))
        img_data = colorize_tile_numpy(grid_conc, pdk=PDK, alpha_bg=110)

        return Image.fromarray(img_data, 'RGBA')