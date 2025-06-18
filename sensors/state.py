from datetime import datetime, timedelta
import uuid
import json
import logging
from collections import deque
import threading

from db.database import log_event
from sensors.serial_handler import outgoing_message_queue

class StateManager():
    _status_buffer_lock = threading.Lock()
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

    def _handle_data_message(self, message: dict):
        current = message.get("average")

        if current is None:
            return
        type(self).current_weight = current
        if type(self)._event_delta_baseline is None:
            type(self)._event_delta_baseline = current
            return
        if abs(current - type(self)._event_delta_baseline) >= 5:
            log_event(type(self)._event_delta_baseline, current)
            type(self)._event_delta_baseline = current
    
    def _try_parse_to_json(self, value: str):
        try:
            return json.loads(value), True
        except json.JSONDecodeError:
            return value, False

    def process_raw_message(self, value: str):
        value, is_json = self._try_parse_to_json(value)

        if is_json:
            if value.get("status"):
                # if there is a status field, then append it to the buffer
                self.append_to_status_message_buffer(value)
            else:
                # assume it's a data message
                self._handle_data_message(value)
        else:
            # assume message is meant to be informational / print to terminal
            logging.info(value)

    def append_to_status_message_buffer(self, message: dict):
        """
        Add a new message to the buffer and ID.
        Thread-safe.
        """
        with type(self)._status_buffer_lock:
            type(self)._status_message_id_counter += 1
            message = {
                "id": type(self)._status_message_id_counter,
                "value": message
            }
            type(self)._status_message_buffer.append(message)


    def get_messages_since(self, last_seen_id: int):
        """
        Return a list of messages where id > last_seen_id.
        Thread-safe.
        """
        with type(self)._status_buffer_lock:
            return [msg for msg in type(self)._status_message_buffer if msg["id"] > last_seen_id]
        


    def get_latest_message(self):
        """
        Return the most recent message (or None if buffer is empty).
        Thread-safe.
        """
        with type(self)._status_buffer_lock:
            if type(self)._status_message_buffer:
                return type(self)._status_message_buffer[-1]
            return None


    def get_all_messages(self):
        """
        Return all messages currently in the buffer.
        Thread-safe.
        """
        with type(self)._status_buffer_lock:
            return list(type(self)._status_message_buffer)

    def watch_for_message(self, message_uuid, timeout = 20):
        timeout_dt = datetime.now() + timedelta(seconds=timeout)
        
        while datetime.now() < timeout_dt: 
            for incoming_message in self.get_messages_since(self._instance_buffer_position):
                msg_id, raw_value = incoming_message.values()
                try:
                    parsed_value = json.loads(raw_value)
                except json.JSONDecodeError:
                    continue

                if parsed_value.get("message_uuid", "") == message_uuid:
                    self._instance_buffer_position = msg_id
                    # drop the "uuid" k/v pair as it's no longer needed from here on
                    return {k: v for k, v in parsed_value.items() if k != "message_uuid"}
                
                self._instance_buffer_position = msg_id
            
            threading.Event().wait(0.1)
        
        logging.info(f"No response received, timed out ({timeout} seconds)")
        return {}        
    
    def send_message_wait_for_response(self, message: str):
        """
        Send a serial message, wait for, and return a status response
        """
        message_uuid = str(uuid.uuid4())
        outgoing_message_queue.put({"message": message, "message_uuid": message_uuid})
        
        response = self.watch_for_message(message_uuid)

        logging.info(f"Sent message: {response.get('status', 'ERROR: no status returned!')}!")
        return response

state = StateManager()
