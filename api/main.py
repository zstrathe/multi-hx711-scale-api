from fastapi import FastAPI, Body, Form, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import Config
from datetime import datetime
import csv
import io

from db.database import get_events, get_all_events, get_filtered_events
from sensors.state import scale_state, message_handler
from sensors.serial_handler import start_serial_threads

SERIAL_ADDRESS = Config.SERIAL_ADDRESS
SERIAL_BAUDRATE = Config.SERIAL_BAUDRATE

app = FastAPI()
templates = Jinja2Templates(directory="web/templates")

@app.on_event("startup")
def startup_event():
    start_serial_threads()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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
    return {"weight": scale_state.current_weight}


@app.post("/calibrate")
def calibrate(reference_weight: float = Body(...)):
    result = message_handler.send_message_wait_for_response(f"CALIBRATE:{reference_weight}")
    return result if result.get("status") == "success" else JSONResponse(content=result, status_code=500)


@app.post("/tare")
def tare():
    result = message_handler.send_message_wait_for_response("TARE")
    return result if result.get("status") == "success" else JSONResponse(content=result, status_code=500)