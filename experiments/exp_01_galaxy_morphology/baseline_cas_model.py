"""
baseline_cas_model.py - Classical Concentration-Asymmetry-Smoothness (CAS) baseline
for galaxy morphology classification.
"""

import os
import json
import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import rotate, uniform_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def compute_cas_features(img_path: str) -> dict:
    """
    Computes classical non-parametric Concentration, Asymmetry, and Smoothness (CAS) parameters.
    """
    img = Image.open(img_path).convert("L")  # Convert to greyscale
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape
    cy, cx = h // 2, w // 2

    # Background subtraction
    bg = np.median(arr[:15, :15])
    I = np.clip(arr - bg, 0, None)
    total_flux = np.sum(I) + 1e-6

    # Radial flux curve for Concentration C
    y, x = np.ogrid[:h, :w]
    radii = np.sqrt((x - cx)**2 + (y - cy)**2)
    sorted_idx = np.argsort(radii.flat)
    sorted_flux = np.cumsum(I.flat[sorted_idx])
    
    r20_idx = np.searchsorted(sorted_flux, 0.20 * total_flux)
    r50_idx = np.searchsorted(sorted_flux, 0.50 * total_flux)
    r80_idx = np.searchsorted(sorted_flux, 0.80 * total_flux)
    
    r20 = max(1.0, radii.flat[sorted_idx[min(r20_idx, len(sorted_idx)-1)]])
    r50 = max(1.5, radii.flat[sorted_idx[min(r50_idx, len(sorted_idx)-1)]])
    r80 = max(2.0, radii.flat[sorted_idx[min(r80_idx, len(sorted_idx)-1)]])
    
    C = 5.0 * np.log10(r80 / r20)

    # Rotational Asymmetry A (180-degree rotation residual)
    I_180 = rotate(I, 180, reshape=False)
    diff_rot = np.abs(I - I_180)
    A = np.sum(diff_rot) / (2.0 * total_flux)

    # Smoothness / Clumpiness S (box-car smoothing residual)
    I_smooth = uniform_filter(I, size=5)
    diff_smooth = np.abs(I - I_smooth)
    S = np.sum(diff_smooth) / total_flux

    # Mean intensity and second-order moment of light M20
    mean_int = float(np.mean(arr))
    std_int = float(np.std(arr))
    gini_approx = float(np.sum(np.abs(np.subtract.outer(arr[::4, ::4].flat, arr[::4, ::4].flat))) / (2 * len(arr[::4, ::4].flat)**2 * mean_int + 1e-6))

    return {
        "Concentration": float(C),
        "Asymmetry": float(A),
        "Smoothness": float(S),
        "Mean_Intensity": mean_int,
        "Std_Intensity": std_int,
        "Gini_Approx": float(gini_approx),
        "Half_Light_Radius": float(r50)
    }


def run_baseline_experiment():
    catalog_path = os.path.join(DATA_DIR, "galaxy_catalog.csv")
    if not os.path.exists(catalog_path):
        print(f"Error: Catalog not found at {catalog_path}. Run dataset_builder.py first.")
        return

    df = pd.read_csv(catalog_path)
    print(f"Loaded {len(df)} records from {catalog_path}")

    print("Extracting CAS morphological parameters for all astronomical images...")
    features_list = []
    for _, row in df.iterrows():
        cas = compute_cas_features(row["file_path"])
        cas["class_idx"] = row["class_idx"]
        cas["split"] = row["split"]
        features_list.append(cas)

    feat_df = pd.DataFrame(features_list)
    feat_cols = ["Concentration", "Asymmetry", "Smoothness", "Mean_Intensity", "Std_Intensity", "Gini_Approx", "Half_Light_Radius"]

    # Splits
    train_df = feat_df[feat_df["split"] == "train"]
    val_df = feat_df[feat_df["split"] == "val"]
    test_df = feat_df[feat_df["split"] == "test"]

    X_train, y_train = train_df[feat_cols], train_df["class_idx"]
    X_val, y_val = val_df[feat_cols], val_df["class_idx"]
    X_test, y_test = test_df[feat_cols], test_df["class_idx"]

    # Combine train + val for standard fitting
    X_train_full = pd.concat([X_train, X_val])
    y_train_full = pd.concat([y_train, y_val])

    print("Fitting Baseline Classifier (Random Forest on CAS Features)...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    rf.fit(X_train_full, y_train_full)

    # Evaluate on held-out test set
    y_pred_test = rf.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred_test)
    test_f1 = f1_score(y_test, y_pred_test, average="macro")

    print("\n--- BASELINE RANDOM FOREST RESULTS (HELD-OUT TEST SET) ---")
    print(f"Accuracy: {test_acc:.4f} | Macro F1-Score: {test_f1:.4f}")
    report = classification_report(y_test, y_pred_test, target_names=["Elliptical", "Spiral", "Edge-on", "Merger_Anomaly"], output_dict=True)
    cm = confusion_matrix(y_test, y_pred_test).tolist()

    # Save baseline artifacts
    joblib.dump(rf, os.path.join(MODELS_DIR, "baseline_rf_cas.joblib"))
    results = {
        "model_type": "Classical_CAS_RandomForest",
        "features": feat_cols,
        "test_accuracy": round(float(test_acc), 4),
        "test_macro_f1": round(float(test_f1), 4),
        "classification_report": report,
        "confusion_matrix": cm,
        "feature_importances": {col: round(float(imp), 4) for col, imp in zip(feat_cols, rf.feature_importances_)}
    }

    with open(os.path.join(RESULTS_DIR, "baseline_cas_results.json"), "w") as f:
        json.dump(results, f, indent=4)

    print(f"Baseline results saved to {RESULTS_DIR}/baseline_cas_results.json")
    print("Feature Importances:", results["feature_importances"])


if __name__ == "__main__":
    run_baseline_experiment()
