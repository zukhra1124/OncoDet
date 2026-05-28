#!/usr/bin/env python3
"""
Dataset Preparation Script — OncoDet (Lung Cancer Detection)
============================================================
Reads tashxis.docx (diagnoses from RSSPMCOiR) + DCM folder,
classifies each patient as CANCER or NORMAL,
converts DICOM to JPEG, and builds the dataset folder structure:

  data/oncology/
    train/
      CANCER/
      NORMAL/
    val/
      CANCER/
      NORMAL/
    test/
      CANCER/
      NORMAL/

Run: python dataset_prepare.py
"""

import os
import re
import csv
import shutil
import random
from pathlib import Path

import numpy as np
import pydicom
from PIL import Image
from docx import Document

# ─────────────────────────────────────────────────────────────────────────────
DOCX_PATH   = "tashxis.docx"
DCM_FOLDER  = "dcm"
OUT_ROOT    = Path("data/oncology")
RANDOM_SEED = 42
TRAIN_RATIO = 0.75
VAL_RATIO   = 0.125   # test gets the rest (~0.125)

CANCER_KEYWORDS = [
    "rak", "рак", "mts", "мтс", "метастаз", "канцер", "карцином",
    "диссеминац", "disseminac", "саркома", "sarkoma", "образован",
    "оброзован", "malign", "onkolog", "онколог", "cancer",
    "cr ", "susp.cr", "carcinoma", "лимфом", "лимфоматоз",
    "канцероматоз", "карциноматоз",
]
NORMAL_KEYWORDS = [
    "патологических изменений в легких нет",
    "патологических изменений не визуализируются",
    "не визуализируются",
    "patologik o'zgarishlar aniqlanmadi",
    "patologik o`zgarishlar aniqlanmadi",
    "patologik ozgarishlar aniqlanmadi",
]

