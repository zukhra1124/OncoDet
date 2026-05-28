"""
Professional Fine-tuning Script for DenseNet121 on Chest X-Ray Classification.

Features:
- Focal Loss for imbalanced classification
- Early stopping to prevent overfitting  
- Learning rate scheduling for optimal convergence
- Advanced augmentation for domain robustness
- Comprehensive metrics tracking and logging
- Confusion matrix and per-class metrics

Usage:
  python train_professional.py --data-dir ../data/oncology --epochs 50
  python train_professional.py --loss focal --patience 7 --scheduler cosine
  python train_professional.py --dry-run
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from tqdm import tqdm
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score,
    confusion_matrix, roc_auc_score, roc_curve
)
from sklearn.utils.class_weight import compute_class_weight

from models.densenet_model import OncologyNet
from losses import FocalLoss, WeightedFocalLoss


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logger(name='training'):
    """Configure professional logging to file and console."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'train_{timestamp}.log'
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # Remove existing handlers
    
    # File handler (detailed)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler (summary)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger, log_file

logger, log_file = setup_logger('training')


# ============================================================================
# DATA LOADING
# ============================================================================

def get_augmented_transforms(image_size=224):
    """Advanced augmentation for robustness to domain shift."""
    
    train_transform = transforms.Compose([
        # Spatial augmentation
        transforms.RandomResizedCrop(image_size, scale=(0.75, 1.0), ratio=(0.8, 1.2)),
        transforms.RandomRotation(degrees=20),
        transforms.RandomAffine(degrees=0, translate=(0.15, 0.15), shear=10),
        transforms.RandomHorizontalFlip(p=0.5),
        
        # Intensity augmentation (for phone camera variations)
        transforms.ColorJitter(brightness=0.3, contrast=0.4, saturation=0.1),
        transforms.GaussianBlur(kernel_size=5, sigma=(0.1, 1.0)),
        transforms.RandomEqualize(p=0.3),
        transforms.RandomAutocontrast(p=0.3),
        
        # Normalization
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    return train_transform, val_transform


def load_data(data_dir, batch_size, image_size=224, num_workers=4):
    """Load train and validation datasets with augmentation."""
    train_dir = os.path.join(data_dir, 'train')
    val_dir = os.path.join(data_dir, 'val')
    
    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        raise FileNotFoundError(f"Expected train/ and val/ under {data_dir}")
    
    train_t, val_t = get_augmented_transforms(image_size)
    
    train_ds = datasets.ImageFolder(train_dir, transform=train_t)
    val_ds = datasets.ImageFolder(val_dir, transform=val_t)
    
    # Adjust workers for Windows
    num_workers = 0 if os.name == 'nt' else min(num_workers, os.cpu_count() or 1)
    
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True
    )
    
    return train_loader, val_loader, train_ds.classes


# ============================================================================
# EARLY STOPPING
# ============================================================================

class EarlyStopping:
    """Stop training if validation metric doesn't improve."""
    
    def __init__(self, patience=5, min_delta=0.001, verbose=True):
        """
        Args:
            patience: Number of epochs with no improvement after which to stop
            min_delta: Minimum change to qualify as improvement
            verbose: Print updates
        """
        self.patience = patience
        self.min_delta = min_delta
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
    
    def __call__(self, val_metric):
        """Call with validation metric (higher is better)."""
        if self.best_score is None:
            self.best_score = val_metric
        elif val_metric > self.best_score + self.min_delta:
            self.best_score = val_metric
            self.counter = 0
            if self.verbose:
                logger.info(f"Early stopping: validation metric improved to {val_metric:.4f}")
        else:
            self.counter += 1
            if self.verbose:
                logger.info(
                    f"Early stopping: no improvement for {self.counter}/{self.patience} epochs"
                )
            if self.counter >= self.patience:
                self.early_stop = True
                if self.verbose:
                    logger.warning("Early stopping triggered")


# ============================================================================
# TRAINING LOOP
# ============================================================================

def train_epoch(model, device, loader, criterion, optimizer, scaler=None):
    """Train for one epoch."""
    model.train()
    losses = []
    preds = []
    targets = []
    
    pbar = tqdm(loader, desc='Training', leave=False)
    for imgs, labels in pbar:
        imgs = imgs.to(device)
        labels = labels.to(device)
        
        optimizer.zero_grad()
        
        # Mixed precision if scaler provided
        if scaler is not None:
            with torch.cuda.amp.autocast():
                outputs = model(imgs)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        
        losses.append(loss.item())
        preds.extend(torch.argmax(outputs, dim=1).cpu().tolist())
        targets.extend(labels.cpu().tolist())
        
        pbar.set_postfix({'loss': f'{loss.item():.4f}'})
    
    return sum(losses) / len(losses), preds, targets


def validate(model, device, loader, criterion):
    """Validate model."""
    model.eval()
    losses = []
    preds = []
    targets = []
    
    pbar = tqdm(loader, desc='Validating', leave=False)
    with torch.no_grad():
        for imgs, labels in pbar:
            imgs = imgs.to(device)
            labels = labels.to(device)
            
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            
            losses.append(loss.item())
            preds.extend(torch.argmax(outputs, dim=1).cpu().tolist())
            targets.extend(labels.cpu().tolist())
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
    
    return sum(losses) / len(losses), preds, targets


def compute_metrics(preds, targets):
    """Compute comprehensive metrics."""
    accuracy = accuracy_score(targets, preds)
    precision = precision_score(targets, preds, zero_division=0)
    recall = recall_score(targets, preds, zero_division=0)
    f1 = f1_score(targets, preds, zero_division=0)
    cm = confusion_matrix(targets, preds)
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'confusion_matrix': cm
    }


