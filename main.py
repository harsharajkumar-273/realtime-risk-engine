import os
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from config import settings
from api.routes import router as api_router
from api.websocket import ws_manager
from ml.predictor import MLPredictor

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print(f"🚀 Launching {settings.APP_NAME}")
    print(f"📍 Web UI available at: http://localhost:{settings.PORT}")
    print("=" * 60)
    # Warm up ML predictor
    predictor = MLPredictor()
    yield
    print("Shutting down risk engine...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Low-Latency Event-Driven Financial Transaction Risk Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Mount Static Files for Dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API Router
app.include_router(api_router, prefix="/api/v1", tags=["Risk Engine API"])

@app.get("/", include_in_schema=False)
async def get_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