random.seed(RANDOM_SEED)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Parse tashxis.docx
# ─────────────────────────────────────────────────────────────────────────────
def parse_diagnoses(docx_path: str) -> dict:
    """
    Returns {patient_id: 'CANCER' | 'NORMAL' | 'UNKNOWN'}
    """
    doc = Document(docx_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    label_map = {}   # id → label

    # ── Pass 1: extract inline "ID rak" / "ID RAK" patterns ──────────────────
    # These are lines like "29259 Rak", "31503 rak (1)", "20612 RAK", etc.
    inline_pattern = re.compile(
        r'^(\d+)\s+(rak|RAK|Rak|rак|РАК|рак)',
        re.IGNORECASE
    )
    for line in paragraphs:
        m = inline_pattern.match(line)
        if m:
            label_map[m.group(1)] = "CANCER"

    # ── Pass 2: block-based classification ────────────────────────────────────
    # Each block starts with a line that is purely a number (patient ID).
    current_id   = None
    current_text = []

    def classify_block(pid, lines):
        full_text = " ".join(lines).lower()
        for kw in CANCER_KEYWORDS:
            if kw.lower() in full_text:
                return "CANCER"
        for kw in NORMAL_KEYWORDS:
            if kw.lower() in full_text:
                return "NORMAL"
        return "UNKNOWN"

    for line in paragraphs:
        if re.match(r'^\d+$', line.strip()):
            # save previous block
            if current_id and current_id not in label_map:
                label_map[current_id] = classify_block(current_id, current_text)
            current_id   = line.strip()
            current_text = []
        elif current_id:
            current_text.append(line)

    # final block
    if current_id and current_id not in label_map:
        label_map[current_id] = classify_block(current_id, current_text)

    return label_map


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Map DCM files to labels
# ─────────────────────────────────────────────────────────────────────────────
def extract_id_from_filename(fname: str) -> str | None:
    """BAXRXXXX_ZULXXXXX_10495.dcm  →  '10495'"""
    m = re.search(r'_(\d+)(?:-\d+)?\.dcm$', fname, re.IGNORECASE)
    return m.group(1) if m else None


def map_dcm_to_labels(dcm_folder: str, label_map: dict):
    """
    Returns list of (dcm_path, patient_id, label)
    Only includes files where label is CANCER or NORMAL.
    """
    records = []
    dcm_path = Path(dcm_folder)
    for dcm_file in sorted(dcm_path.glob("*.dcm")):
        pid = extract_id_from_filename(dcm_file.name)
        if pid is None:
            print(f"  [SKIP] Cannot extract ID from: {dcm_file.name}")
            continue
        label = label_map.get(pid, "UNKNOWN")
        if label == "UNKNOWN":
            print(f"  [SKIP] No label for ID {pid}: {dcm_file.name}")
            continue
        records.append((dcm_file, pid, label))
    return records


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Convert DICOM to JPEG
# ─────────────────────────────────────────────────────────────────────────────
def dicom_to_pil(dcm_path: Path) -> Image.Image:
    """
    Reads a DICOM file and returns a normalised 8-bit grayscale PIL Image.
    Handles multi-frame, different photometric interpretations, and
    applies windowing if VOI LUT data is available.
    """
    ds = pydicom.dcmread(str(dcm_path), force=True)

    try:
        pixel_array = ds.pixel_array.astype(np.float32)
    except Exception as e:
        raise ValueError(f"Cannot read pixel data from {dcm_path}: {e}")

    # Handle multi-frame: take the middle frame
    if pixel_array.ndim == 3:
        mid = pixel_array.shape[0] // 2
        pixel_array = pixel_array[mid]

    # Apply rescale slope/intercept if present (Hounsfield units for CT)
    slope     = float(getattr(ds, "RescaleSlope",     1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    pixel_array = pixel_array * slope + intercept

    # Apply VOI windowing if available
    wc = getattr(ds, "WindowCenter", None)
    ww = getattr(ds, "WindowWidth",  None)
    if wc is not None and ww is not None:
        wc = float(wc[0]) if hasattr(wc, "__len__") else float(wc)
        ww = float(ww[0]) if hasattr(ww, "__len__") else float(ww)
        lo = wc - ww / 2
        hi = wc + ww / 2
        pixel_array = np.clip(pixel_array, lo, hi)

    # Normalise to 0–255
    pmin, pmax = pixel_array.min(), pixel_array.max()
    if pmax > pmin:
        pixel_array = (pixel_array - pmin) / (pmax - pmin) * 255
    else:
        pixel_array = np.zeros_like(pixel_array)
    pixel_array = pixel_array.astype(np.uint8)

    # Handle MONOCHROME1 (inverted: 0=white, 255=black) — invert it
    photometric = str(getattr(ds, "PhotometricInterpretation", "")).strip()
    if photometric == "MONOCHROME1":
        pixel_array = 255 - pixel_array

    img = Image.fromarray(pixel_array, mode="L")
    return img.convert("RGB")   # model expects 3-channel input


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Split and save
# ─────────────────────────────────────────────────────────────────────────────
def split_records(records, train_r=TRAIN_RATIO, val_r=VAL_RATIO):
    """Stratified split into train / val / test."""
    cancer = [r for r in records if r[2] == "CANCER"]
    normal = [r for r in records if r[2] == "NORMAL"]

    random.shuffle(cancer)
    random.shuffle(normal)

    def _split(lst, tr, vr):
        n = len(lst)
        n_train = int(n * tr)
        n_val   = int(n * vr)
        return lst[:n_train], lst[n_train:n_train+n_val], lst[n_train+n_val:]

    c_train, c_val, c_test = _split(cancer, train_r, val_r)
    n_train, n_val, n_test = _split(normal, train_r, val_r)

    return (
        c_train + n_train,
        c_val   + n_val,
        c_test  + n_test,
    )


def save_split(records, split_name: str, out_root: Path,
               labels_writer, errors: list):
    """Convert + save DCM records to out_root/split_name/LABEL/id.jpg"""
    for dcm_path, pid, label in records:
        dest_dir = out_root / split_name / label
        dest_dir.mkdir(parents=True, exist_ok=True)
        # Use patient_id + original stem to keep unique names
        out_name = f"{pid}_{dcm_path.stem}.jpg"
        out_path = dest_dir / out_name
        try:
            img = dicom_to_pil(dcm_path)
            img.save(str(out_path), "JPEG", quality=95)
            labels_writer.writerow([pid, dcm_path.name, split_name, label])
        except Exception as e:
            err_msg = f"ERROR: {dcm_path.name} — {e}"
            print(f"  {err_msg}")
            errors.append(err_msg)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  OncoDet Dataset Preparation")
    print("=" * 60)

    # 1. Parse diagnoses
    print("\n[1/4] Parsing tashxis.docx ...")
    # Manual overrides for IDs whose labels were embedded in other blocks
    MANUAL = {
        "38456": "CANCER",   # "ochagli zatening" - suspicious focal opacities
        "23901": "CANCER",   # "cheklangan zatimlash" - limited darkening left lung
        "30144": "NORMAL",   # "pnevmoniya" label - not cancer, treat as non-cancer
        "26042": "CANCER",   # context: oncology centre patient
        "26783": "CANCER",   # context: oncology centre patient
        "26599": "CANCER",   # context: oncology centre patient
        "11862": "CANCER",   # "dopolnitel'naya ten'" - additional shadow right field
        "9587" : "CANCER",   # "ochagovye izmeneniya" lower right lung
        "21870": "NORMAL",   # no strong cancer findings in context
        "20775": "NORMAL",   # no strong cancer findings in context
        "25986": "NORMAL",   # normal chest X-ray context
        "26941": "NORMAL",   # no strong cancer findings
        "35359": "CANCER",   # oncology centre post-op
        "36061": "CANCER",   # oncology centre patient
    }
    label_map = parse_diagnoses(DOCX_PATH)
    label_map.update(MANUAL)
    n_cancer  = sum(1 for v in label_map.values() if v == "CANCER")
    n_normal  = sum(1 for v in label_map.values() if v == "NORMAL")
    n_unknown = sum(1 for v in label_map.values() if v == "UNKNOWN")
    print(f"      Patients: {len(label_map)} total — "
          f"{n_cancer} CANCER, {n_normal} NORMAL, {n_unknown} UNKNOWN")

    # 2. Map DCM → labels
    print("\n[2/4] Mapping DCM files to labels ...")
    records = map_dcm_to_labels(DCM_FOLDER, label_map)
    r_cancer = sum(1 for r in records if r[2] == "CANCER")
    r_normal = sum(1 for r in records if r[2] == "NORMAL")
    print(f"      DCM files matched: {len(records)} "
          f"({r_cancer} CANCER, {r_normal} NORMAL)")

    if not records:
        print("  ERROR: No matched records. Check docx IDs vs DCM filenames.")
        return

    # 3. Split
    print("\n[3/4] Splitting into train / val / test ...")
    train, val, test = split_records(records)
    print(f"      Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # 4. Convert + save
    print(f"\n[4/4] Converting DICOM to JPEG and saving to {OUT_ROOT} ...")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    errors = []

    labels_csv = OUT_ROOT / "labels.csv"
    with open(labels_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["patient_id", "dcm_filename", "split", "label"])
        save_split(train, "train", OUT_ROOT, w, errors)
        save_split(val,   "val",   OUT_ROOT, w, errors)
        save_split(test,  "test",  OUT_ROOT, w, errors)

    # Count output files
    out_counts = {}
    for split in ("train", "val", "test"):
        for cls in ("CANCER", "NORMAL"):
            p = OUT_ROOT / split / cls
            count = len(list(p.glob("*.jpg"))) if p.exists() else 0
            out_counts[f"{split}/{cls}"] = count

    print("\n" + "=" * 60)
    print("  DONE — Dataset Statistics")
    print("=" * 60)
    for k, v in out_counts.items():
        print(f"  {k:20s}: {v} images")
    total = sum(out_counts.values())
    print(f"  {'TOTAL':20s}: {total} images")
    print(f"  Labels CSV  : {labels_csv}")
    if errors:
        print(f"\n  Conversion errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"    {e}")
    print()


if __name__ == "__main__":
    main()
