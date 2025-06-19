import uuid
import json
import logging
import threading
import concurrent.futures

from db.database import log_event
from sensors.serial_handler import outgoing_message_queue

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

class MessageHandler():
    """
    Singleton class for handling messages between RPi and Arduino via serial
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self._pending_message_futures = {}
        self._futures_lock = threading.Lock()
    
    def _try_parse_to_json(self, value: str):
        try:
            return json.loads(value), True
        except json.JSONDecodeError:
            return value, False

    def process_raw_message(self, value: str):
        value, is_json = self._try_parse_to_json(value)

        if is_json:

            # handle status messages asynchronously with futures
            msg_uuid = value.get("message_uuid")
            if msg_uuid:
                with self._futures_lock:
                    future = self._pending_message_futures.pop(msg_uuid, None)
                if future and not future.done():
                    future.set_result(value)
    
            else:
                # assume it's a data message if there is no message_uuid field
                scale_state._handle_data_message(value)
        else:
            # assume message is meant to be informational / print to terminal
            logging.info(value)

    def watch_for_message(self, message_uuid, timeout = 20):
        future = concurrent.futures.Future()
        with self._futures_lock:
            self._pending_message_futures[message_uuid] = future
        
        try:
            response_message = future.result(timeout=timeout)
            # filter out the message_uuid field as itn's no longer relevant
            response_message = {k: v for k, v in response_message.items() if k != "message_uuid"}
            return response_message
        except concurrent.futures.TimeoutError:
            with self._futures_lock:
                self._pending_message_futures.pop(message_uuid, None)
            logging.info(f"No response received, timed out ({timeout} seconds)")
            return {}

    def send_message_wait_for_response(self, message: str):
        """
        Send a serial message, wait for, and return a status response
        """
        message_uuid = str(uuid.uuid4())
        outgoing_message_queue.put({"message": message, "message_uuid": message_uuid})
        
        response = self.watch_for_message(message_uuid)

        logging.info(f"Sent message: {response.get('status', 'ERROR: no status returned')}")
        return response

scale_state = ScaleStateManager()
message_handler = MessageHandler()