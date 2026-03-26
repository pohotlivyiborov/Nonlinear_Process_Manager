import numpy as np


def colorize_tile_numpy(conc_grid, pdk=0.008, alpha_bg=110):
    c = conc_grid.flatten()

    # Цвета (R, G, B, Alpha)
    color_green = np.array([46, 204, 113, alpha_bg])
    color_yellow = np.array([241, 196, 15, 180])
    color_orange = np.array([230, 126, 34, 210])
    color_red = np.array([231, 76, 60, 240])

    rgba = np.zeros((len(c), 4), dtype=np.float32)

    t0, t1, t2, t3 = pdk * 0.001, pdk * 0.2, pdk * 0.6, pdk * 1.0

    m_bg = c <= t0
    m_gy = (c > t0) & (c <= t1)
    m_yo = (c > t1) & (c <= t2)
    m_or = (c > t2)

    rgba[m_bg] = color_green

    if np.any(m_gy):
        f = (c[m_gy] - t0) / (t1 - t0)
        rgba[m_gy] = color_green * (1 - f[:, None]) + color_yellow * f[:, None]
    if np.any(m_yo):
        f = (c[m_yo] - t1) / (t2 - t1)
        rgba[m_yo] = color_yellow * (1 - f[:, None]) + color_orange * f[:, None]
    if np.any(m_or):
        f = np.clip((c[m_or] - t2) / (t3 - t2), 0, 1)
        rgba[m_or] = color_orange * (1 - f[:, None]) + color_red * f[:, None]

    return rgba.astype(np.uint8).reshape((256, 256, 4))
