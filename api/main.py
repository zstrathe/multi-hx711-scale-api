from fastapi import FastAPI, Body, Form, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sensors import state
from config import Config
from db.database import get_events, get_all_events, get_filtered_events
from datetime import datetime
import csv
import io
import serial
import time
import json

SERIAL_ADDRESS = Config.SERIAL_ADDRESS
SERIAL_BAUDRATE = Config.SERIAL_BAUDRATE

app = FastAPI()
templates = Jinja2Templates(directory="web/templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("calibrate.html", {"request": request})

@app.get("/events", response_class=HTMLResponse)
def show_events(request: Request, min_weight: float = Query(None), max_weight: float = Query(None),
                start: datetime = Query(None), end: datetime = Query(None)):
    events = get_filtered_events(min_weight, max_weight, start.isoformat() if start else None,
                                 end.isoformat() if end else None)
    return templates.TemplateResponse("events.html", {"request": request, "events": events})

@app.get("/events.csv")
def download_csv(min_weight: float = Query(None), max_weight: float = Query(None),
                 start: datetime = Query(None), end: datetime = Query(None)):
    events = get_filtered_events(min_weight, max_weight, start.isoformat() if start else None,
                                 end.isoformat() if end else None)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["timestamp", "starting_weight", "final_weight"])
    writer.writeheader()
    writer.writerows(events)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=events.csv"})


@app.get("/status")
def status():
    return {"weight": state.current_weight}

def send_serial_command(command: str, wait_for_response_timeout: int = 10) -> dict:
    try:
        with serial.Serial(SERIAL_ADDRESS, SERIAL_BAUDRATE, timeout=1) as ser:
            ser.flushInput()
            ser.write((command + "\n").encode())
            
            deadline = time.time() + wait_for_response_timeout
            
            while time.time() < deadline:
                if ser.in_waiting:
                    line = ser.readline().decode().strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        return data
                    except json.JSONDecodeError:
                        print(f"Non-JSON line: {line}")
                        continue

            return {
                "status": "error", 
                "error_message": f"Timed out waiting for JSON response for command: {command}"
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "error_message": str(e)
        }

@app.post("/calibrate")
def calibrate(reference_weight: float = Body(...)):
    result = send_serial_command(f"CALIBRATE:{reference_weight}")
    return result if result.get("status") == "success" else JSONResponse(content=result, status_code=500)

@app.post("/tare")
def tare():
    result = send_serial_command("TARE")
    return result if result.get("status") == "success" else JSONResponse(content=result, status_code=500)