"""Every chart builder must work (and serialise to JSON) on the minimum supported Plotly."""
import pandas as pd
import pytest

from app.utils import ui
from app.utils.predict import predict_symptom, run_assessment, symptom_impact
from app.utils.schemas import SPECS


@pytest.mark.parametrize("name", ["diabetes", "heart", "liver"])
def test_risk_charts(name):
    for preset in SPECS[name].presets.values():
        r = run_assessment(name, preset)
        for fig in (ui.gauge_chart(r["risk_pct"], r["level"]), ui.factors_chart(r["factors"]),
                    ui.waterfall_chart(r["base_pct"], r["factors"], r["risk_pct"]),
                    ui.mini_gauge(r["risk_pct"], name, "#ef4444")):
            assert fig.to_json()


def test_symptom_and_dashboard_charts():
    top, probs = predict_symptom(["high_fever", "headache", "joint_pain"])
    assert ui.prob_bars([t.strip() for t in top], probs).to_json()
    assert ui.impact_chart(symptom_impact(["high_fever", "headache", "joint_pain"])).to_json()
    df = pd.DataFrame({"created_at": pd.date_range("2026-01-01", periods=4), "risk_score": [10, 40, 70, 90],
                       "disease": ["Diabetes", "Diabetes", "Heart Disease", "Heart Disease"]})
    assert ui.trend_chart(df).to_json()
    assert ui.donut(["a", "b"], [3, 4], center_text="7").to_json()
