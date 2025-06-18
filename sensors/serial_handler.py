import serial
from queue import Queue, Empty
import threading

from config import Config
from sensors.state import state

SERIAL_ADDRESS = Config.SERIAL_ADDRESS
SERIAL_BAUDRATE = Config.SERIAL_BAUDRATE

ser = serial.Serial(SERIAL_ADDRESS, SERIAL_BAUDRATE, timeout=1)

outgoing_message_queue = Queue()

def _write_to_serial():
    while True:
        try:
            cmd = outgoing_message_queue.get(timeout=1)
            ser.write(cmd + "\n").encode()
        except Empty:
            continue

def _read_from_serial(port=SERIAL_ADDRESS, baudrate=SERIAL_BAUDRATE):
    with serial.Serial(port, baudrate, timeout=1) as ser:
        while True:
            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue
            state.process_raw_message(line)

threading.Thread(target=_write_to_serial, daemon=True).start()
threading.Thread(target=_read_from_serial, daemon=True).start()
