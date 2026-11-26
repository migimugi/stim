import matplotlib.pyplot as plt
from layout import SurfaceCodeLayout
from plot_surface_code import draw_layout
from memory import MemoryCircuitBuilder

from pathlib import Path
import webbrowser

#layout = SurfaceCodeLayout(distance=5)
#fig, ax = draw_layout(layout)
#plt.show()



builder = MemoryCircuitBuilder(distance=5, rounds=2)
circuit = builder.build()

diagram = builder.op.circuit.diagram("timeslice-svg")

svg = str(diagram)

# 最初の <svg ...> の直後に、白い背景を追加する
svg = svg.replace(
    ">",
    '><rect width="100%" height="100%" fill="white"/>',
    1,
)

path = Path(__file__).resolve().with_name("memory_timeslice.svg")
path.write_text(svg, encoding="utf-8")