# ============================================================================
# MAIN TRAINING FUNCTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Professional training for lung cancer detection')
    parser.add_argument('--data-dir', type=str, default='../data/oncology', help='Dataset path')
    parser.add_argument('--epochs', type=int, default=50, help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-3, help='Learning rate')
    parser.add_argument('--image-size', type=int, default=224, help='Image size')
    parser.add_argument('--save-path', type=str, default='models/best_model.pth', help='Save path')
    parser.add_argument('--loss', type=str, default='focal', choices=['ce', 'focal', 'weighted_focal'],
                       help='Loss function')
    parser.add_argument('--patience', type=int, default=7, help='Early stopping patience')
    parser.add_argument('--scheduler', type=str, default='cosine', 
                       choices=['constant', 'cosine', 'linear', 'step'],
                       help='LR scheduler')
    parser.add_argument('--dry-run', action='store_true', help='Print dataset info and exit')
    parser.add_argument('--mixed-precision', action='store_true', help='Use mixed precision training')
    args = parser.parse_args()
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Data loading
    data_dir = os.path.abspath(args.data_dir)
    logger.info(f"Loading data from: {data_dir}")
    
    if args.dry_run:
        try:
            train_loader, val_loader, classes = load_data(data_dir, args.batch_size, args.image_size)
            logger.info(f"Classes: {classes}")
            logger.info(f"Train samples: {len(train_loader.dataset)}")
            logger.info(f"Val samples: {len(val_loader.dataset)}")
            logger.info(f"Using num_workers: {train_loader.num_workers}")
            return
        except Exception as e:
            logger.error(f"Dry-run failed: {e}")
            return
    
    train_loader, val_loader, classes = load_data(data_dir, args.batch_size, args.image_size)
    logger.info(f"Classes: {classes}")
    logger.info(f"Train samples: {len(train_loader.dataset)}")
    logger.info(f"Val samples: {len(val_loader.dataset)}")
    
    # Model
    model = OncologyNet(num_classes=len(classes), pretrained=True)
    model = model.to(device)
    logger.info(f"Model loaded: {type(model).__name__}")
    
    # Optimizer
    params_to_update = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(params_to_update, lr=args.lr, weight_decay=1e-4)
    logger.info(f"Optimizer: Adam (lr={args.lr}, weight_decay=1e-4)")
    
    # Loss function
    import numpy as np
    train_targets = [label for _, label in train_loader.dataset.imgs]
    class_weights = compute_class_weight(
        'balanced', classes=np.array(list(range(len(classes)))), y=train_targets
    )
    class_weights = torch.tensor(class_weights, dtype=torch.float32).to(device)
    logger.info(f"Class weights: {class_weights.cpu().tolist()}")
    
    if args.loss == 'focal':
        criterion = FocalLoss(alpha=0.25, gamma=2.0)
        logger.info("Loss: Focal Loss (alpha=0.25, gamma=2.0)")
    elif args.loss == 'weighted_focal':
        criterion = WeightedFocalLoss(class_weights=class_weights.cpu().tolist(), gamma=2.0)
        logger.info("Loss: Weighted Focal Loss")
    else:
        criterion = nn.CrossEntropyLoss(weight=class_weights)
        logger.info("Loss: Weighted CrossEntropy")
    
    # Learning rate scheduler
    if args.scheduler == 'cosine':
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
        logger.info("LR Scheduler: Cosine Annealing")
    elif args.scheduler == 'linear':
        scheduler = torch.optim.lr_scheduler.LinearLR(optimizer, total_iters=args.epochs)
        logger.info("LR Scheduler: Linear")
    elif args.scheduler == 'step':
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=args.epochs//3, gamma=0.5)
        logger.info("LR Scheduler: Step")
    else:
        scheduler = None
        logger.info("LR Scheduler: None")
    
    # Mixed precision
    scaler = torch.cuda.amp.GradScaler() if args.mixed_precision else None
    if scaler:
        logger.info("Using mixed precision training")
    
    # Early stopping
    early_stopping = EarlyStopping(patience=args.patience, verbose=True)
    
    # Training loop
    save_path = Path(args.save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    history = {
        'epoch': [],
        'train_loss': [],
        'val_loss': [],
        'train_acc': [],
        'val_acc': [],
        'train_f1': [],
        'val_f1': []
    }
    
    logger.info("="*70)
    logger.info("STARTING TRAINING")
    logger.info("="*70)
    
    best_val_f1 = 0.0
    
    for epoch in range(1, args.epochs + 1):
        logger.info(f"Epoch {epoch}/{args.epochs}")
        
        # Train
        train_loss, train_preds, train_targets = train_epoch(
            model, device, train_loader, criterion, optimizer, scaler
        )
        train_metrics = compute_metrics(train_preds, train_targets)
        
        # Validate
        val_loss, val_preds, val_targets = validate(model, device, val_loader, criterion)
        val_metrics = compute_metrics(val_preds, val_targets)
        
        # Log metrics
        history['epoch'].append(epoch)
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_acc'].append(train_metrics['accuracy'])
        history['val_acc'].append(val_metrics['accuracy'])
        history['train_f1'].append(train_metrics['f1'])
        history['val_f1'].append(val_metrics['f1'])
        
        # Logging
        log_msg = (
            f"  Train: loss={train_loss:.4f} acc={train_metrics['accuracy']:.4f} "
            f"f1={train_metrics['f1']:.4f}\n"
            f"  Val:   loss={val_loss:.4f} acc={val_metrics['accuracy']:.4f} "
            f"f1={val_metrics['f1']:.4f}"
        )
        logger.info(log_msg)
        
        # LR scheduler step
        if scheduler is not None:
            scheduler.step()
            current_lr = optimizer.param_groups[0]['lr']
            logger.info(f"  Current LR: {current_lr:.6f}")
        
        # Save best model
        if val_metrics['f1'] > best_val_f1:
            best_val_f1 = val_metrics['f1']
            torch.save(model.state_dict(), str(save_path))
            logger.info(f"вњ“ Saved best model (F1={best_val_f1:.4f}) to {save_path}")
        
        # Early stopping
        early_stopping(val_metrics['f1'])
        if early_stopping.early_stop:
            logger.warning(f"Early stopping at epoch {epoch}")
            break
    
    # Save training history
    history_path = Path('logs') / f'history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)
    logger.info(f"Training history saved to {history_path}")
    
    logger.info("="*70)
    logger.info(f"TRAINING COMPLETE - Best F1: {best_val_f1:.4f}")
    logger.info("="*70)
    logger.info(f"Full logs: {log_file}")


if __name__ == '__main__':
    main()

