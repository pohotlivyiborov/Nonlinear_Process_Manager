import numpy as np
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
import time
import logging

from .source_service import SourceService
from .simulation_params_service import SimulationParamsService
from .substance_service import SubstanceService
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
        self.substance_service = SubstanceService(db)

    def get_tile_bounds(self, tx, ty, zoom):
        equator = 40075016.685578488
        tile_size = equator / (2 ** zoom)
        origin = equator / 2.0
        min_x = tx * tile_size - origin
        max_x = (tx + 1) * tile_size - origin
        max_y = origin - ty * tile_size
        min_y = origin - (ty + 1) * tile_size
        return min_x, min_y, max_x, max_y

    async def _get_prepared_sources(self, substance_id: int):
        current_time = time.time()

        # Инициализация словарей в кэше, если их еще нет (для безопасности)
        if not isinstance(pollution_state.cached_sources, dict):
            pollution_state.cached_sources = {}
            pollution_state.sources_time = {}

        # Проверка свежести кэша для КОНКРЕТНОГО вещества
        if substance_id in pollution_state.cached_sources and \
                (current_time - pollution_state.sources_time.get(substance_id, 0) < 2):
            return pollution_state.cached_sources[substance_id]

        # Обращение к БД через Сервисы
        sources_db = await self.source_service.get_sources_by_substance(substance_id)
        substance = await self.substance_service.get_substance_by_id(substance_id)

        if not substance:
            logger.error(f"Substance {substance_id} not found!")
            mcl = 0.008  # Фолбэк ПДК
        else:
            mcl = substance.mcl

        # Дискретизация (внутри вытянет settling_velocity благодаря selectinload в репозитории)
        prepared_data = discretize_sources(sources_db)

        # Сохраняем в кэш кортеж: (массивы_данных, ПДК_вещества)
        pollution_state.cached_sources[substance_id] = (prepared_data, mcl)
        pollution_state.sources_time[substance_id] = current_time

        return pollution_state.cached_sources[substance_id]

    async def render_tile(self, substance_id: int, tx: int, ty: int, tz: int):
        if tz < 11:
            return Image.new("RGBA", (256, 256), (0, 0, 0, 0))

        min_x, min_y, max_x, max_y = self.get_tile_bounds(tx, ty, tz)
        res = 256
        px_size = (max_x - min_x) / res

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

        # Получаем данные И ПДК конкретного вещества
        prepared_data, mcl = await self._get_prepared_sources(substance_id)

        # Распаковываем 7 массивов (включая settling_velocity)
        src_xs, src_ys, src_rates, src_heights, src_sy0, src_sz0, src_settling = prepared_data

        BUFFER = 200000
        mask = (src_xs > min_x - BUFFER) & (src_xs < max_x + BUFFER) & \
               (src_ys > min_y - BUFFER) & (src_ys < max_y + BUFFER)

        if not np.any(mask):
            return Image.new("RGBA", (256, 256), (46, 204, 113, 110))

        s_xs, s_ys = src_xs[mask], src_ys[mask]
        s_rates, s_heights = src_rates[mask], src_heights[mask]
        s_sy0, s_sz0 = src_sy0[mask], src_sz0[mask]
        s_settling = src_settling[mask]  # Маска для скоростей оседания

        px_half = px_size / 2.0
        xs = np.linspace(min_x + px_half, max_x - px_half, res, dtype=np.float32)
        ys = np.linspace(max_y - px_half, min_y + px_half, res, dtype=np.float32)
        xv, yv = np.meshgrid(xs, ys)

        # Передаем s_settling в Numba!
        conc_flat = calculate_concentration_chunk(
            xv.ravel(), yv.ravel(),
            s_xs, s_ys, s_rates, s_heights,
            s_sy0, s_sz0, s_settling,
            u, wind_math_rad
        )

        grid_conc = conc_flat.reshape((res, res))

        # Передаем реальный MCL (ПДК) в раскраску
        img_data = colorize_tile_numpy(grid_conc, pdk=mcl, alpha_bg=110)

        return Image.fromarray(img_data, 'RGBA')
