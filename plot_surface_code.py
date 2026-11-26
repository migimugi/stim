"""Draw the user's SurfaceCodeLayout without generating a Stim circuit."""

import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon


def draw_layout(layout, show_indices=True):
    """Return (fig, ax). Red = X checks; blue = Z checks.

    Check supports and ancilla positions are read from the supplied layout.
    Four-data checks are squares; two-data boundary checks are triangles.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = {"X": "#e75a60", "Z": "#478ed8"}
    for kind, checks in (("X", layout.x_check), ("Z", layout.z_check)):
        for ancilla, support in checks.items():
            vertices = [layout.location.coord_at(q) for q in support]
            if len(vertices) == 2:
                vertices.append(layout.location.coord_at(ancilla))
            elif len(vertices) != 4:
                raise ValueError("This drawing supports checks of weight 2 or 4.")
            cx = sum(p[0] for p in vertices) / len(vertices)
            cy = sum(p[1] for p in vertices) / len(vertices)
            vertices.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
            ax.add_patch(Polygon(vertices, closed=True,
                                 facecolor=colors[kind], alpha=0.38,
                                 edgecolor=colors[kind], linewidth=1.8))

    for qubits, face, text_color, size in (
        (layout.data_qubits, "white", "#182332", 460),
        (layout.ancilla_qubits, "#182332", "white", 380),
    ):
        points = [layout.location.coord_at(q) for q in qubits]
        ax.scatter([p[0] for p in points], [p[1] for p in points],
                   s=size, facecolors=face, edgecolors="#182332",
                   linewidths=1.5, zorder=3)
        if show_indices:
            for q, (x, y) in zip(qubits, points):
                ax.text(x, y, str(q), ha="center", va="center",
                        fontsize=10, color=text_color, zorder=4)

    legend = [
        Patch(facecolor=colors[k], alpha=0.65, label=f"{k} stabilizer")
        for k in ("X", "Z")
    ] + [
        Line2D([], [], linestyle="", marker="o", markersize=10,
               markerfacecolor=face, markeredgecolor="#182332", label=label)
        for face, label in (("white", "Data qubit"), ("#182332", "Ancilla"))
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=2, frameon=False, fontsize=11)
    end = 2 * (layout.distance - 1)
    ax.set_xlim(-1.6, end + 1.6)
    ax.set_ylim(-1.6, end + 1.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Rotated surface code | distance {layout.distance}",
                 fontsize=17, pad=20, color="#182332")
    fig.text(0.5, 0.025,
             "Numbers are Stim qubit indices. Tiles show stabilizer supports.",
             ha="center", fontsize=10, color="#536173")
    fig.subplots_adjust(top=0.91, bottom=0.15, left=0.05, right=0.95)
    return fig, ax
