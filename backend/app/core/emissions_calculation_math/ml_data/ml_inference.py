import os
import numpy as np
import joblib
import logging

logger = logging.getLogger("uvicorn")


class NumpyMLModelSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NumpyMLModelSingleton, cls).__new__(cls)
            cls._instance.weights = []
            cls._instance.scaler_x = None
            cls._instance.scaler_y = None
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir)

            # Загружаем скейлеры
            self.scaler_x = joblib.load(os.path.join(data_dir, "scaler_x.pkl"))
            self.scaler_y = joblib.load(os.path.join(data_dir, "scaler_y.pkl"))

            # Загружаем матрицы весов
            data = np.load(os.path.join(data_dir, "model_weights.npz"))

            # Распаковываем веса по слоям (W_0, b_0), (W_1, b_1) и т.д.
            i = 0
            while f'W_{i}' in data:
                self.weights.append((data[f'W_{i}'], data[f'b_{i}']))
                i += 1

            logger.info(f"NumPy ML Модель (слоев: {len(self.weights)}) успешно загружена.")
        except Exception as e:
            logger.error(f"Ошибка загрузки NumPy ML модели: {e}")

    def predict_grid(self, lat_grid, lon_grid, temp, humidity, wind_speed, wind_dir):
        if not self.weights:
            return np.zeros_like(lat_grid, dtype=np.float32)

        flat_lat = lat_grid.flatten()
        flat_lon = lon_grid.flatten()
        n_points = len(flat_lat)

        # Формируем входные данные
        X_raw = np.column_stack((
            flat_lat,
            flat_lon,
            np.full(n_points, temp, dtype=np.float32),
            np.full(n_points, humidity, dtype=np.float32),
            np.full(n_points, wind_speed, dtype=np.float32),
            np.full(n_points, wind_dir, dtype=np.float32)
        ))

        # Масштабируем
        X_scaled = self.scaler_x.transform(X_raw)

        # --- ИНФЕРЕНС НЕЙРОСЕТИ НА ЧИСТОМ NUMPY ---
        out = X_scaled
        for i, (W, b) in enumerate(self.weights):
            # Умножение матриц: X * W + b
            out = np.dot(out, W) + b

            # Функция активации ReLU (np.maximum(0, x)) для всех слоев, КРОМЕ ПОСЛЕДНЕГО
            if i < len(self.weights) - 1:
                out = np.maximum(0, out)

        # Обратное масштабирование
        y_pred = self.scaler_y.inverse_transform(out)

        # Защита от отрицательных концентраций
        y_pred = np.clip(y_pred, 0, None)

        return y_pred.reshape(lat_grid.shape).astype(np.float32)


# Глобальный объект для импорта
ml_inference = NumpyMLModelSingleton()