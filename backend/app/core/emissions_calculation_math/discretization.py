import numpy as np
from matplotlib.path import Path
from backend.app.core.emissions_calculation_math.math_numba import lat_lon_to_meters_yandex_single


def discretize_sources(sources_db):
    v_xs, v_ys, v_rates, v_heights = [], [], [], []
    v_sy0, v_sz0 = [], []  # Массивы для начального расширения

    MAX_POINTS_PER_SOURCE = 200
    MIN_STEP_METERS = 100.0

    for s in sources_db:
        s_type_str = s.type.value if hasattr(s.type, 'value') else str(s.type)

        if s_type_str == "point" or not s.coordinates:
            mx, my = lat_lon_to_meters_yandex_single(s.latitude, s.longitude)
            v_xs.append(mx)
            v_ys.append(my)
            v_rates.append(s.emission_rate)
            v_heights.append(s.height)
            v_sy0.append(0.0)
            v_sz0.append(0.0)

        elif s_type_str == "line":
            coords = s.coordinates
            line_points = []
            for i in range(len(coords) - 1):
                p1_x, p1_y = lat_lon_to_meters_yandex_single(coords[i][0], coords[i][1])
                p2_x, p2_y = lat_lon_to_meters_yandex_single(coords[i + 1][0], coords[i + 1][1])

                dist = np.hypot(p2_x - p1_x, p2_y - p1_y)

                step = max(MIN_STEP_METERS, dist / MAX_POINTS_PER_SOURCE)
                num_points = max(2, int(dist / step))

                xs = np.linspace(p1_x, p2_x, num_points, endpoint=True)
                ys = np.linspace(p1_y, p2_y, num_points, endpoint=True)
                line_points.extend(list(zip(xs, ys)))

            if not line_points:
                continue

            unique_points = list(dict.fromkeys(line_points))
            rate_per_point = s.emission_rate / len(unique_points)

            for x, y in unique_points:
                v_xs.append(x)
                v_ys.append(y)
                v_rates.append(rate_per_point)
                v_heights.append(s.height)
                v_sy0.append(step)  # <--- ИЗМЕНЕНИЕ ЗДЕСЬ
                v_sz0.append(5.0)

        elif s_type_str == "polygon":
            coords = s.coordinates
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            poly_points = [lat_lon_to_meters_yandex_single(c[0], c[1]) for c in coords]
            poly_path = Path(poly_points)

            xs, ys = zip(*poly_points)
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            area = (max_x - min_x) * (max_y - min_y)
            dynamic_step = max(MIN_STEP_METERS, np.sqrt(area / MAX_POINTS_PER_SOURCE))

            grid_x, grid_y = np.meshgrid(
                np.arange(min_x, max_x, dynamic_step),
                np.arange(min_y, max_y, dynamic_step)
            )
            flat_grid = np.vstack((grid_x.flatten(), grid_y.flatten())).T
            mask = poly_path.contains_points(flat_grid)
            inside_points = flat_grid[mask]

            if len(inside_points) == 0:
                inside_points = [[np.mean(xs), np.mean(ys)]]

            rate_per_point = s.emission_rate / len(inside_points)

            for x, y in inside_points:
                v_xs.append(x)
                v_ys.append(y)
                v_rates.append(rate_per_point)
                v_heights.append(s.height)
                v_sy0.append(dynamic_step)
                v_sz0.append(5.0)

    return (
        np.array(v_xs, dtype=np.float32),
        np.array(v_ys, dtype=np.float32),
        np.array(v_rates, dtype=np.float32),
        np.array(v_heights, dtype=np.float32),
        np.array(v_sy0, dtype=np.float32),
        np.array(v_sz0, dtype=np.float32)
    )