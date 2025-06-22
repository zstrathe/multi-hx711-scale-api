from db.database import log_event

class ScaleStateManager():
    """
    Singleton class for managing state, such as:
        - current weight on scale, 
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance
    
    def _init_state(self):
        # init class variables
        self.current_weight = 0.0
        self._event_delta_baseline = None

    def _handle_data_message(self, message: dict):
        current = message.get("weight")

        if current is None:
            return
        
        self.current_weight = current

        if self._event_delta_baseline is None:
            self._event_delta_baseline = current
            return
        
        if abs(current - self._event_delta_baseline) >= 5:
            log_event(self._event_delta_baseline, current)
            self._event_delta_baseline = current

scale_state = ScaleStateManager()
