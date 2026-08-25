import pytest
import time
from core.feature_store import FeatureStore

def test_feature_store_rolling_aggregates():
    store = FeatureStore()
    account_id = "test_acc_001"
    now = time.time()
    
    # 1. Initially empty
    feats = store.get_user_features(account_id, now)
    assert feats["tx_count_5m"] == 0
    assert feats["spend_24h"] == 0.0
    
    # 2. Add 3 transactions
    store.update_user_features(account_id, 100.0, 40.71, -74.00, now - 100)
    store.update_user_features(account_id, 200.0, 40.72, -74.01, now - 50)
    store.update_user_features(account_id, 300.0, 40.73, -74.02, now)
    
    feats_updated = store.get_user_features(account_id, now)
    assert feats_updated["tx_count_5m"] == 3
    assert feats_updated["spend_24h"] == 600.0
    assert feats_updated["avg_amount_24h"] == 200.0
    assert feats_updated["last_lat"] == 40.73
    assert feats_updated["last_lon"] == -74.02
    assert feats_updated["last_timestamp"] == now
