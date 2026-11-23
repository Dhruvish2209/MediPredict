"""
00_verify_datasets.py
Sanity-check all downloaded datasets before starting EDA.
Run from project root:  python notebooks/00_verify_datasets.py
"""
import os
import pandas as pd

# Expected (rows, cols) for each file
EXPECTED = {
    'dataset.csv': (4920, 18),
    'Symptom-severity.csv': (133, 2),
    'symptom_Description.csv': (41, 2),
    'symptom_precaution.csv': (41, 5),
    'diabetes.csv': (768, 9),
    'heart.csv': (918, 12),
    'indian_liver_patient.csv': (583, 11),
}

DATA_DIR = 'E:\\Uday\\College_Work\\Sem 3\\Mini Project\\MediPredict\\data\\raw'
all_ok = True

print("=" * 60)
print("DATASET VERIFICATION")
print("=" * 60)

for filename, expected_shape in EXPECTED.items():
    path = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(path):
        print(f"❌ MISSING: {filename}")
        all_ok = False
        continue
    
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        # Liver dataset sometimes needs latin-1
        df = pd.read_csv(path, encoding='latin-1')
    
    actual = df.shape
    if actual == expected_shape:
        print(f"✅ {filename:30s} shape={actual}  cols={list(df.columns[:3])}...")
    else:
        print(f"⚠️  {filename:30s} shape={actual} (expected {expected_shape})")
        all_ok = False

print("=" * 60)
if all_ok:
    print("✅ ALL DATASETS READY — Proceed to EDA")
else:
    print("❌ Fix the issues above before proceeding")
print("=" * 60)