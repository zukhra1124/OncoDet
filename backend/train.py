"""Fine-tuning script for DenseNet121 on Lung Cancer Detection dataset.

Data produced by: python dataset_prepare.py  (from DCM + tashxis.docx)

Usage examples:
  python train.py --data-dir ../data/oncology --epochs 20 --batch-size 16
  python train.py --dry-run   # prints dataset sizes and model summary
"""

import os
import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from tqdm import tqdm
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

from models.densenet_model import OncologyNet


def get_transforms(image_size=224):
    # Enhanced augmentation to handle domain shift (phone images, different quality)
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),  # handle slight angle variations in phone photos
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),  # shift for robustness
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.5)),  # phone image blur variations
        transforms.ColorJitter(brightness=0.2, contrast=0.3, saturation=0.1),  # phone lighting/contrast
        transforms.RandomEqualize(p=0.3),  # histogram equalization for low-contrast phone photos
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    return train_transform, val_transform


def make_dataloaders(data_dir, batch_size, image_size):
    train_dir = os.path.join(data_dir, 'train')
    val_dir = os.path.join(data_dir, 'val')

    train_t, val_t = get_transforms(image_size)

    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        raise FileNotFoundError(f"Expected train/ and val/ under {data_dir}")

    train_ds = datasets.ImageFolder(train_dir, transform=train_t)
    val_ds = datasets.ImageFolder(val_dir, transform=val_t)

    num_workers = 0 if os.name == 'nt' else min(4, os.cpu_count() or 1)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, train_ds.classes


def train_one_epoch(model, device, loader, criterion, optimizer):
    model.train()
    losses = []
    preds = []
    targets = []

    for imgs, labels in tqdm(loader, desc='train', leave=False):
        imgs = imgs.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        losses.append(loss.item())
        preds.extend(torch.argmax(outputs, dim=1).cpu().tolist())
        targets.extend(labels.cpu().tolist())

    return sum(losses) / len(losses), preds, targets


def evaluate(model, device, loader, criterion):
    model.eval()
    losses = []
    preds = []
    targets = []

    with torch.no_grad():
        for imgs, labels in tqdm(loader, desc='eval', leave=False):
            imgs = imgs.to(device)
            labels = labels.to(device)

            outputs = model(imgs)
            loss = criterion(outputs, labels)

            losses.append(loss.item())
            preds.extend(torch.argmax(outputs, dim=1).cpu().tolist())
            targets.extend(labels.cpu().tolist())

    return sum(losses) / len(losses), preds, targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=str, default='../data/oncology', help='Path to dataset root')
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--image-size', type=int, default=224)
    parser.add_argument('--save-path', type=str, default='models/best_model.pth')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # quick checks
    data_dir = os.path.abspath(args.data_dir)
    print(f"Dataset root: {data_dir}")

    # if dry-run just print info and exit
    if args.dry_run:
        try:
            train_loader, val_loader, classes = make_dataloaders(data_dir, args.batch_size, args.image_size)
            print(f"Found classes: {classes}")
            print(f"Train samples: {len(train_loader.dataset)} | Val samples: {len(val_loader.dataset)}")
            print(f"Using DataLoader num_workers={train_loader.num_workers}")
        except Exception as e:
            print(f"Dry-run check failed: {e}")
        return

    # build dataloaders
    train_loader, val_loader, classes = make_dataloaders(data_dir, args.batch_size, args.image_size)

    # Compute class weights to handle imbalance (more weight on minority class)
    class_counts = torch.tensor([len(train_loader.dataset.classes), 0], dtype=torch.float)
    train_targets = []
    for _, labels in train_loader.dataset.imgs:
        train_targets.append(train_loader.dataset.class_to_idx[labels])
    
    class_weights = compute_class_weight(
        'balanced',
        classes=list(range(len(classes))),
        y=train_targets
    )
    class_weights = torch.tensor(class_weights, dtype=torch.float).to(device)
    print(f"Class weights (NORMAL, CANCER): {class_weights.cpu().tolist()}")

    # model
    model = OncologyNet(num_classes=len(classes), pretrained=True)
    model = model.to(device)

    # only train params that require_grad (classifier head)
    params_to_update = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(params_to_update, lr=args.lr)
    # Use weighted CrossEntropyLoss to penalize misclassification of minority class more
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    best_val_acc = 0.0
    save_path = Path(args.save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        print(f"Epoch {epoch}/{args.epochs}")
        train_loss, train_preds, train_targets = train_one_epoch(model, device, train_loader, criterion, optimizer)
        val_loss, val_preds, val_targets = evaluate(model, device, val_loader, criterion)

        val_acc = accuracy_score(val_targets, val_preds)
        val_precision = precision_score(val_targets, val_preds, average='binary', zero_division=0)
        val_recall = recall_score(val_targets, val_preds, average='binary', zero_division=0)
        val_f1 = f1_score(val_targets, val_preds, average='binary', zero_division=0)

        print(f" train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  val_acc={val_acc:.4f}  val_f1={val_f1:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), str(save_path))
            print(f"Saved best model to {save_path} (val_acc={best_val_acc:.4f})")

    print("Training complete.")


if __name__ == '__main__':
    main()
