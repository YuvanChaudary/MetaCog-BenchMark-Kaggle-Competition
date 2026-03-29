"""
MetaCog Benchmark — Streamlit Dashboard
=========================================
Live evaluation dashboard with 5 panels:
  1. Sidebar configuration
  2. MetaCog Index gauge + metrics + verdict
  3. Calibration curve + focus breakdown
  4. Live task feed
  5. Failure taxonomy
"""
import os
import time
from datetime import datetime

import streamlit as st
import duckdb
import plotly.graph_objects as go

from dashboard.components.metacog_gauge import render_metacog_gauge
from dashboard.components.calibration_curve import render_calibration_curve
from dashboard.components.focus_breakdown import render_focus_breakdown
from dashboard.components.verdict_card import render_verdict_card
from dashboard.components.live_feed import render_live_feed

# ─── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="MetaCog Benchmark",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.5rem; }
div[data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.08);
    border-radius: 10px;
    padding: 12px 16px;
    border-left: 3px solid #3498db;
}
div[data-testid="stMetric"] label { font-size: 13px !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 28px !important; font-weight: 700 !important;
}
.stExpander { border: 1px solid #eee; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.getenv("DATABASE_URL", "./data/metacog.duckdb")


# ─── Data Loading ───────────────────────────────────────────
@st.cache_data(ttl=3)
def _normalize_focus_area(area: str) -> str:
    """Map focus area aliases from storage to display keys."""
    if not area:
        return "unknown"
    alias_map = {
        "calib": "calibration",
        "calibration": "calibration",
        "error_detect": "error_detection",
        "error_detection": "error_detection",
        "correction": "correction",
        "certainty": "certainty",
    }
    return alias_map.get(area, area)


def load_run_results(run_id: str) -> dict:
    """Query DuckDB for all results with given run_id."""
    if not run_id or not os.path.exists(DB_PATH):
        return {}
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        rows = conn.execute(
            "SELECT * FROM results WHERE run_id = ? ORDER BY timestamp DESC",
            [run_id]
        ).fetchdf()
        conn.close()

        if rows.empty:
            return {}

        task_results = rows.to_dict("records")

        # Compute aggregate stats
        focus_areas_display = ["calibration", "error_detection", "correction", "certainty"]
        sub_scores = {}
        rows["focus_area_display"] = rows["focus_area"].apply(_normalize_focus_area)
        for fa in focus_areas_display:
            fa_rows = rows[rows["focus_area_display"] == fa]
            if fa_rows.empty:
                sub_scores[fa] = {"score": 0.0, "n_tasks": 0, "dominant_failure": "no_data",
                                  "confidence_interval": (0.0, 0.0)}
            else:
                n = len(fa_rows)
                acc = fa_rows["correct"].mean() * 100
                sub_scores[fa] = {
                    "score": round(acc, 1),
                    "n_tasks": n,
                    "dominant_failure": "well_calibrated" if acc > 70 else "needs_improvement",
                    "confidence_interval": (max(0, acc - 8), min(100, acc + 8)),
                }

        metacog_index = sum(s["score"] for s in sub_scores.values()) / max(len(sub_scores), 1)

        # Calibration bin data
        bin_data = _compute_bin_data(rows)

        # ECE / Brier
        ece = rows["ece_running"].iloc[-1] if "ece_running" in rows.columns else 0.0
        brier = rows["brier_running"].iloc[-1] if "brier_running" in rows.columns else 0.0

        # Failure taxonomy
        total = len(rows)
        correct_count = rows["correct"].sum() if "correct" in rows.columns else 0
        taxonomy = {
            "overconfident_wrong": round(
                len(rows[(rows.get("confidence", 0.5) > 0.7) & (~rows["correct"])]) / max(total, 1), 3),
            "failed_error_catch": 0.25,
            "justified_not_fixed": 0.25,
            "correct_epistemic_state": round(correct_count / max(total, 1), 3),
        }

        model_id = rows["model_id"].iloc[0] if "model_id" in rows.columns else "unknown"
        ts = rows["timestamp"].iloc[0] if "timestamp" in rows.columns else datetime.now()

        verdict = _generate_verdict(metacog_index, model_id)

        return {
            "metacog_index": round(metacog_index, 1),
            "sub_scores": sub_scores,
            "bin_data": bin_data,
            "ece": ece,
            "brier": brier,
            "failure_taxonomy": taxonomy,
            "verdict": verdict,
            "model_id": model_id,
            "timestamp": str(ts),
            "task_results": task_results,
        }
    except Exception as e:
        st.warning(f"Database temporarily unavailable: {e}")
        return {}


@st.cache_data(ttl=10)
def load_run_history() -> list:
    """Query DuckDB for recent run IDs."""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        result = conn.execute(
            "SELECT DISTINCT run_id FROM results ORDER BY run_id DESC LIMIT 5"
        ).fetchall()
        conn.close()
        return [r[0] for r in result]
    except Exception as e:
        st.warning(f"Database temporarily unavailable: {e}")
        return []


def _compute_bin_data(df, n_bins: int = 10) -> list:
    """Compute calibration bin data from result rows."""
    if "confidence" not in df.columns or "correct" not in df.columns:
        return []
    bins = []
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        mid = (lo + hi) / 2
        mask = (df["confidence"] >= lo) & (df["confidence"] < hi)
        subset = df[mask]
        if len(subset) > 0:
            bins.append({
                "bin_mid": mid,
                "accuracy": float(subset["correct"].mean()),
                "count": int(len(subset)),
            })
    return bins


def _generate_verdict(index: float, model_id: str) -> str:
    idx = round(index)
    if idx >= 80:
        return f"Model {model_id} demonstrates strong metacognitive awareness ({idx}/100)."
    elif idx >= 60:
        return f"Model {model_id} shows moderate metacognitive ability ({idx}/100) — room for improvement."
    elif idx >= 40:
        return f"Model {model_id} has significant metacognitive gaps ({idx}/100) — caution advised."
    else:
        return f"Model {model_id} fails metacognitive evaluation ({idx}/100) — not safe for high-stakes use."


# ─── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:8px 0 4px 0;">
        <span style="font-size:36px;">🧠</span>
        <h2 style="margin:4px 0 0 0;font-weight:700;color:#1a1a2e;">MetaCog Benchmark</h2>
        <p style="color:#888;font-size:13px;margin:2px 0 0 0;">Metacognition Evaluation Framework</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("#### Run Configuration")
    model_id = st.text_input("Model ID", value="gpt-4o", key="model_id_input")
    focus_area = st.selectbox("Focus Area",
                               ["All", "calibration", "error_detection", "correction", "certainty"])
    difficulty = st.selectbox("Difficulty", ["All", "easy", "medium", "hard"])
    task_count = st.number_input("Task Count", min_value=10, max_value=200, value=20, step=5)

    col_a, col_b = st.columns(2)
    with col_a:
        start_btn = st.button("▶ Start", type="primary", width="stretch")
    with col_b:
        refresh_btn = st.button("↺ Refresh", width="stretch")

    if start_btn:
        st.session_state["auto_refresh"] = True
        st.toast("Evaluation started!", icon="🚀")

    if refresh_btn:
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("#### Run History")
    history = load_run_history()
    if history:
        selected_run = st.selectbox("View previous run", history, key="run_select")
        st.session_state["current_run_id"] = selected_run
    else:
        st.caption("No runs recorded yet.")
        st.session_state.setdefault("current_run_id", "demo-run-001")

# ─── Load Data ──────────────────────────────────────────────
run_id = st.session_state.get("current_run_id", "demo-run-001")
data = load_run_results(run_id)

# ─── Apply Sidebar Filters ──────────────────────────────────
def apply_filters(data, model_id, focus_area, difficulty, task_count):
    """Filter data based on sidebar selections."""
    if not data or not data.get("task_results"):
        return data

    filtered_results = data["task_results"].copy()

    # Filter by focus area (normalize storage -> display key)
    if focus_area != "All":
        filtered_results = [
            t for t in filtered_results
            if _normalize_focus_area(t.get("focus_area")) == focus_area
        ]

    # Filter by difficulty only if data contains the key
    if difficulty != "All":
        has_difficulty = any("difficulty" in t for t in filtered_results)
        if has_difficulty:
            filtered_results = [t for t in filtered_results if t.get("difficulty") == difficulty]

    # Limit by task count
    filtered_results = filtered_results[:int(task_count)]

    # Create filtered data copy
    filtered_data = data.copy()
    filtered_data["task_results"] = filtered_results

    # Recalculate sub_scores to reflect filtered data if focus_area is selected
    if focus_area != "All" and filtered_results:
        correct_count = sum(1 for t in filtered_results if t.get("correct", False))
        total_count = len(filtered_results)
        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

        filtered_data["sub_scores"] = data["sub_scores"].copy()
        filtered_data["sub_scores"][focus_area]["score"] = round(accuracy, 1)
        filtered_data["sub_scores"][focus_area]["n_tasks"] = total_count

    return filtered_data

data = apply_filters(data, model_id, focus_area, difficulty, task_count)

# ─── DEMO fallback data ────────────────────────────────────
if not data:
    data = {
        "metacog_index": 66.5,
        "sub_scores": {
            "calibration": {"score": 72.0, "n_tasks": 20, "dominant_failure": "well_calibrated",
                            "confidence_interval": (0.65, 0.79)},
            "error_detection": {"score": 61.0, "n_tasks": 20, "dominant_failure": "failed_error_catch",
                                "confidence_interval": (0.54, 0.68)},
            "correction": {"score": 58.0, "n_tasks": 20, "dominant_failure": "justified_not_fixed",
                           "confidence_interval": (0.50, 0.66)},
            "certainty": {"score": 75.0, "n_tasks": 20, "dominant_failure": "accurate_epistemic_self_assessment",
                          "confidence_interval": (0.68, 0.82)},
        },
        "bin_data": [
            {"bin_mid": 0.05, "accuracy": 0.10, "count": 5},
            {"bin_mid": 0.15, "accuracy": 0.18, "count": 8},
            {"bin_mid": 0.25, "accuracy": 0.30, "count": 12},
            {"bin_mid": 0.35, "accuracy": 0.28, "count": 10},
            {"bin_mid": 0.45, "accuracy": 0.42, "count": 15},
            {"bin_mid": 0.55, "accuracy": 0.58, "count": 18},
            {"bin_mid": 0.65, "accuracy": 0.60, "count": 22},
            {"bin_mid": 0.75, "accuracy": 0.72, "count": 25},
            {"bin_mid": 0.85, "accuracy": 0.80, "count": 20},
            {"bin_mid": 0.95, "accuracy": 0.88, "count": 15},
        ],
        "ece": 0.0623,
        "brier": 0.1840,
        "failure_taxonomy": {
            "overconfident_wrong": 0.30,
            "failed_error_catch": 0.25,
            "justified_not_fixed": 0.20,
            "correct_epistemic_state": 0.25,
        },
        "verdict": f"Model gpt-4o shows moderate metacognitive ability (67/100) — room for improvement.",
        "model_id": model_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "task_results": [
            {"task_id": f"calib_{str(i).zfill(3)}", "focus_area": "calibration", "difficulty": "medium",
             "confidence": 0.75 + (i % 5) * 0.05, "correct": i % 3 != 0,
             "anomaly_codes": ["SYCOPHANTIC_MILD"] if i % 7 == 0 else [], "gap": 0.15}
            for i in range(1, 21)
        ],
    }


# ═══════════════════════════════════════════════════════════
# PANEL 2 — MetaCog Index (top row)
# ═══════════════════════════════════════════════════════════
st.markdown("")
col1, col2, col3 = st.columns([0.40, 0.35, 0.25])

with col1:
    gauge_fig = render_metacog_gauge(data["metacog_index"], data["model_id"])
    st.plotly_chart(gauge_fig, width='stretch', key="gauge")

with col2:
    st.markdown("")
    scores = data["sub_scores"]
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Calibration",
                   f"{scores['calibration']['score']:.1f}",
                   delta=None)
        st.metric("Correction",
                   f"{scores['correction']['score']:.1f}",
                   delta=None)
    with m2:
        st.metric("Error Detection",
                   f"{scores['error_detection']['score']:.1f}",
                   delta=None)
        st.metric("Certainty",
                   f"{scores['certainty']['score']:.1f}",
                   delta=None)

