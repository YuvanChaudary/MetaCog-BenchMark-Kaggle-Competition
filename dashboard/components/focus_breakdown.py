"""
Plotly horizontal bar chart for focus area score breakdown.
"""
import plotly.graph_objects as go


def render_focus_breakdown(scores: dict, metacog_index: float) -> go.Figure:
    """
    Returns a Plotly horizontal bar chart of focus area scores.
    scores: dict[str, dict] with keys 'score', 'dominant_failure'.
    """
    areas = []
    values = []
    colours = []
    failures = []

    colour_map = {
        "high": "#2ecc71",
        "mid": "#f39c12",
        "low": "#e74c3c",
    }

    for area_name, data in scores.items():
        score = data.get("score", 0) if isinstance(data, dict) else getattr(data, "score", 0)
        failure = data.get("dominant_failure", "") if isinstance(data, dict) else getattr(data, "dominant_failure", "")

        display_name = area_name.replace("_", " ").title()
        areas.append(display_name)
        values.append(score)
        failures.append(failure)

        if score > 70:
            colours.append(colour_map["high"])
        elif score >= 50:
            colours.append(colour_map["mid"])
        else:
            colours.append(colour_map["low"])

    # Reverse for top-down reading in horizontal bar chart
    areas.reverse()
    values.reverse()
    colours.reverse()
    failures.reverse()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=areas,
        x=values,
        orientation="h",
        marker=dict(
            color=colours,
            line=dict(width=1, color="#fff"),
            cornerradius=4,
        ),
        text=[f"  {v:.1f}" for v in values],
        textposition="inside",
        textfont=dict(color="white", size=13, family="Inter"),
        hovertemplate="%{y}: %{x:.1f}/100<br><i>%{customdata}</i><extra></extra>",
        customdata=failures,
    ))

    # Vertical reference line at metacog_index
    fig.add_vline(
        x=metacog_index,
        line_dash="dot",
        line_color="#2d3436",
        line_width=2,
        annotation_text=f"Overall: {metacog_index:.1f}",
        annotation_position="top",
        annotation_font=dict(size=11, color="#2d3436"),
    )

    fig.update_layout(
        template="plotly_white",
        title=dict(text="Focus Area Scores", font=dict(size=16)),
        xaxis=dict(title="Score", range=[0, 105], dtick=20),
        yaxis=dict(title=""),
        height=380,
        margin=dict(l=120, r=30, t=50, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.35,
    )
    return fig
