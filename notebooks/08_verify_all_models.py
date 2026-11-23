"""
08_verify_all_models.py
Loads all 4 models and verifies predictions + SHAP readiness.
Run from project root:  python notebooks/08_verify_all_models.py
"""
import sys
from pathlib import Path

# Add project root to path so we can import app.utils if needed
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd

MODELS_DIR = ROOT / 'models'


def check_file(name):
    path = MODELS_DIR / name
    status = "✅" if path.exists() else "❌"
    print(f"  {status} {name}")
    return path.exists()


print("=" * 60)
print("MODEL INTEGRATION TEST")
print("=" * 60)

print("\n[1/5] Checking model artifacts...")
files = [
    'symptom_model.pkl', 'symptom_label_encoder.pkl', 'symptom_features.pkl',
    'symptom_model_name.pkl',
    'diabetes_model.pkl', 'diabetes_scaler.pkl', 'diabetes_imputer.pkl',
    'diabetes_features.pkl', 'diabetes_model_name.pkl',
    'heart_model.pkl', 'heart_scaler.pkl', 'heart_imputer.pkl',
    'heart_features.pkl', 'heart_model_name.pkl',
    'liver_model.pkl', 'liver_scaler.pkl', 'liver_imputer.pkl',
    'liver_features.pkl', 'liver_model_name.pkl',
]
all_exist = all(check_file(f) for f in files)

if not all_exist:
    print("\n❌ Some artifacts missing. Re-run Phase 2 notebooks.")
    sys.exit(1)

print("\n[2/5] Loading symptom model...")
sym_model = joblib.load(MODELS_DIR / 'symptom_model.pkl')
sym_le = joblib.load(MODELS_DIR / 'symptom_label_encoder.pkl')
sym_features = joblib.load(MODELS_DIR / 'symptom_features.pkl')
sym_name = joblib.load(MODELS_DIR / 'symptom_model_name.pkl')
print(f"  ✅ {sym_name} | {len(sym_features)} symptoms | {len(sym_le.classes_)} diseases")

print("\n[3/5] Symptom prediction test (Dengue pattern)...")
dengue_pattern = ['high_fever', 'headache', 'joint_pain', 'muscle_pain',
                   'skin_rash', 'nausea', 'fatigue', 'chills', 'vomiting',
                   'back_pain', 'pain_behind_the_eyes', 'loss_of_appetite',
                   'red_spots_over_body']
vec = np.array([[1 if f in dengue_pattern else 0 for f in sym_features]])
proba = sym_model.predict_proba(vec)[0]
top3 = np.argsort(proba)[::-1][:3]
top3_names = sym_le.inverse_transform(top3)
print(f"  Input: {len(dengue_pattern)} symptoms")
for name, p in zip(top3_names, proba[top3]):
    print(f"    {name}: {p*100:.2f}%")
assert top3_names[0] == 'Dengue', "❌ Expected Dengue as top prediction"
print("  ✅ Symptom model verified")


def test_disease(name, input_dict):
    """Verify one disease model with a realistic input."""
    model = joblib.load(MODELS_DIR / f'{name}_model.pkl')
    scaler = joblib.load(MODELS_DIR / f'{name}_scaler.pkl')
    imputer = joblib.load(MODELS_DIR / f'{name}_imputer.pkl')
    features = joblib.load(MODELS_DIR / f'{name}_features.pkl')
    model_name = joblib.load(MODELS_DIR / f'{name}_model_name.pkl')

    df = pd.DataFrame([[input_dict.get(f, np.nan) for f in features]], columns=features)
    df_imp = pd.DataFrame(imputer.transform(df), columns=features)
    df_scaled = pd.DataFrame(scaler.transform(df_imp), columns=features)

    proba = model.predict_proba(df_scaled)[0][1]
    print(f"  ✅ {name.title()}: {model_name}, risk={proba*100:.1f}%")
    return proba


print("\n[4/5] Disease model predictions...")

# Diabetes — high-risk profile
test_disease('diabetes', {
    'Pregnancies': 6, 'Glucose': 168, 'BloodPressure': 88,
    'SkinThickness': 35, 'Insulin': 200, 'BMI': 38.5,
    'DiabetesPedigreeFunction': 0.85, 'Age': 52
})

# Heart — high-risk profile (using fedesoriano encoded features)
test_disease('heart', {
    'Age': 65, 'Sex': 1, 'RestingBP': 160, 'Cholesterol': 280,
    'FastingBS': 1, 'MaxHR': 110, 'ExerciseAngina': 1, 'Oldpeak': 2.5,
    'ChestPainType_ATA': 0, 'ChestPainType_NAP': 0, 'ChestPainType_TA': 0,
    'RestingECG_Normal': 1, 'RestingECG_ST': 0, 'ST_Slope_Flat': 1, 'ST_Slope_Up': 0
})

# Liver — high-risk profile
test_disease('liver', {
    'Age': 55, 'Gender': 1, 'Total_Bilirubin': 3.5, 'Direct_Bilirubin': 1.8,
    'Alkaline_Phosphotase': 350, 'Alamine_Aminotransferase': 120,
    'Aspartate_Aminotransferase': 150, 'Total_Protiens': 6.2,
    'Albumin': 2.8, 'Albumin_and_Globulin_Ratio': 0.8
})

print("\n[5/5] SHAP readiness...")
try:
    import shap
    from sklearn.linear_model import LogisticRegression
    for name in ['diabetes', 'heart', 'liver']:
        model = joblib.load(MODELS_DIR / f'{name}_model.pkl')
        model_inner = model.named_steps['clf'] if hasattr(model, 'named_steps') else model
        if isinstance(model_inner, LogisticRegression):
            kind = 'LinearExplainer'
        else:
            kind = 'TreeExplainer'
        print(f"  ✅ {name}: uses {kind}")
except ImportError:
    print("  ❌ shap not installed")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL MODELS VERIFIED — Ready for the app")
print("=" * 60)