with col3:
    render_verdict_card(
        verdict=data["verdict"],
        index=data["metacog_index"],
        model_id=data["model_id"],
        timestamp=data["timestamp"],
    )

# ═══════════════════════════════════════════════════════════
# PANEL 3 — Calibration Curve + Focus Breakdown
# ═══════════════════════════════════════════════════════════
st.divider()
left_col, right_col = st.columns(2)

with left_col:
    if data["bin_data"]:
        cal_fig = render_calibration_curve(data["bin_data"], data["ece"], data["brier"])
        st.plotly_chart(cal_fig, width='stretch', key="cal_curve")
    else:
        st.info("No calibration data available yet.")

with right_col:
    focus_fig = render_focus_breakdown(data["sub_scores"], data["metacog_index"])
    st.plotly_chart(focus_fig, width='stretch', key="focus_bars")

# ═══════════════════════════════════════════════════════════
# PANEL 4 — Live Task Feed
# ═══════════════════════════════════════════════════════════
st.divider()
feed_header = st.columns([0.7, 0.15, 0.15])
with feed_header[0]:
    st.markdown("### 📡 Live Evaluation Feed")
    st.caption("Most recent tasks — auto-refreshes every 3 seconds")
with feed_header[2]:
    if st.button("⏸ Pause feed"):
        st.session_state["paused"] = not st.session_state.get("paused", False)
        label = "Paused" if st.session_state["paused"] else "Resumed"
        st.toast(f"Feed {label}", icon="⏸" if st.session_state["paused"] else "▶")

