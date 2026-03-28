'''Singleton хранения кэша выбросов'''


class PollutionState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PollutionState, cls).__new__(cls)
            cls._instance.cached_sources = {} #substances_id: кэшированные данные
            cls._instance.sources_time = {} #substances_id: время
            cls._instance.cached_params = None
            cls._instance.params_time = 0
        return cls._instance

    def invalidate_sources(self):
        self.cached_sources = None
        self.sources_time = 0


# Глобальный объект кэша
pollution_state = PollutionState()
