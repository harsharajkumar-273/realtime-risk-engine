import asyncio
import time
import numpy as np
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from core.pipeline import RiskPipeline, RiskDecisionResponse
from stream.generator import TransactionStreamGenerator
from api.websocket import ws_manager
from config import settings

router = APIRouter()
pipeline = RiskPipeline()
stream_generator = TransactionStreamGenerator()

# Telemetry state
stream_task: Optional[asyncio.Task] = None
is_streaming = False
current_tps = 15.0

metrics_store = {
    "total_processed": 0,
    "allowed": 0,
    "review": 0,
    "declined": 0,
    "latencies_ms": []
}

class TransactionRequest(BaseModel):
    transaction_id: Optional[str] = None
    account_id: str
    amount: float
    currency: str = "USD"
    country: str = "US"
    mcc: int = 5411
    lat: float = 40.7128
    lon: float = -74.0060
    timestamp: Optional[float] = None

class StreamControlRequest(BaseModel):
    tps: float = Field(default=15.0, ge=1.0, le=500.0)

class AnomalySimulateRequest(BaseModel):
    fraud_type: str  # "HIGH_AMOUNT", "VELOCITY_SPIKE", "IMPOSSIBLE_TRAVEL", "SANCTIONED_GEO"

@router.post("/evaluate", response_model=RiskDecisionResponse)
async def evaluate_transaction(tx_req: TransactionRequest):
    tx_dict = tx_req.model_dump()
    if not tx_dict.get("transaction_id"):
        tx_dict["transaction_id"] = f"tx_{int(time.time()*1000)}"
    if not tx_dict.get("timestamp"):
        tx_dict["timestamp"] = time.time()
        
    result = pipeline.process_transaction(tx_dict)
    
    # Update telemetry
    metrics_store["total_processed"] += 1
    if result.decision == "ALLOW":
        metrics_store["allowed"] += 1
    elif result.decision == "REVIEW":
        metrics_store["review"] += 1
    else:
        metrics_store["declined"] += 1
        
    metrics_store["latencies_ms"].append(result.latencies["total_ms"])
    if len(metrics_store["latencies_ms"]) > 2000:
        metrics_store["latencies_ms"] = metrics_store["latencies_ms"][-1000:]
        
    # Broadcast to WebSocket dashboard
    await ws_manager.broadcast({
        "type": "TRANSACTION_PROCESSED",
        "data": {
            "transaction": tx_dict,
            "decision": result.model_dump()
        }
    })
    
    return result

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "circuit_state": pipeline.circuit_breaker.state.value,
        "feature_store_backend": "Redis" if pipeline.feature_store.use_redis else "In-Memory Fallback",
        "ml_model_loaded": pipeline.ml_predictor.is_loaded
    }

@router.get("/metrics")
async def get_metrics():
    lats = metrics_store["latencies_ms"]
    p50 = float(np.percentile(lats, 50)) if lats else 0.0
    p95 = float(np.percentile(lats, 95)) if lats else 0.0
    p99 = float(np.percentile(lats, 99)) if lats else 0.0
    avg_lat = float(np.mean(lats)) if lats else 0.0
    
    return {
        "total_processed": metrics_store["total_processed"],
        "decisions": {
            "ALLOW": metrics_store["allowed"],
            "REVIEW": metrics_store["review"],
            "DECLINE": metrics_store["declined"]
        },
        "is_streaming": is_streaming,
        "current_tps": current_tps,
        "latencies": {
            "avg_ms": round(avg_lat, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2)
        }
    }

async def _stream_loop(tps: float):
    global is_streaming
    is_streaming = True
    interval = 1.0 / tps
    
    while is_streaming:
        tx = stream_generator.generate_single_transaction()
        result = pipeline.process_transaction(tx)
        
        metrics_store["total_processed"] += 1
        if result.decision == "ALLOW":
            metrics_store["allowed"] += 1
        elif result.decision == "REVIEW":
            metrics_store["review"] += 1
        else:
            metrics_store["declined"] += 1
            
        metrics_store["latencies_ms"].append(result.latencies["total_ms"])
        if len(metrics_store["latencies_ms"]) > 2000:
            metrics_store["latencies_ms"] = metrics_store["latencies_ms"][-1000:]
            
        await ws_manager.broadcast({
            "type": "TRANSACTION_PROCESSED",
            "data": {
                "transaction": tx,
                "decision": result.model_dump()
            }
        })
        
        await asyncio.sleep(interval)

@router.post("/stream/start")
async def start_stream(req: StreamControlRequest, background_tasks: BackgroundTasks):
    global stream_task, is_streaming, current_tps
    if is_streaming:
        return {"status": "already_running", "tps": current_tps}
        
    current_tps = req.tps
    stream_task = asyncio.create_task(_stream_loop(req.tps))
    return {"status": "started", "tps": req.tps}

@router.post("/stream/stop")
async def stop_stream():
    global stream_task, is_streaming
    is_streaming = False
    if stream_task:
        stream_task.cancel()
        stream_task = None
    return {"status": "stopped"}

@router.post("/simulate/anomaly")
async def simulate_anomaly(req: AnomalySimulateRequest):
    tx = stream_generator.generate_single_transaction(force_fraud_type=req.fraud_type)
    result = pipeline.process_transaction(tx)
    
    await ws_manager.broadcast({
        "type": "TRANSACTION_PROCESSED",
        "data": {
            "transaction": tx,
            "decision": result.model_dump()
        }
    })
    
    return {"injected_fraud_type": req.fraud_type, "result": result}
