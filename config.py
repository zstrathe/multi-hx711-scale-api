import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SERIAL_ADDRESS = os.getenv("SERIAL_ADDRESS")
    SERIAL_BAUDRATE = os.getenv("SERIAL_BAUDRATE")