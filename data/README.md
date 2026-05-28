# Dataset Info — OncoDet

## Lung Cancer Detection Dataset (Local Clinical Data)

**Source:** Republican Specialized Scientific-Practical Medical Center of Oncology
and Radiology (RSSPMCOiR), Tashkent, Uzbekistan

**Collection period:** 2025–2026
**Format:** DICOM (`.dcm`) images + radiologist reports in `tashxis.docx`

---

### How the dataset is prepared

Raw data lives in `dcm/` (131 DICOM files, 105 unique patient IDs) and
diagnoses are in `tashxis.docx` (Uzbek + Russian radiologist reports).

Run the preparation script from the project root:
```bash
python dataset_prepare.py
```

This will:
1. Parse `tashxis.docx` and classify each patient as **CANCER** or **NORMAL**
   based on explicit radiologist labels ("rak", mts, "образование", etc.)
2. Convert every matched DICOM file to a normalised 8-bit JPEG
3. Create a stratified train/val/test split (75 / 12.5 / 12.5 %)
4. Write `data/oncology/labels.csv` with full provenance

---

### Output structure
```
data/oncology/
├── train/
│   ├── CANCER/    (~59 images)
│   └── NORMAL/    (~36 images)
├── val/
│   ├── CANCER/    (~9 images)
│   └── NORMAL/    (~6 images)
├── test/
│   ├── CANCER/    (~11 images)
│   └── NORMAL/    (~7 images)
└── labels.csv     (patient_id, dcm_filename, split, label)
```

Total: **128 images** (79 CANCER, 49 NORMAL)

---

### Label definitions

| Label  | Meaning |
|--------|---------|
| CANCER | Radiologist confirmed or strongly suspected lung cancer / metastases / malignant mass |
| NORMAL | No pathological changes found in the lungs |

**Excluded:** 2 DCM files had unreadable pixel data; ~4 images had ambiguous or missing diagnoses and were excluded from training.

---

### Without training

The app works without trained weights — it uses ImageNet-pretrained DenseNet121 by default.
Predictions will not be clinically meaningful without fine-tuning, but all features
(Grad-CAM, federated learning, OOD detection, UI) work for demonstration.

### Supported upload formats
PNG, JPEG, BMP, TIFF — any size, grayscale or RGB (converted to RGB internally)
