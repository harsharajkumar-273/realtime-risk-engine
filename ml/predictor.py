import time
import os
import joblib
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from config import settings

logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self, model_path: str = settings.ML_MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.feature_cols = []
        self.feature_importances = {}
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            logger.warning(f"Model file '{self.model_path}' not found. Training model now...")
            try:
                from ml.train_model import train_and_save_model
                train_and_save_model()
            except Exception as e:
                logger.error(f"Failed to auto-train model: {e}")
                return
                
        try:
            artifact = joblib.load(self.model_path)
            self.model = artifact["model"]
            self.feature_cols = artifact["feature_cols"]
            self.feature_importances = artifact.get("feature_importances", {})
            self.is_loaded = True
            logger.info(f"Loaded ML Risk Model ({artifact.get('model_type', 'Classifier')}) successfully.")
        except Exception as e:
            logger.error(f"Failed to load ML model artifact: {e}")
            self.is_loaded = False

    def predict_risk(self, features: Dict[str, Any]) -> Tuple[float, List[str], float]:
        """Perform low-latency risk scoring and top feature attributions."""
        start_time = time.perf_counter()
        
        if not self.is_loaded:
            raise RuntimeError("ML model artifact not loaded.")
            
        # Build feature vector matching feature_cols order
        row = []
        for col in self.feature_cols:
            row.append(float(features.get(col, 0.0)))
            
        X = np.array([row], dtype=np.float32)
        
        # Fast prediction probability
        prob = float(self.model.predict_proba(X)[0, 1])
        
        # Calculate top contributing features for reason codes
        top_reasons = []
        if prob > settings.RISK_SCORE_REVIEW_THRESHOLD:
            # Simple attribution weighting by feature magnitude * global importance
            contributions = []
            for idx, col in enumerate(self.feature_cols):
                val = row[idx]
                imp = self.feature_importances.get(col, 0.1)
                contributions.append((col, val * imp))
            
            contributions.sort(key=lambda x: x[1], reverse=True)
            top_reasons = [f"ML_FLAG_{col.upper()}" for col, _ in contributions[:2]]

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return prob, top_reasons, latency_ms
