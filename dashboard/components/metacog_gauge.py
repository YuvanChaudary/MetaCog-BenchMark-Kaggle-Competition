"""
Plotly gauge component for MetaCog Index display.
"""
import plotly.graph_objects as go


def render_metacog_gauge(index: float, model_id: str) -> go.Figure:
    """
    Returns a Plotly circular gauge figure showing the MetaCog Index.
    Colour zones: 0-40 red, 40-70 amber, 70-100 green.
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=index,
        number={"font": {"size": 52, "color": "#1a1a2e"}, "suffix": ""},
        title={"text": f"MetaCog Index<br><span style='font-size:13px;color:#666'>{model_id}</span>",
               "font": {"size": 18}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 2,
                "tickcolor": "#ccc",
                "dtick": 10,
                "tickfont": {"size": 11, "color": "#888"},
            },
            "bar": {"color": "#2d3436", "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "rgba(231,76,60,0.25)"},
                {"range": [40, 70], "color": "rgba(243,156,18,0.20)"},
                {"range": [70, 100], "color": "rgba(46,204,113,0.20)"},
            ],
            "threshold": {
                "line": {"color": "#e74c3c" if index < 40 else "#f39c12" if index < 70 else "#2ecc71",
                         "width": 4},
                "thickness": 0.85,
                "value": index,
            },
        },
    ))

    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=30, r=30, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
