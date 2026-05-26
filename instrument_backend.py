# This is the API for the function so the app has access
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/readings")
def get_readings():
    return {"temperature": 23.4, "pressure": 101.3}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
