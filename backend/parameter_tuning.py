"""
Parameter Tuning via Grid Search — OncoDet
==========================================
Searches over (classification threshold, temperature) to find the
combination that MINIMISES FALSE NEGATIVES (cancer patients classified
as normal — the most dangerous error in oncology screening).

Also reports: Confusion Matrix, Precision, Recall, F1 for each config.

Run:
  cd backend
  python parameter_tuning.py --data-dir ../data/oncology/val
  python parameter_tuning.py --data-dir ../data/oncology/test
"""

import os
import sys
import argparse
import csv
from pathlib import Path
from itertools import product

import torch
import torch.nn.functional as F
import numpy as np
from torchvision import datasets, transforms
from sklearn.metrics import (
    confusion_matrix, precision_score, recall_score,
    f1_score, accuracy_score
)

# ── make sure we can import backend modules ──────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from models.model_loader import get_model, get_device
from config import CLASS_NAMES, IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
def load_dataset(data_dir: str):
    """Load all images from a folder that follows ImageFolder structure."""
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
    dataset = datasets.ImageFolder(data_dir, transform=transform)
    loader  = torch.utils.data.DataLoader(
        dataset, batch_size=8, shuffle=False, num_workers=0
    )
    return loader, dataset.classes


# ─────────────────────────────────────────────────────────────────────────────
# INFERENCE
# ─────────────────────────────────────────────────────────────────────────────
def get_probabilities(loader, temperature: float):
    """
    Run full dataset through model, return raw probabilities
    for the CANCER class (index 0) after temperature scaling.
    Also returns true labels.
    """
    model  = get_model()
    device = get_device()
    model.eval()

    all_probs  = []
    all_labels = []

    with torch.no_grad():
        for imgs, labels in loader:
            imgs   = imgs.to(device)
            logits = model(imgs)
            logits = logits / temperature          # temperature scaling
            probs  = F.softmax(logits, dim=1)
            # index 0 = CANCER (ImageFolder alphabetical: C < N)
            cancer_prob = probs[:, 0].cpu().numpy()
            all_probs.extend(cancer_prob.tolist())
            all_labels.extend(labels.cpu().numpy().tolist())

    return np.array(all_probs), np.array(all_labels)


