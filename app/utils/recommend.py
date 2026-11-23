"""Rule-based, plain-language guidance generated from the person's own values.
General wellness information only - never a diagnosis or treatment plan."""

LEVEL_ADVICE = {
    "HIGH": ("alert", "See a doctor soon",
             "Your profile resembles patients who were diagnosed with this condition. Book an appointment in the next few "
             "days and bring these results and your recent lab reports. This is a screening estimate, not a diagnosis."),
    "MEDIUM": ("warn", "Discuss this at your next check-up",
               "Some of your values are in a range worth watching. Mention these results to your doctor and consider "
               "repeating the relevant tests in 3 – 6 months."),
    "LOW": ("good", "Keep up the good habits",
            "Your profile is similar to patients without this condition. Stay active, eat well and keep your routine "
            "check-ups up to date."),
}


def _r(tone, title, text):
    return {"tone": tone, "title": title, "text": text}


def recommendations(name: str, v: dict, level: str) -> list:
    tone, title, text = LEVEL_ADVICE[level]
    out = [_r(tone, title, text)]
    g = v.get

    if name == "diabetes":
        if (g("Glucose") or 0) >= 200:
            out.append(_r("alert", "Glucose is in the diabetic range", "A 2-hour glucose of 200 mg/dL or more is in the "
                          "diabetic range. Ask your doctor for confirmatory tests (fasting glucose, HbA1c)."))
        elif (g("Glucose") or 0) >= 140:
            out.append(_r("warn", "Glucose is above normal", "Readings of 140 – 199 mg/dL after a glucose challenge suggest "
                          "pre-diabetes. Lifestyle changes work well at this stage."))
        bmi = g("BMI") or 0
        if bmi >= 30:
            out.append(_r("warn", "BMI is in the obese range", "Losing even 5 – 7 % of body weight meaningfully lowers "
                          "diabetes risk. Aim for 150 minutes of brisk activity per week."))
        elif bmi >= 25:
            out.append(_r("info", "BMI is above the healthy range", "Small steps (daily walks, fewer sugary drinks, "
                          "more fibre) add up quickly."))
        if (g("BloodPressure") or 0) >= 90:
            out.append(_r("warn", "Diastolic blood pressure is high", "High blood pressure and diabetes often occur "
                          "together. Have your blood pressure checked regularly."))
        if (g("DiabetesPedigreeFunction") or 0) >= 0.8:
            out.append(_r("info", "Strong family history", "A strong family history raises baseline risk, so regular "
                          "screening matters even when other numbers look fine."))
        if (g("Age") or 0) >= 45:
            out.append(_r("info", "Age-based screening", "Guidelines suggest diabetes screening at least every 3 years "
                          "from age 45."))
        out.append(_r("info", "Confirm with a lab test", "Only a laboratory test (fasting glucose or HbA1c) can diagnose "
                      "diabetes. This tool is a risk estimate."))

    elif name == "heart":
        if (g("RestingBP") or 0) >= 140:
            out.append(_r("warn", "Resting blood pressure is high", "Readings of 140 mm Hg or more at rest are in the "
                          "hypertensive range. Reduce salt, stay active and get this checked."))
        elif (g("RestingBP") or 0) >= 130:
            out.append(_r("info", "Blood pressure is slightly raised", "Readings of 130 – 139 are classed as stage-1 "
                          "hypertension by some guidelines. Monitor it regularly."))
        if (g("Cholesterol") or 0) >= 240:
            out.append(_r("warn", "Cholesterol is high", "Total cholesterol above 240 mg/dL raises heart risk. Discuss "
                          "diet and possibly medication with your doctor."))
        elif (g("Cholesterol") or 0) >= 200:
            out.append(_r("info", "Cholesterol is borderline", "Cutting saturated fat and adding fibre and omega-3s can help."))
        if g("ExerciseAngina") == "Y":
            out.append(_r("warn", "Chest pain during exercise", "Angina on exertion should be assessed by a cardiologist, "
                          "especially if it is new or getting worse."))
        if g("ChestPainType") == "TA":
            out.append(_r("warn", "Typical angina pattern", "Pressure or tightness triggered by effort and relieved by rest "
                          "deserves a medical evaluation."))
        if (g("Oldpeak") or 0) >= 2:
            out.append(_r("warn", "Marked ST depression", "ST depression of 2 mm or more on a stress test is a recognised "
                          "warning sign. Review the result with a cardiologist."))
        age, hr = g("Age") or 0, g("MaxHR") or 0
        if age and hr and hr < 0.7 * (220 - age):
            out.append(_r("info", "Low peak heart rate", "Your maximum heart rate is well below the age-predicted value "
                          f"(about {220 - age} bpm), which can reflect reduced cardiac fitness or medication effects."))
        if g("FastingBS") == 1:
            out.append(_r("info", "Raised fasting sugar", "Elevated blood sugar and heart disease are closely linked; "
                          "consider a diabetes check."))
        out.append(_r("info", "Heart-healthy habits", "Do not smoke, keep a Mediterranean-style diet, aim for 150 minutes "
                      "of activity a week and manage stress and sleep."))

    elif name == "liver":
        tb, db_ = g("Total_Bilirubin") or 0, g("Direct_Bilirubin") or 0
        if tb >= 3:
            out.append(_r("alert", "Bilirubin is markedly raised", "Total bilirubin above 3 mg/dL usually shows as yellowing "
                          "of the skin or eyes. Please see a doctor promptly."))
        elif tb > 1.2 or db_ > 0.3:
            out.append(_r("warn", "Bilirubin is above normal", "Raised bilirubin can reflect liver, bile-duct or red-cell "
                          "problems and should be followed up."))
        if (g("Alamine_Aminotransferase") or 0) > 56 or (g("Aspartate_Aminotransferase") or 0) > 40:
            out.append(_r("warn", "Liver enzymes (ALT/AST) are elevated", "Raised transaminases indicate liver-cell irritation. "
                          "Common causes include fatty liver, alcohol, viral hepatitis and some medicines."))
        if (g("Alkaline_Phosphotase") or 0) > 147:
            out.append(_r("info", "ALP is elevated", "ALP can be raised in bile-duct and bone conditions; your doctor can "
                          "interpret it with your other tests."))
        if (g("Albumin") or 9) < 3.5 or (g("Albumin_and_Globulin_Ratio") or 9) < 1.0:
            out.append(_r("warn", "Low albumin / A:G ratio", "Albumin is made by the liver; a low value can indicate reduced "
                          "liver function or protein loss."))
        out.append(_r("info", "Protect your liver", "Limit alcohol, avoid exceeding the recommended dose of paracetamol, "
                      "maintain a healthy weight and consider hepatitis A/B vaccination."))

    return out
