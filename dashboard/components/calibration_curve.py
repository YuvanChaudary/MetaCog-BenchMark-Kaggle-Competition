"""
Plotly calibration curve (reliability diagram) component.
"""
import plotly.graph_objects as go


def render_calibration_curve(bin_data: list[dict],
                              ece: float,
                              brier: float) -> go.Figure:
    """
    Returns a Plotly reliability diagram figure.
    bin_data: list of dicts with keys 'bin_mid', 'accuracy', 'count'.
    """
    fig = go.Figure()

    # Perfect calibration diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(dash="dash", color="#aaa", width=1.5),
        name="Perfect Calibration",
        showlegend=True,
    ))

    # Overconfident zone (above diagonal)
    fig.add_trace(go.Scatter(
        x=[0, 1, 1, 0],
        y=[0, 1, 0, 0],
        fill="toself",
        fillcolor="rgba(231,76,60,0.06)",
        line=dict(width=0),
        name="Overconfident Zone",
        showlegend=False,
        hoverinfo="skip",
    ))

    # Underconfident zone (below diagonal)
    fig.add_trace(go.Scatter(
        x=[0, 0, 1, 0],
        y=[0, 1, 1, 0],
        fill="toself",
        fillcolor="rgba(52,152,219,0.06)",
        line=dict(width=0),
        name="Underconfident Zone",
        showlegend=False,
        hoverinfo="skip",
    ))

    if bin_data:
        mids = [b.get("bin_mid", 0) for b in bin_data]
        accs = [b.get("accuracy", 0) for b in bin_data]
        counts = [b.get("count", 1) for b in bin_data]
        max_count = max(counts) if counts else 1

        # Scaled marker sizes (8–30)
        sizes = [max(8, int(30 * (c / max_count))) for c in counts]

        fig.add_trace(go.Scatter(
            x=mids,
            y=accs,
            mode="lines+markers",
            marker=dict(
                size=sizes,
                color="#3498db",
                line=dict(width=1.5, color="#2980b9"),
                opacity=0.85,
            ),
            line=dict(color="#3498db", width=2.5),
            name="Model Calibration",
            hovertemplate="Conf: %{x:.2f}<br>Acc: %{y:.2f}<br>n=%{text}<extra></extra>",
            text=[str(c) for c in counts],
        ))

    # ECE and Brier annotations
    fig.add_annotation(
        x=0.03, y=0.97, xref="paper", yref="paper",
        text=f"<b>ECE:</b> {ece:.4f}",
        showarrow=False, font=dict(size=13, color="#e74c3c"),
        align="left", bgcolor="rgba(255,255,255,0.8)",
        borderpad=4,
    )
    fig.add_annotation(
        x=0.03, y=0.90, xref="paper", yref="paper",
        text=f"<b>Brier:</b> {brier:.4f}",
        showarrow=False, font=dict(size=13, color="#8e44ad"),
        align="left", bgcolor="rgba(255,255,255,0.8)",
        borderpad=4,
    )

    fig.update_layout(
        template="plotly_white",
        title=dict(text="Reliability Diagram", font=dict(size=16)),
        xaxis=dict(title="Mean Predicted Confidence", range=[0, 1], dtick=0.1),
        yaxis=dict(title="Fraction Correct", range=[0, 1], dtick=0.1),
        height=380,
        margin=dict(l=50, r=20, t=50, b=50),
        legend=dict(x=0.60, y=0.12, font=dict(size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
