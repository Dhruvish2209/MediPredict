"""Declarative description of every structured-risk form.

One schema drives: the input form, validation hints, feature encoding, SHAP grouping,
reference-range chips, recommendations and the PDF report. Adding a new disease model
means adding a DiseaseSpec here - no new UI code.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Field:
    key: str
    label: str
    kind: str                      # 'number' | 'choice' | 'binary'
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    unit: str = ""
    help: str = ""
    options: Optional[list] = None   # choice: [(value, label), ...]
    features: Optional[list] = None  # model features this field controls (default [key])
    ref: Optional[tuple] = None      # (low, high) typical healthy range
    ref_text: str = ""
    optional: bool = False           # "I don't know" allowed -> NaN -> imputer
    whatif: bool = False             # offered in the what-if simulator
    section: str = "Details"
    is_int: bool = False

    @property
    def model_features(self):
        return self.features or [self.key]

    def label_for(self, value):
        if self.kind in ("choice", "binary") and self.options:
            for v, lab in self.options:
                if v == value:
                    return lab
        if value is None:
            return "Not provided"
        if self.kind == "number":
            v = int(value) if self.is_int else round(float(value), 2)
            return f"{v} {self.unit}".strip()
        return str(value)


@dataclass
class DiseaseSpec:
    name: str                 # model prefix: 'diabetes' | 'heart' | 'liver'
    title: str
    short: str                # label stored in history
    icon: str                 # material icon name
    emoji: str
    accent: str
    dataset: str
    blurb: str
    fields: list
    encode: Callable
    presets: dict = field(default_factory=dict)
    reference_target: str = ""

    def field(self, key):
        return next(f for f in self.fields if f.key == key)


# ------------------------------------------------------------------ DIABETES
def _enc_diabetes(v):
    return {k: v.get(k) for k in ["Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
                                  "Insulin", "BMI", "DiabetesPedigreeFunction", "Age"]}


DIABETES = DiseaseSpec(
    name="diabetes", title="Diabetes Risk Assessment", short="Diabetes", icon="water_drop", emoji="🩸",
    accent="#f59e0b",
    dataset="PIMA Indians Diabetes Database · 768 patients · 8 clinical measurements",
    blurb="Estimates the likelihood of type-2 diabetes from routine clinical measurements.",
    reference_target="Outcome",
    fields=[
        Field("Age", "Age", "number", 35, 18, 100, 1, "years", "Your age in years.", section="About you", is_int=True),
        Field("Pregnancies", "Pregnancies", "number", 0, 0, 20, 1, "", "Number of times pregnant (0 if not applicable).",
              section="About you", is_int=True),
        Field("BMI", "Body Mass Index", "number", 25.0, 12.0, 70.0, 0.1, "kg/m²",
              "Weight (kg) ÷ height (m)². Use the BMI calculator below if you are unsure.",
              ref=(18.5, 24.9), ref_text="18.5 – 24.9", whatif=True, section="About you"),
        Field("DiabetesPedigreeFunction", "Diabetes Pedigree Function", "number", 0.5, 0.05, 2.5, 0.01, "",
              "A score of diabetes family history (higher = stronger family history). Typical range 0.1 – 1.0.",
              section="About you"),
        Field("Glucose", "Plasma Glucose", "number", 100, 40, 300, 1, "mg/dL",
              "Plasma glucose 2 h after an oral glucose tolerance test (the dataset's measure) or a recent lab value.",
              ref=(70, 139), ref_text="< 140 (2-h test) · fasting < 100", whatif=True, section="Lab values", is_int=True),
        Field("BloodPressure", "Diastolic Blood Pressure", "number", 75, 40, 140, 1, "mm Hg",
              "The lower number of a blood-pressure reading.", ref=(60, 80), ref_text="60 – 80", whatif=True,
              section="Lab values", is_int=True),
        Field("Insulin", "2-hour Serum Insulin", "number", 80, 10, 900, 1, "µU/mL",
              "Skip this if you have not had an insulin test.", ref=(16, 166), ref_text="16 – 166",
              optional=True, section="Lab values", is_int=True),
        Field("SkinThickness", "Triceps Skin-fold Thickness", "number", 25, 5, 100, 1, "mm",
              "Measured by a clinician with callipers. Skip if unknown.", optional=True,
              section="Lab values", is_int=True),
    ],
    encode=_enc_diabetes,
    presets={
        "Healthy example": dict(Age=25, Pregnancies=1, BMI=22.5, DiabetesPedigreeFunction=0.2, Glucose=90,
                                BloodPressure=70, Insulin=85, SkinThickness=20),
        "High-risk example": dict(Age=52, Pregnancies=6, BMI=38.5, DiabetesPedigreeFunction=0.85, Glucose=168,
                                  BloodPressure=88, Insulin=200, SkinThickness=35),
    },
)


# --------------------------------------------------------------------- HEART
def _enc_heart(v):
    cp, ecg, slope = v.get("ChestPainType"), v.get("RestingECG"), v.get("ST_Slope")
    return {
        "Age": v.get("Age"), "Sex": 1 if v.get("Sex") == "M" else 0,
        "RestingBP": v.get("RestingBP"), "Cholesterol": v.get("Cholesterol"),
        "FastingBS": int(v.get("FastingBS", 0)), "MaxHR": v.get("MaxHR"),
        "ExerciseAngina": 1 if v.get("ExerciseAngina") == "Y" else 0, "Oldpeak": v.get("Oldpeak"),
        "ChestPainType_ATA": int(cp == "ATA"), "ChestPainType_NAP": int(cp == "NAP"), "ChestPainType_TA": int(cp == "TA"),
        "RestingECG_Normal": int(ecg == "Normal"), "RestingECG_ST": int(ecg == "ST"),
        "ST_Slope_Flat": int(slope == "Flat"), "ST_Slope_Up": int(slope == "Up"),
    }


HEART = DiseaseSpec(
    name="heart", title="Heart Disease Risk Assessment", short="Heart Disease", icon="cardiology", emoji="❤️",
    accent="#ef4444",
    dataset="Heart Failure Prediction Dataset · 918 patients from 5 hospitals · 11 clinical features",
    blurb="Estimates the likelihood of heart disease from your vitals, ECG findings and exercise-test results.",
    reference_target="HeartDisease",
    fields=[
        Field("Age", "Age", "number", 50, 18, 100, 1, "years", section="About you", is_int=True),
        Field("Sex", "Sex", "choice", "M", options=[("M", "Male"), ("F", "Female")], section="About you"),
        Field("ChestPainType", "Chest Pain Type", "choice", "ASY",
              options=[("ASY", "Asymptomatic"), ("ATA", "Atypical angina"), ("NAP", "Non-anginal pain"), ("TA", "Typical angina")],
              features=["ChestPainType_ATA", "ChestPainType_NAP", "ChestPainType_TA"],
              help="Asymptomatic = no chest pain symptoms. Typical angina = pressure/tightness triggered by effort.",
              section="Symptoms & exercise"),
        Field("ExerciseAngina", "Exercise-induced Angina", "binary", "N", options=[("N", "No"), ("Y", "Yes")],
              help="Chest pain that appears during exercise.", section="Symptoms & exercise"),
        Field("RestingBP", "Resting Blood Pressure", "number", 120, 70, 250, 1, "mm Hg", "Systolic (upper) value at rest.",
              ref=(90, 120), ref_text="90 – 120", whatif=True, section="Vitals & labs", is_int=True),
        Field("Cholesterol", "Serum Cholesterol", "number", 200, 80, 650, 1, "mg/dL",
              "Total cholesterol. Skip if you have not had a lipid test.", ref=(125, 199), ref_text="< 200",
              optional=True, whatif=True, section="Vitals & labs", is_int=True),
        Field("FastingBS", "Fasting Blood Sugar > 120 mg/dL", "binary", 0, options=[(0, "No"), (1, "Yes")],
              section="Vitals & labs"),
        Field("RestingECG", "Resting ECG", "choice", "Normal",
              options=[("Normal", "Normal"), ("ST", "ST-T abnormality"), ("LVH", "Left ventricular hypertrophy")],
              features=["RestingECG_Normal", "RestingECG_ST"], section="ECG & stress test"),
        Field("MaxHR", "Maximum Heart Rate Achieved", "number", 150, 50, 230, 1, "bpm",
              "Highest heart rate reached during an exercise test.", whatif=True, section="ECG & stress test", is_int=True),
        Field("Oldpeak", "ST Depression (Oldpeak)", "number", 0.0, -3.0, 7.0, 0.1, "mm",
              "ST depression induced by exercise relative to rest.", ref=(0.0, 1.0), ref_text="0 – 1.0",
              section="ECG & stress test"),
        Field("ST_Slope", "ST Slope", "choice", "Up", options=[("Up", "Upsloping"), ("Flat", "Flat"), ("Down", "Downsloping")],
              features=["ST_Slope_Flat", "ST_Slope_Up"], help="Slope of the peak-exercise ST segment.",
              section="ECG & stress test"),
    ],
    encode=_enc_heart,
    presets={
        "Healthy example": dict(Age=40, Sex="M", ChestPainType="ATA", ExerciseAngina="N", RestingBP=120, Cholesterol=190,
                                FastingBS=0, RestingECG="Normal", MaxHR=172, Oldpeak=0.0, ST_Slope="Up"),
        "High-risk example": dict(Age=65, Sex="M", ChestPainType="ASY", ExerciseAngina="Y", RestingBP=160, Cholesterol=280,
                                  FastingBS=1, RestingECG="Normal", MaxHR=110, Oldpeak=2.5, ST_Slope="Flat"),
    },
)


# --------------------------------------------------------------------- LIVER
def _enc_liver(v):
    d = {k: v.get(k) for k in ["Age", "Total_Bilirubin", "Direct_Bilirubin", "Alkaline_Phosphotase",
                               "Alamine_Aminotransferase", "Aspartate_Aminotransferase", "Total_Protiens",
                               "Albumin", "Albumin_and_Globulin_Ratio"]}
    d["Gender"] = 1 if v.get("Gender") == "Male" else 0
    return d


LIVER = DiseaseSpec(
    name="liver", title="Liver Disease Risk Assessment", short="Liver Disease", icon="gastroenterology", emoji="🫁",
    accent="#8b5cf6",
    dataset="Indian Liver Patient Dataset · 583 patients · 10 blood-test features",
    blurb="Estimates the likelihood of liver disease from a standard liver-function blood panel.",
    reference_target="Dataset",
    fields=[
        Field("Age", "Age", "number", 45, 1, 100, 1, "years", section="About you", is_int=True),
        Field("Gender", "Gender", "choice", "Male", options=[("Male", "Male"), ("Female", "Female")], section="About you"),
        Field("Total_Bilirubin", "Total Bilirubin", "number", 1.0, 0.1, 80.0, 0.1, "mg/dL", ref=(0.1, 1.2),
              ref_text="0.1 – 1.2", whatif=True, section="Bilirubin & proteins"),
        Field("Direct_Bilirubin", "Direct Bilirubin", "number", 0.3, 0.05, 20.0, 0.1, "mg/dL", ref=(0.0, 0.3),
              ref_text="0 – 0.3", section="Bilirubin & proteins"),
        Field("Total_Protiens", "Total Proteins", "number", 6.8, 2.0, 10.0, 0.1, "g/dL", ref=(6.0, 8.3),
              ref_text="6.0 – 8.3", section="Bilirubin & proteins"),
        Field("Albumin", "Albumin", "number", 4.0, 0.5, 6.0, 0.1, "g/dL", ref=(3.5, 5.0), ref_text="3.5 – 5.0",
              whatif=True, section="Bilirubin & proteins"),
        Field("Albumin_and_Globulin_Ratio", "Albumin / Globulin Ratio", "number", 1.2, 0.1, 3.0, 0.05, "",
              "Skip if not reported in your lab results.", ref=(1.1, 2.5), ref_text="1.1 – 2.5", optional=True,
              section="Bilirubin & proteins"),
        Field("Alkaline_Phosphotase", "Alkaline Phosphatase (ALP)", "number", 150, 40, 2300, 1, "IU/L", ref=(44, 147),
              ref_text="44 – 147", section="Liver enzymes", is_int=True),
        Field("Alamine_Aminotransferase", "ALT (SGPT)", "number", 30, 5, 2100, 1, "IU/L", ref=(7, 56), ref_text="7 – 56",
              whatif=True, section="Liver enzymes", is_int=True),
        Field("Aspartate_Aminotransferase", "AST (SGOT)", "number", 35, 5, 5000, 1, "IU/L", ref=(10, 40), ref_text="10 – 40",
              whatif=True, section="Liver enzymes", is_int=True),
    ],
    encode=_enc_liver,
    presets={
        "Healthy example": dict(Age=35, Gender="Female", Total_Bilirubin=0.7, Direct_Bilirubin=0.1, Total_Protiens=7.0,
                                Albumin=4.2, Albumin_and_Globulin_Ratio=1.4, Alkaline_Phosphotase=110,
                                Alamine_Aminotransferase=25, Aspartate_Aminotransferase=28),
        "High-risk example": dict(Age=55, Gender="Male", Total_Bilirubin=3.5, Direct_Bilirubin=1.8, Total_Protiens=6.2,
                                  Albumin=2.8, Albumin_and_Globulin_Ratio=0.8, Alkaline_Phosphotase=350,
                                  Alamine_Aminotransferase=120, Aspartate_Aminotransferase=150),
    },
)

SPECS = {"diabetes": DIABETES, "heart": HEART, "liver": LIVER}


def range_status(f: Field, value):
    """'low' | 'normal' | 'high' | None relative to the typical healthy range."""
    if f.ref is None or value is None:
        return None
    lo, hi = f.ref
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "normal"
