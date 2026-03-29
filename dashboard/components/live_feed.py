"""
Live task feed component — scrolling table of recent evaluation results.
"""
import streamlit as st
import pandas as pd


# Badge colour map for focus areas
_FOCUS_COLOURS = {
    "calibration": ("#9b59b6", "#f3e5f5"),
    "error_detection": ("#00897b", "#e0f2f1"),
    "correction": ("#e17055", "#fbe9e7"),
    "certainty": ("#2980b9", "#e3f2fd"),
}


def _badge(text: str, fg: str, bg: str) -> str:
    return (
        f'<span style="background:{bg};color:{fg};'
        f'padding:3px 8px;border-radius:4px;font-size:12px;'
        f'font-weight:600;">{text}</span>'
    )


def render_live_feed(task_results: list[dict]) -> None:
    """
    Renders a styled table of the most recent evaluation results.
    """
    if not task_results:
        st.info("No evaluation results yet. Start a run to see live feed.")
        return

    rows = []
    for r in task_results[-20:]:
        task_id = str(r.get("task_id", ""))[:8]
        focus = r.get("focus_area", "calibration")
        difficulty = r.get("difficulty", "easy")
        confidence = r.get("confidence", 0.0)
        correct = r.get("correct", False)
        anomaly_codes = r.get("anomaly_codes", [])
        gap = abs(confidence - (1.0 if correct else 0.0))

        fg, bg = _FOCUS_COLOURS.get(focus, ("#555", "#eee"))
        focus_badge = _badge(focus.replace("_", " "), fg, bg)

        correct_str = (
            '<span style="color:#2ecc71;font-weight:700;">✓</span>'
            if correct else
            '<span style="color:#e74c3c;font-weight:700;">✗</span>'
        )

        anomaly_str = ""
        if anomaly_codes:
            anomaly_str = _badge(", ".join(anomaly_codes[:2]), "#c0392b", "#fdecea")

        conf_pct = int(confidence * 100)
        conf_bar = (
            f'<div style="background:#eee;border-radius:4px;height:16px;width:100%;">'
            f'<div style="background:{"#2ecc71" if conf_pct > 70 else "#f39c12" if conf_pct > 40 else "#e74c3c"};'
            f'width:{conf_pct}%;height:100%;border-radius:4px;"></div></div>'
            f'<span style="font-size:11px;color:#666;">{conf_pct}%</span>'
        )

        rows.append({
            "Task ID": task_id,
            "Focus": focus_badge,
            "Difficulty": difficulty.capitalize(),
            "Confidence": conf_bar,
            "Correct": correct_str,
            "Anomaly": anomaly_str,
            "Gap": f"{gap:.2f}",
        })

    df = pd.DataFrame(rows)

    st.markdown(
        df.to_html(escape=False, index=False, classes="feed-table"),
        unsafe_allow_html=True,
    )

    # Inject minimal CSS for the table
    st.markdown("""
    <style>
    .feed-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .feed-table th {
        background: #f8f9fa;
        padding: 10px 12px;
        text-align: left;
        font-weight: 600;
        color: #555;
        border-bottom: 2px solid #eee;
    }
    .feed-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: middle;
    }
    .feed-table tr:hover td {
        background: #fafafa;
    }
    </style>
    """, unsafe_allow_html=True)
