"""
Verdict card component — renders coloured verdict text.
"""
import streamlit as st


def render_verdict_card(verdict: str,
                         index: float,
                         model_id: str,
                         timestamp: str) -> None:
    """
    Renders the MetaCog verdict as styled markdown.
    Colour: red if index < 40, amber if 40-70, green if > 70.
    """
    if index < 40:
        colour = "#e74c3c"
        bg = "rgba(231,76,60,0.08)"
        label = "CRITICAL"
    elif index < 70:
        colour = "#f39c12"
        bg = "rgba(243,156,18,0.08)"
        label = "MODERATE"
    else:
        colour = "#2ecc71"
        bg = "rgba(46,204,113,0.08)"
        label = "STRONG"

    st.markdown(f"""
    <div style="
        background: {bg};
        border-left: 4px solid {colour};
        border-radius: 8px;
        padding: 20px 18px;
        margin-top: 8px;
    ">
        <span style="
            display: inline-block;
            background: {colour};
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 4px;
            letter-spacing: 1px;
            margin-bottom: 10px;
        ">{label}</span>
        <p style="
            font-size: 15px;
            font-weight: 600;
            line-height: 1.5;
            margin: 8px 0 12px 0;
        ">{verdict}</p>
        <p style="
            font-size: 12px;
            opacity: 0.8;
            margin: 0;
        ">
            <b>{model_id}</b> &nbsp;·&nbsp; {timestamp}
        </p>
    </div>
    """, unsafe_allow_html=True)
