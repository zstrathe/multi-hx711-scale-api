import uuid
import json
import logging
from collections import deque
from threading import Lock

from db.database import log_event
from sensors.serial_handler import outgoing_message_queue

class StateManager():
    _status_buffer_lock = Lock()
    _status_buffer_maxlen = 100
    _status_message_buffer = deque(maxlen=_status_buffer_maxlen)
    _status_message_id_counter = 0

    current_weight = 0.0
    _event_delta_baseline = None
    
    def __init__(self):
        self._instance_buffer_position = 0

    def _check_if_message_is_data_or_status(self, message: str):
        try:
            message = json.loads(message)
            if message.get("status"):
                return "status"
            return "data"

        except json.JSONDecodeError:
            return

    def _handle_data_message(self, message: json):
        current = message.get("average")

        if current is None:
            return
        state.current_weight = current
        if self._event_delta_baseline is None:
            self._event_delta_baseline = current
            return
        if abs(current - self._event_delta_baseline) >= 5:
            log_event(self._event_delta_baseline, current)
            self._event_delta_baseline = current

    def process_raw_message(self, value: str):
        message_type = self._check_if_message_is_data_or_status(value)
            
        if message_type == "data":
            self._handle_data_message(value)    
        elif message_type == "status":
            self.append_message_to_buffer(value)
        else:
            # assume message is meant to be informational (printed to terminal)
            logging.info(value)

    def append_message_to_buffer(self, value: str):
        """
        Add a new message to the buffer and ID.
        Thread-safe.
        """
        global _message_id_counter

        with self._status_buffer_lock:
            _message_id_counter += 1
            message = {
                "id": _message_id_counter,
                "value": value
            }
            self._status_message_buffer.append(message)


    def get_messages_since(self, last_seen_id: int):
        """
        Return a list of messages where id > last_seen_id.
        Thread-safe.
        """
        with self._status_buffer_lock:
            messages = [msg for msg in self._status_message_buffer if msg["id"] > last_seen_id]
        return [message["value"] for message in messages] 


    def get_latest_message(self):
        """
        Return the most recent message (or None if buffer is empty).
        Thread-safe.
        """
        with self._status_buffer_lock:
            if self._status_message_buffer:
                message = self._status_message_buffer[-1]
                return message["value"]
            return None


    def get_all_messages(self):
        """
        Return all messages currently in the buffer.
        Thread-safe.
        """
        with self._status_buffer_lock:
            messages = list(self._status_message_buffer)
        return [message["value"] for message in messages]
        
    
    def send_message_wait_for_response(self, message: str):
        """
        Send a serial message, wait for, and return a status response
        """
        message_uuid = uuid.uuid4()
        outgoing_message_queue.put({"message": message, "message_uuid": message_uuid})
        
        buffer_position = self._instance_buffer_position

        for incoming_message in self.get_messages_since(buffer_position):
            if incoming_message.get("uuid", "") == message_uuid:
                logging.info("Sent message: successful!")
                return message["message"]

state = StateManager()
