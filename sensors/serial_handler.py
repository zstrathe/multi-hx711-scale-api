import logging
import serial
from queue import Empty
from concurrent.futures import ThreadPoolExecutor

from config import Config
from sensors.message_queue import outgoing_message_queue
from sensors.state import message_handler

SERIAL_ADDRESS = Config.SERIAL_ADDRESS
SERIAL_BAUDRATE = Config.SERIAL_BAUDRATE

ser = serial.Serial(SERIAL_ADDRESS, SERIAL_BAUDRATE, timeout=1)

def _write_to_serial():
    while True:
        try:
            cmd = outgoing_message_queue.get(timeout=1)
            ser.write((cmd + "\n").encode())
        except Empty:
            continue
        except Exception as e:
            logging.warning(f"Write error: {e}")

def _read_from_serial(port=SERIAL_ADDRESS, baudrate=SERIAL_BAUDRATE):
    while True:
        try:
            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue
            message_handler.process_raw_message(line)
        except Exception as e:
            logging.warning(f"Read error: {e}")

executor = ThreadPoolExecutor(max_workers=2)
executor.submit(_write_to_serial)
executor.submit(_read_from_serial)
