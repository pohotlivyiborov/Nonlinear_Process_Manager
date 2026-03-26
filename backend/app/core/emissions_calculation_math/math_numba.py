# app/core/emissions_calculation_math/math_numba.py
import numpy as np
from numba import njit, prange

E_WGS84 = 0.0818191908426215
R_EARTH = 6378137.0


@njit(fastmath=True)
def lat_lon_to_meters_yandex_single(lat, lon):
    if lat > 89.9: lat = 89.9
    if lat < -89.9: lat = -89.9
    phi = lat * (np.pi / 180.0)
    lam = lon * (np.pi / 180.0)
    x = R_EARTH * lam
    sin_phi = np.sin(phi)
    con = E_WGS84 * sin_phi
    com = (1.0 - con) / (1.0 + con)
    factor = np.power(com, 0.5 * E_WGS84)
    tan_val = np.tan(0.5 * (np.pi * 0.5 - phi))
    ts = tan_val / factor
    y = -R_EARTH * np.log(ts)
    return x, y


@njit(fastmath=True, parallel=True)
def calculate_concentration_chunk(
        x_grid_flat, y_grid_flat, src_xs, src_ys, src_rates, src_heights,
        src_sy0, src_sz0,
        u, base_wind_rad
):
    n_pixels = len(x_grid_flat)
    n_sources = len(src_xs)
    result = np.zeros(n_pixels, dtype=np.float32)

    for i in prange(n_pixels):
        px = x_grid_flat[i]
        py = y_grid_flat[i]
        val = 0.0

        for k in range(n_sources):
            dx = px - src_xs[k]
            dy = py - src_ys[k]

            dist = np.sqrt(dx * dx + dy * dy)
            if dist < 1.0: dist = 1.0

            swirl_angle = dist * 0.000015 * (15.0 / max(u, 1.0))
            current_angle = base_wind_rad + swirl_angle

            cos_a = np.cos(current_angle)
            sin_a = np.sin(current_angle)

            downwind = dx * cos_a + dy * sin_a
            crosswind = -dx * sin_a + dy * cos_a

            # Мягкое отсечение против ветра (оставляем только ближнюю зону для диффузии)
            if downwind < -300.0:
                continue

            wiggle = np.sin(dist / 1500.0) * (dist * 0.08)
            crosswind += wiggle

            Q = src_rates[k] * 1000.0  # Перевод в мг/с

            # --- 1. ФИЗИЧНОЕ РАДИАЛЬНОЕ ПЯТНО (PUFF) ---
            # Это диффузия газа против ветра и вокруг трубы. 
            # Зависит от Q, высоты трубы (src_heights) и скорости ветра (u).
            puff_radius = src_sy0[k] + 20.0
            puff_sigma_z = src_sz0[k] + 10.0

            puff_peak = Q / (6.283185 * max(u, 0.5) * puff_radius * puff_sigma_z)
            puff_exp_xy = np.exp(-0.5 * (dist / puff_radius) ** 2)
            puff_exp_z = np.exp(-0.5 * (src_heights[k] / puff_sigma_z) ** 2)

            puff_val = puff_peak * puff_exp_xy * puff_exp_z

            # --- 2. ОСНОВНОЙ ШЛЕЙФ ПО ВЕТРУ (PLUME) ---
            plume_val = 0.0
            if downwind > 0:
                sigma_y = src_sy0[k] + 0.18 * downwind / np.sqrt(1.0 + 0.0001 * downwind) + 20.0
                sigma_z = src_sz0[k] + 0.10 * downwind / np.sqrt(1.0 + 0.0015 * downwind) + 10.0

                peak = Q / (6.283185 * max(u, 0.5) * sigma_y * sigma_z)
                exp_y = np.exp(-0.5 * (crosswind / sigma_y) ** 2)
                exp_z = np.exp(-0.5 * (src_heights[k] / sigma_z) ** 2)

                plume_val = peak * exp_y * exp_z

            # Берем максимум из радиального пятна и шлейфа, чтобы в центре трубы
            # они плавно перетекали друг в друга без искусственного удвоения яркости.
            # После этого суммируем с остальными источниками (суперпозиция).
            val += max(plume_val, puff_val)

        result[i] = val

    return result