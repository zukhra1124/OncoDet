Training instructions for fine-tuning DenseNet121 on Chest X-Ray dataset.

Prerequisites
- Python environment with backend/requirements.txt installed

Quick dry-run (checks dataset structure):
```bash
cd backend
python train.py --dry-run --data-dir ../data/chest_xray
```

Run full training (example):
```bash
cd backend
python train.py --data-dir ../data/chest_xray --epochs 20 --batch-size 32 --lr 1e-3
```

Outputs
- Trained weights saved to `backend/models/best_model.pth` by default.
- Use `--save-path` to change the location.

Notes
- If you have a GPU, PyTorch will use it automatically.
- Ensure `data/chest_xray/train` and `data/chest_xray/val` exist and follow ImageFolder layout.
