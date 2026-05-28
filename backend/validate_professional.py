"""
Professional validation script for model evaluation.
Includes comprehensive metrics, confusion matrix analysis, and ROC curves.

Usage:
  python validate_professional.py --model-path models/best_model.pth
  python validate_professional.py --model-path models/best_model.pth --plot-roc
"""

import os
import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, roc_curve, auc, classification_report
)

from models.model_loader import get_model, get_device
from config import CLASS_NAMES, IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD
from utils.preprocessing import preprocess_image


class ModelEvaluator:
    """Professional model evaluation class."""
    
    def __init__(self, model_path=None, use_temperature_scaling=True, temperature=1.4):
        """Initialize evaluator."""
        self.device = get_device()
        self.model = get_model()
        self.use_temperature_scaling = use_temperature_scaling
        self.temperature = temperature
        self.results = {}
    
    def predict_batch(self, image_dir, class_label):
        """Predict on batch of images from directory."""
        predictions = []
        confidences = []
        filenames = []
        
        if not os.path.exists(image_dir):
            print(f"Warning: Directory not found: {image_dir}")
            return predictions, confidences, filenames
        
        image_files = [f for f in os.listdir(image_dir) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]
        
        print(f"Processing {len(image_files)} {class_label} images...")
        
        self.model.eval()
        with torch.no_grad():
            for filename in image_files:
                filepath = os.path.join(image_dir, filename)
                try:
                    # Preprocess image
                    tensor, pil_image = preprocess_image(filepath, detect_phone_image=True)
                    tensor = tensor.to(self.device)
                    
                    # Predict
                    outputs = self.model(tensor)
                    
                    # Temperature scaling
                    if self.use_temperature_scaling:
                        outputs = outputs / self.temperature
                    
                    probs = torch.softmax(outputs, dim=1)
                    confidence, pred_idx = torch.max(probs, dim=1)
                    
                    predictions.append(pred_idx.item())
                    confidences.append(confidence.item())
                    filenames.append(filename)
                    
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
        
        return predictions, confidences, filenames
    
    def evaluate_directory_pair(self, normal_dir, cancer_dir):
        """Evaluate on normal and cancer directories."""
        # Get normal predictions
        normal_preds, normal_conf, normal_files = self.predict_batch(normal_dir, "NORMAL")
        normal_targets = [0] * len(normal_preds)
        
        # Get cancer predictions
        cancer_preds, cancer_conf, cancer_files = self.predict_batch(
            cancer_dir, "CANCER"
        )
        cancer_targets = [1] * len(cancer_preds)
        
        # Combine
        all_preds = normal_preds + cancer_preds
        all_targets = normal_targets + cancer_targets
        all_conf = normal_conf + cancer_conf
        all_files = normal_files + cancer_files
        
        return all_preds, all_targets, all_conf, all_files
    
    def compute_metrics(self, predictions, targets, confidences=None):
        """Compute comprehensive evaluation metrics."""
        metrics = {}
        
        # Basic metrics
        metrics['accuracy'] = accuracy_score(targets, predictions)
        metrics['precision'] = precision_score(targets, predictions, zero_division=0)
        metrics['recall'] = recall_score(targets, predictions, zero_division=0)
        metrics['f1_score'] = f1_score(targets, predictions, zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(targets, predictions)
        metrics['confusion_matrix'] = cm.tolist()
        
        # Per-class metrics
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        metrics['true_negatives'] = int(tn)
        metrics['false_positives'] = int(fp)
        metrics['false_negatives'] = int(fn)
        metrics['true_positives'] = int(tp)
        
        # Sensitivity and specificity
        metrics['sensitivity'] = tp / (tp + fn) if (tp + fn) > 0 else 0
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        # Average confidence
        if confidences:
            metrics['avg_confidence'] = np.mean(confidences)
            metrics['min_confidence'] = np.min(confidences)
            metrics['max_confidence'] = np.max(confidences)
        
        # ROC-AUC if we have confidences and binary classification
        if confidences and len(set(targets)) == 2:
            try:
                # Use max probability as confidence score
                metrics['roc_auc'] = roc_auc_score(targets, confidences)
            except:
                metrics['roc_auc'] = None
        
        return metrics
    
    def print_report(self, metrics, predictions, targets):
        """Print comprehensive evaluation report."""
        print("\n" + "="*70)
        print("COMPREHENSIVE EVALUATION REPORT")
        print("="*70)
        
        print("\nрџ“Љ OVERALL METRICS:")
        print(f"  Accuracy:     {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
        print(f"  Precision:    {metrics['precision']:.4f}")
        print(f"  Recall:       {metrics['recall']:.4f}")
        print(f"  F1-Score:     {metrics['f1_score']:.4f}")
        if metrics.get('roc_auc'):
            print(f"  ROC-AUC:      {metrics['roc_auc']:.4f}")
        
        print("\nрџЏҐ MEDICAL METRICS:")
        print(f"  Sensitivity:  {metrics['sensitivity']:.4f} (recall for CANCER)")
        print(f"  Specificity:  {metrics['specificity']:.4f} (recall for NORMAL)")
        
        print("\nрџ“€ CONFUSION MATRIX:")
        cm = metrics['confusion_matrix']
        print(f"  Predicted    NORMAL  CANCER")
        print(f"  Actually NORMAL    {cm[0][0]:4d}  {cm[0][1]:4d}")
        print(f"  Actually PNEUM     {cm[1][0]:4d}  {cm[1][1]:4d}")
        
        print("\nвљ пёЏ  ERROR ANALYSIS:")
        print(f"  True Positives:   {metrics['true_positives']:4d} (correctly detected CANCER)")
        print(f"  True Negatives:   {metrics['true_negatives']:4d} (correctly identified NORMAL)")
        print(f"  False Positives:  {metrics['false_positives']:4d} (healthy diagnosed as sick) рџљЁ")
        print(f"  False Negatives:  {metrics['false_negatives']:4d} (missed CANCER) рџљЁ")
        
        if 'avg_confidence' in metrics:
            print(f"\nрџЋЇ CONFIDENCE LEVELS:")
            print(f"  Average: {metrics['avg_confidence']:.4f}")
            print(f"  Min:     {metrics['min_confidence']:.4f}")
            print(f"  Max:     {metrics['max_confidence']:.4f}")
        
        print("\n" + "="*70)


def plot_roc_curve(targets, confidences, save_path='logs/roc_curve.png'):
    """Plot ROC curve."""
    fpr, tpr, thresholds = roc_curve(targets, confidences)
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random classifier')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve - Lung Cancer Detection')
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    print(f"ROC curve saved to {save_path}")
    plt.close()


def plot_confusion_matrix(cm, save_path='logs/confusion_matrix.png'):
    """Plot confusion matrix."""
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, cmap='Blues', aspect='auto')
    
    # Labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(CLASS_NAMES)
    ax.set_yticklabels(CLASS_NAMES)
    ax.set_ylabel('True Label')
    ax.set_xlabel('Predicted Label')
    ax.set_title('Confusion Matrix - Lung Cancer Detection')
    
    # Add values
    for i in range(2):
        for j in range(2):
            text = ax.text(j, i, cm[i, j], ha="center", va="center", color="black", fontsize=14)
    
    plt.colorbar(im, ax=ax)
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    print(f"Confusion matrix saved to {save_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Professional model validation')
    parser.add_argument('--model-path', type=str, default='models/best_model.pth',
                       help='Path to model weights')
    parser.add_argument('--normal-dir', type=str, default=None,
                       help='Directory with NORMAL images')
    parser.add_argument('--cancer-dir', type=str, default=None,
                       help='Directory with CANCER images')
    parser.add_argument('--temperature', type=float, default=1.4,
                       help='Temperature scaling factor')
    parser.add_argument('--plot-roc', action='store_true', help='Plot ROC curve')
    parser.add_argument('--plot-cm', action='store_true', help='Plot confusion matrix')
    parser.add_argument('--save-json', action='store_true', help='Save metrics to JSON')
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = ModelEvaluator(
        model_path=args.model_path,
        use_temperature_scaling=True,
        temperature=args.temperature
    )
    
    if not args.normal_dir or not args.cancer_dir:
        print("Usage:")
        print("  python validate_professional.py \\")
        print("    --normal-dir ./data/oncology/val/NORMAL \\")
        print("    --cancer-dir ./data/oncology/val/CANCER")
        return
    
    # Evaluate
    predictions, targets, confidences, filenames = evaluator.evaluate_directory_pair(
        args.normal_dir, args.cancer_dir
    )
    
    # Compute metrics
    metrics = evaluator.compute_metrics(predictions, targets, confidences)
    
    # Print report
    evaluator.print_report(metrics, predictions, targets)
    
    # Plots
    if args.plot_roc:
        plot_roc_curve(targets, confidences)
    
    if args.plot_cm:
        plot_confusion_matrix(np.array(metrics['confusion_matrix']))
    
    # Save JSON
    if args.save_json:
        json_path = Path('logs') / f'metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(json_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\nMetrics saved to {json_path}")


if __name__ == '__main__':
    main()


