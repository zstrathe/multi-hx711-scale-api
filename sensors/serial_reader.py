import serial
import json
from db.database import log_event
from config import Config
from sensors import state

SERIAL_ADDRESS = Config.SERIAL_ADDRESS
SERIAL_BAUDRATE = Config.SERIAL_BAUDRATE

def read_from_serial(port=SERIAL_ADDRESS, baudrate=SERIAL_BAUDRATE):
    with serial.Serial(port, baudrate, timeout=1) as ser:
        baseline = None
        while True:
            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                current = data.get("average")
                if current is None:
                    continue
                state.current_weight = current
                if baseline is None:
                    baseline = current
                    continue
                if abs(current - baseline) >= 5:
                    log_event(baseline, current)
                    baseline = current
            except json.JSONDecodeError:
                continue