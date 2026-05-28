# OncoDet — AI-Based Lung Cancer Detection System

## Project Overview
OncoDet is an AI-powered clinical decision-support system for detecting lung cancer
from chest X-ray images. The system was developed as a diploma project and is trained
on real clinical data collected from the Republican Specialized Scientific-Practical
Medical Center of Oncology and Radiology (RSSPMCOiR), Tashkent, Uzbekistan.

## What does the system do?
1. A clinician uploads a chest X-ray (JPEG, PNG, or exported from DICOM).
2. An OOD validator confirms the image is a valid chest X-ray.
3. The image is preprocessed and fed to a DenseNet121 model trained on local oncology data.
4. The model outputs **NORMAL** or **CANCER** with a confidence score.
5. Grad-CAM highlights the tumour regions that drove the prediction.
6. Low-confidence cases are automatically flagged for mandatory physician review.

## Why is this system important?
- Uzbekistan has a severe shortage of radiologists (1.2 per 100,000 population).
- Early-stage lung cancer detected on X-ray has significantly better treatment outcomes.
- OncoDet acts as a screening support tool, prioritising urgent cases for specialist review.
- The federated learning module demonstrates privacy-preserving training across hospital nodes.

## Dataset
- **Source:** RSSPMCOiR (Republican Specialized Scientific-Practical Medical Center of Oncology and Radiology), Tashkent
- **Format:** DICOM (`.dcm`) converted to JPEG by `dataset_prepare.py`
- **Labels:** Extracted from `tashxis.docx` — radiologist reports with conclusions
- **Classes:** NORMAL / CANCER
- **Total images:** 128 (79 CANCER, 49 NORMAL after conversion)
- **Splits:** 75% train / 12.5% val / 12.5% test (stratified)

> **To prepare the dataset from raw DCM files:**
> ```bash
> python dataset_prepare.py
> ```
> This reads `dcm/` + `tashxis.docx`, converts DICOM → JPEG, and creates `data/oncology/`.

## Technology Stack

### Backend
- Python 3.11
- Flask 3.0 + Flask-CORS
- PyTorch 2.0 + Torchvision
- pydicom (DICOM reading)
- scikit-learn
- PIL / Pillow + OpenCV

### Frontend
- React 18 + Vite
- Tailwind CSS
- Axios
- React Router
- Framer Motion
- lucide-react

## Project Architecture
```
OncoDet/
├── dcm/                      # Raw DICOM files from RSSPMCOiR
├── tashxis.docx              # Radiologist diagnoses (Uzbek + Russian)
├── dataset_prepare.py        # DCM → JPEG + label extraction
├── data/
│   └── oncology/
│       ├── train/CANCER/     # Training images
│       ├── train/NORMAL/
│       ├── val/CANCER/
│       ├── val/NORMAL/
│       ├── test/CANCER/
│       ├── test/NORMAL/
│       └── labels.csv        # Full label mapping
├── backend/
│   ├── app.py                # Flask application factory
│   ├── config.py             # All constants (CLASS_NAMES = [NORMAL, CANCER])
│   ├── train.py              # Basic fine-tuning script
│   ├── train_professional.py # Advanced training (Focal Loss, Early Stopping)
│   ├── losses.py             # Focal Loss, Weighted Focal Loss
│   ├── models/
│   │   ├── densenet_model.py # OncologyNet (DenseNet121 + custom head)
│   │   └── model_loader.py   # Cached model loading
│   ├── services/
│   │   ├── prediction.py     # Inference + temperature scaling
│   │   ├── gradcam.py        # Grad-CAM heatmap generation
│   │   ├── chest_xray_validator.py  # OOD detection
│   │   └── federated.py      # FedAvg simulation
│   └── routes/
│       ├── predict_routes.py # POST /api/predict, /api/upload
│       ├── gradcam_routes.py # POST /api/gradcam
│       ├── federated_routes.py # POST /api/federated-train
│       └── stats_routes.py   # GET /api/model-stats
└── frontend/
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx
        │   ├── UploadPage.jsx
        │   ├── ResultsPage.jsx
        │   ├── FederatedPage.jsx
        │   └── PerformancePage.jsx
        └── services/api.js
```

## Model Performance
- Architecture: DenseNet121 (ImageNet pre-trained, custom 2-class head)
- Classes: `["NORMAL", "CANCER"]`
- Training: Focal Loss (α=0.25, γ=2.0) + Adam + Cosine Annealing + Early Stopping
- Best validation accuracy: see `backend/logs/` after training

## Training
```bash
# Standard training
cd backend
python train.py --data-dir ../data/oncology --epochs 30 --batch-size 16

# Professional training (Focal Loss + Early Stopping + logging)
python train_professional.py \
    --data-dir ../data/oncology \
    --loss focal \
    --scheduler cosine \
    --patience 7 \
    --epochs 50
```

## API Endpoints
| Method | Endpoint               | Description                        |
|--------|------------------------|------------------------------------|
| POST   | /api/predict           | Upload + classify + Grad-CAM       |
| POST   | /api/upload            | Save image only                    |
| POST   | /api/gradcam           | Generate Grad-CAM for saved image  |
| POST   | /api/federated-train   | Run federated learning simulation  |
| GET    | /api/model-stats       | Return stored performance metrics  |
| GET    | /api/health            | Health check                       |

## Quick Start

### Option 1: One-click (Windows)
```
double-click start_all.bat
```

### Option 2: Manual
```bash
# Terminal 1 — Backend (port 5001)
cd backend
python app.py

# Terminal 2 — Frontend (port 5175)
cd frontend
npm run dev
```
Open: http://localhost:5175

### Option 3: Docker
```bash
docker compose up --build
```

## Dependencies Setup
```bash
pip install -r backend/requirements.txt
cd frontend && npm install
```

---

© 2024 OncoDet — Lung Cancer Detection System.
Developed at Westminster International University in Tashkent.
Clinical data: RSSPMCOiR, Tashkent, Uzbekistan.