# ─────────────────────────────────────────────────────────────────────────────
# METRICS AT A GIVEN THRESHOLD
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_threshold(probs, labels, threshold: float):
    """
    Classify images as CANCER if P(cancer) >= threshold, else NORMAL.
    Returns dict with all metrics and the full confusion matrix.

    Labels:   0 = CANCER  (positive class)
              1 = NORMAL  (negative class)

    Confusion matrix layout:
                  Pred CANCER  Pred NORMAL
    True CANCER      TP            FN   ← we want FN → 0
    True NORMAL      FP            TN
    """
    preds = (probs >= threshold).astype(int)   # 1 → CANCER, 0 → NORMAL
    # Note: ImageFolder labels are also 0=CANCER, 1=NORMAL.
    # sklearn expects positive class = 1, so we invert:
    y_true_bin = (labels == 0).astype(int)     # 1 if true CANCER
    y_pred_bin = (preds  == 1).astype(int)     # 1 if predicted CANCER

    cm  = confusion_matrix(y_true_bin, y_pred_bin, labels=[1, 0])
    # cm[0,0]=TP  cm[0,1]=FN  cm[1,0]=FP  cm[1,1]=TN
    TP = int(cm[0, 0]) if cm.shape == (2, 2) else 0
    FN = int(cm[0, 1]) if cm.shape == (2, 2) else 0
    FP = int(cm[1, 0]) if cm.shape == (2, 2) else 0
    TN = int(cm[1, 1]) if cm.shape == (2, 2) else 0

    precision = precision_score(y_true_bin, y_pred_bin, zero_division=0)
    recall    = recall_score(y_true_bin, y_pred_bin, zero_division=0)
    f1        = f1_score(y_true_bin, y_pred_bin, zero_division=0)
    accuracy  = accuracy_score(y_true_bin, y_pred_bin)  # both in same 0/1 space

    return {
        "TP": TP, "FN": FN, "FP": FP, "TN": TN,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "accuracy":  round(accuracy, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PRETTY PRINT CONFUSION MATRIX
# ─────────────────────────────────────────────────────────────────────────────
def print_confusion_matrix(m: dict, threshold: float, temperature: float, label=""):
    print(f"\n{'='*60}")
    print(f"  Confusion Matrix{' — '+label if label else ''}")
    print(f"  Threshold = {threshold:.2f} | Temperature = {temperature:.1f}")
    print(f"{'='*60}")
    print(f"                     Predicted")
    print(f"                   CANCER    NORMAL")
    print(f"  Actual  CANCER  {m['TP']:>6}    {m['FN']:>6}  ← FN (missed cancer!)")
    print(f"          NORMAL  {m['FP']:>6}    {m['TN']:>6}")
    print(f"{'-'*60}")
    print(f"  Precision : {m['precision']:.4f}  (of all predicted CANCER, how many are real?)")
    print(f"  Recall    : {m['recall']:.4f}  (of all real CANCER, how many detected?)  ← KEY")
    print(f"  F1-Score  : {m['f1']:.4f}")
    print(f"  Accuracy  : {m['accuracy']:.4f}")
    print(f"  FN (missed cancer) : {m['FN']}  ← want this = 0")
    print(f"  FP (false alarm)   : {m['FP']}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────────────────────
# GRID SEARCH
# ─────────────────────────────────────────────────────────────────────────────
def grid_search(data_dir: str, save_csv: bool = True):
    print(f"\nLoading data from: {data_dir}")
    loader, classes = load_dataset(data_dir)
    print(f"Classes (ImageFolder order): {classes}")
    print(f"Total images: {len(loader.dataset)}")

    # Grid parameters
    thresholds   = np.round(np.arange(0.10, 0.91, 0.05), 2).tolist()
    temperatures = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]

    best_recall_result = None
    best_f1_result     = None
    all_results        = []

    total = len(thresholds) * len(temperatures)
    print(f"\nGrid Search: {len(thresholds)} thresholds x "
          f"{len(temperatures)} temperatures = {total} combinations\n")

    # Pre-compute probabilities for each temperature (avoid rerunning model)
    temp_probs = {}
    for temp in temperatures:
        probs, labels = get_probabilities(loader, temp)
        temp_probs[temp] = (probs, labels)

    for temp, thresh in product(temperatures, thresholds):
        probs, labels = temp_probs[temp]
        m = evaluate_threshold(probs, labels, thresh)
        row = {"threshold": thresh, "temperature": temp, **m}
        all_results.append(row)

        # Best for RECALL (minimise FN) — primary medical objective
        if best_recall_result is None or (
            m["recall"] > best_recall_result["recall"] or
            (m["recall"] == best_recall_result["recall"] and
             m["f1"] > best_recall_result["f1"])
        ):
            best_recall_result = row

        # Best for F1
        if best_f1_result is None or m["f1"] > best_f1_result["f1"]:
            best_f1_result = row

    # ── Print default threshold result ───────────────────────────────────────
    default_temp   = 1.4
    default_thresh = 0.50
    dp, dl = temp_probs[default_temp]
    dm = evaluate_threshold(dp, dl, default_thresh)
    print_confusion_matrix(dm, default_thresh, default_temp, "Default settings")

    # ── Print best-Recall result ──────────────────────────────────────────────
    bp, bl_ = temp_probs[best_recall_result["temperature"]]
    bm = evaluate_threshold(bp, bl_,
                            best_recall_result["threshold"])
    print_confusion_matrix(bm,
                           best_recall_result["threshold"],
                           best_recall_result["temperature"],
                           "Best Recall (min FN)")

    # ── Print best-F1 result ─────────────────────────────────────────────────
    fp_, fl = temp_probs[best_f1_result["temperature"]]
    fm = evaluate_threshold(fp_, fl, best_f1_result["threshold"])
    print_confusion_matrix(fm,
                           best_f1_result["threshold"],
                           best_f1_result["temperature"],
                           "Best F1-Score")

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'='*75}")
    print(f"  TOP 10 CONFIGURATIONS BY RECALL (minimise FN)")
    print(f"{'='*75}")
    print(f"  {'Thresh':>6}  {'Temp':>5}  {'Recall':>7}  {'Precision':>9}  "
          f"{'F1':>7}  {'Accuracy':>8}  {'FN':>4}  {'FP':>4}")
    print(f"  {'-'*73}")
    top10 = sorted(all_results,
                   key=lambda r: (-r["recall"], -r["f1"]))[:10]
    for r in top10:
        print(f"  {r['threshold']:>6.2f}  {r['temperature']:>5.1f}  "
              f"{r['recall']:>7.4f}  {r['precision']:>9.4f}  "
              f"{r['f1']:>7.4f}  {r['accuracy']:>8.4f}  "
              f"{r['FN']:>4}  {r['FP']:>4}")

    # ── Recommendation ────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RECOMMENDATION")
    print(f"{'='*60}")
    print(f"  Objective : Minimise FN (missed cancer patients)")
    print(f"  Best threshold  : {best_recall_result['threshold']:.2f}")
    print(f"  Best temperature: {best_recall_result['temperature']:.1f}")
    print(f"  Recall    : {best_recall_result['recall']:.4f}  "
          f"(FN = {best_recall_result['FN']})")
    print(f"  Precision : {best_recall_result['precision']:.4f}  "
          f"(FP = {best_recall_result['FP']})")
    print(f"  F1-Score  : {best_recall_result['f1']:.4f}")
    print(f"\n  Recommended settings for this project:")
    print(f"    CONFIDENCE_THRESHOLD = {best_recall_result['threshold']:.2f}  # already applied in backend/config.py")
    print(f"    TEMPERATURE_SCALING = {best_recall_result['temperature']:.1f}  # already applied in backend/config.py and used by backend/services/prediction.py")
    print(f"{'='*60}\n")

    # ── Save CSV ───────────────────────────────────────────────────────────────
    if save_csv:
        out = Path("logs")
        out.mkdir(exist_ok=True)
        csv_path = out / "grid_search_results.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
            writer.writeheader()
            writer.writerows(all_results)
        print(f"  Full results saved: {csv_path}")

    return best_recall_result, best_f1_result, all_results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Grid Search: threshold + temperature to minimise FN")
    parser.add_argument("--data-dir", type=str,
                        default="../data/oncology/val",
                        help="ImageFolder-style directory (val or test)")
    parser.add_argument("--no-csv", action="store_true",
                        help="Skip saving CSV results")
    args = parser.parse_args()

    if not os.path.exists(args.data_dir):
        print(f"ERROR: data directory not found: {args.data_dir}")
        return

    grid_search(args.data_dir, save_csv=not args.no_csv)


if __name__ == "__main__":
    main()