feed_container = st.empty()
with feed_container.container():
    render_live_feed(data.get("task_results", []))

# ═══════════════════════════════════════════════════════════
# PANEL 5 — Failure Taxonomy (collapsible)
# ═══════════════════════════════════════════════════════════
st.divider()
with st.expander("▼ Failure Taxonomy", expanded=False):
    taxonomy = data.get("failure_taxonomy", {})
    if taxonomy:
        labels = {
            "overconfident_wrong": ("Overconfident Wrong", "#e74c3c"),
            "failed_error_catch": ("Failed Error Catch", "#f39c12"),
            "justified_not_fixed": ("Justified Not Fixed", "#e67e22"),
            "correct_epistemic_state": ("Correct Epistemic State", "#2ecc71"),
        }

        fig_tax = go.Figure()
        cumulative = 0
        for key, (label, colour) in labels.items():
            val = taxonomy.get(key, 0.0)
            pct = val * 100
            fig_tax.add_trace(go.Bar(
                y=["Failure Distribution"],
                x=[pct],
                name=f"{label} ({pct:.0f}%)",
                orientation="h",
                marker=dict(color=colour, line=dict(width=0)),
                text=f"{pct:.0f}%",
                textposition="inside",
                textfont=dict(color="white", size=12, family="Inter"),
                hovertemplate=f"{label}: {pct:.1f}%<extra></extra>",
            ))
            cumulative += pct

        fig_tax.update_layout(
            barmode="stack",
            template="plotly_white",
            height=90,
            margin=dict(l=0, r=0, t=10, b=10),
            xaxis=dict(visible=False, range=[0, 100]),
            yaxis=dict(visible=False),
            legend=dict(
                orientation="h", yanchor="top", y=-0.3,
                xanchor="center", x=0.5, font=dict(size=11),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_tax, width='stretch', key="taxonomy")

        # Dominant failure explanation
        dominant = max(taxonomy, key=taxonomy.get)
        dominant_label = labels.get(dominant, (dominant, "#888"))[0]
        st.caption(
            f"**Dominant failure mode:** {dominant_label} "
            f"({taxonomy[dominant]*100:.0f}% of evaluated tasks)"
        )
    else:
        st.info("No failure taxonomy data available.")

# ─── Auto-Refresh ───────────────────────────────────────────
if st.session_state.get("auto_refresh", True):
    if not st.session_state.get("paused", False):
        time.sleep(3)
        st.rerun()
