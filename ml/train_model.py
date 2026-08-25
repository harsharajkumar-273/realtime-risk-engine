import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from config import settings

def generate_synthetic_data(n_samples: int = 10000) -> pd.DataFrame:
    """Generate realistic synthetic financial transaction dataset with fraud patterns."""
    np.random.seed(42)
    
    # Baseline normal transactions
    amount = np.random.exponential(scale=60, size=n_samples) + 2.0
    tx_count_5m = np.random.poisson(lam=0.8, size=n_samples)
    spend_24h = amount * (np.random.poisson(lam=3, size=n_samples) + 1)
    avg_amount_24h = spend_24h / (np.random.poisson(lam=3, size=n_samples) + 1)
    is_foreign = np.random.choice([0, 1], size=n_samples, p=[0.92, 0.08])
    hour_of_day = np.random.randint(0, 24, size=n_samples)
    mcc_risk_score = np.random.choice([0.1, 0.3, 0.8], size=n_samples, p=[0.8, 0.15, 0.05])
    
    # Amount relative to user's 24h average
    amount_ratio = amount / (avg_amount_24h + 1.0)
    
    # Target: Fraud Label (Default 0 = Legit)
    is_fraud = np.zeros(n_samples, dtype=int)
    
    # Inject Fraud Pattern 1: High Velocity Spikes
    fraud_mask_1 = (tx_count_5m >= 4) & (amount > 150)
    is_fraud[fraud_mask_1] = 1
    
    # Inject Fraud Pattern 2: Huge amount relative to historical avg + Night time
    fraud_mask_2 = (amount_ratio > 4.5) & ((hour_of_day < 5) | (hour_of_day > 23))
    is_fraud[fraud_mask_2] = 1
    
    # Inject Fraud Pattern 3: High MCC risk + Foreign + High Amount
    fraud_mask_3 = (mcc_risk_score > 0.5) & (is_foreign == 1) & (amount > 300)
    is_fraud[fraud_mask_3] = 1

    df = pd.DataFrame({
        "amount": amount,
        "tx_count_5m": tx_count_5m,
        "spend_24h": spend_24h,
        "avg_amount_24h": avg_amount_24h,
        "amount_ratio": amount_ratio,
        "is_foreign": is_foreign,
        "hour_of_day": hour_of_day,
        "mcc_risk_score": mcc_risk_score,
        "is_fraud": is_fraud
    })
    
    return df

def train_and_save_model():
    print("Generating synthetic financial risk dataset...")
    df = generate_synthetic_data(n_samples=15000)
    
    feature_cols = [
        "amount", "tx_count_5m", "spend_24h", "avg_amount_24h", 
        "amount_ratio", "is_foreign", "hour_of_day", "mcc_risk_score"
    ]
    
    X = df[feature_cols]
    y = df["is_fraud"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Try XGBoost, fallback to RandomForest
    try:
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            random_state=42,
            eval_metric="logloss"
        )
        model_type = "XGBoost"
    except ImportError:
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
        model_type = "RandomForest"

    print(f"Training {model_type} Risk Model...")
    model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= settings.RISK_SCORE_REVIEW_THRESHOLD).astype(int)
    
    auc_score = roc_auc_score(y_test, y_pred_proba)
    print(f"Model AUC-ROC Score: {auc_score:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))
    
    # Feature Importances
    if hasattr(model, "feature_importances_"):
        importances = dict(zip(feature_cols, model.feature_importances_))
    else:
        importances = {col: 1.0 / len(feature_cols) for col in feature_cols}

    artifact = {
        "model": model,
        "model_type": model_type,
        "feature_cols": feature_cols,
        "feature_importances": importances,
        "auc_score": auc_score
    }
    
    os.makedirs(os.path.dirname(settings.ML_MODEL_PATH), exist_ok=True)
    joblib.dump(artifact, settings.ML_MODEL_PATH)
    print(f"Saved trained risk model artifact to '{settings.ML_MODEL_PATH}'")

if __name__ == "__main__":
    train_and_save_model()
