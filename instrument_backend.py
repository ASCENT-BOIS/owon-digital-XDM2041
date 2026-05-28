# This is the API for the function so the app has access
from enum import Enum

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.pyvisa_backend import PyVISAMultimeter


# Setup the ENUM for the mode
class MultimeterMode(str, Enum):
    voltageDC = "VDC"
    voltageAC = "VAC"
    resistance = "OHM"
    capacitance = "CAP"
    current = "A"
    frequency = "HZ"


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Setup the multimeter
meter = PyVISAMultimeter()


# A test endpoint to ensure the server is running
@app.get("/test")
def test_endpoint():
    return {"is_running": True}


# Connect to the multimeter
@app.post("/connect")
def connect():
    if not meter.connected:
        meter.connect()


# Disconnect from the multimeter
@app.post("/disconnect")
def disconnect():
    if meter.connected:
        meter.disconnect()


# Switch multimeter mode
@app.post("/mode/")
def set_mode(mode: MultimeterMode):
    if meter.connected:
        meter.set_mode(mode.value)


# Measure the value
@app.get("/measure")
def measure():
    if meter.connected:
        return {"value": meter.measure()}
    else:
        return {"value": -1e10}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
