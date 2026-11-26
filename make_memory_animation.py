"""自作メモリー回路の検出領域をSVG・PNG・GIFとして保存する。

python make_memory_animation.py
python make_memory_animation.py --project /Users/hiroseminagi/Documents/stim

必要: stim, Pillow, matplotlib, rsvg-convert
回路のファイルは変更しない。
"""

import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

import stim
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as DrawingPath
from matplotlib.textpath import TextPath
from PIL import Image, ImageDraw, ImageFont


def drawing_coordinates(circuit):
    """描画用コピーでyを反転し、layoutの「上が+y」をSVGでも保つ。

    座標注釈のみ変更する。ゲート・測定順序・測定記録参照は変えない。
    現在のBuilderはREPEATを使わない、展開済みの回路を返す。
    """
    result = stim.Circuit()
    for instruction in circuit:
        if instruction.name in {"QUBIT_COORDS", "DETECTOR"}:
            coords = instruction.gate_args_copy()
            if len(coords) >= 2:
                coords[1] = -coords[1]
            result.append(instruction.name, instruction.targets_copy(), coords)
        else:
            result.append(instruction)
    return result


@lru_cache(maxsize=None)
def gate_outline(label, size):
    """文字の輪郭と、その見た目の中心を求める。"""
    shape = TextPath((0, 0), label, size=size,
                     prop=FontProperties(family="DejaVu Sans Mono"))
    bounds = shape.get_extents()
    parts = []
    commands = {
        DrawingPath.MOVETO: "M", DrawingPath.LINETO: "L",
        DrawingPath.CURVE3: "Q", DrawingPath.CURVE4: "C",
    }
    for points, code in shape.iter_segments(curves=True, simplify=False):
        if code == DrawingPath.CLOSEPOLY:
            parts.append("Z")
        else:
            parts.append(commands[code] + " ".join(f"{v:.5f}" for v in points))
    return " ".join(parts), (bounds.x0 + bounds.x1) / 2, (bounds.y0 + bounds.y1) / 2


def prepare_svg(svg):
    """白背景を付け、R/H/Mの輪郭をゲートの中心に配置する。

    SVG表示ソフトごとのdominant-baselineの違いを避けるため、
    ゲート文字のみテキストから輪郭パスへ置換する。
    """
    def replace_gate(match):
        element = ET.fromstring(match.group(0))
        label = element.text
        if label not in {"R", "H", "M"}:
            return match.group(0)
        if element.get("dominant-baseline") != "central":
            return match.group(0)
        x, y = float(element.get("x")), float(element.get("y"))
        size = float(element.get("font-size"))
        outline, center_x, center_y = gate_outline(label, size)
        color = element.get("fill", "black")
        return (f'<path aria-label="{label}" fill="{color}" '
                f'transform="translate({x-center_x:.5f} {y+center_y:.5f}) scale(1 -1)" '
                f'd="{outline}"/>')

    svg = re.sub(r"<text\b[^>]*>[^<]*</text>", replace_gate, svg)
    return svg.replace(">", '><rect width="100%" height="100%" fill="white"/>', 1)


def save_gif(frames, path):
    """全コマ共通の色表を使い、透過なしで保存する。

    Pillowの自動最適化による透過色・コマ別色表を避け、
    Finder等でも黒い文字や丸が白抜けしないようにする。
    """
    samples = Image.new("RGB", (160, 172 * len(frames)), "white")
    for i, frame in enumerate(frames):
        samples.paste(frame.resize((160, 172)), (0, i * 172))
    adaptive = samples.quantize(colors=254)
    colors = [(255, 255, 255), (0, 0, 0)]
    raw = adaptive.getpalette()
    for i in range(0, len(raw), 3):
        color = tuple(raw[i:i+3])
        if color not in colors:
            colors.append(color)
    colors = colors[:256]
    colors.extend([(255, 255, 255)] * (256 - len(colors)))
    palette = Image.new("P", (1, 1))
    palette.putpalette([value for color in colors for value in color])
    indexed = []
    for frame in frames:
        converted = frame.quantize(palette=palette, dither=Image.Dither.NONE)
        converted.info.clear()
        indexed.append(converted)
    indexed[0].save(path, save_all=True, append_images=indexed[1:],
                    duration=1000, loop=0, disposal=2,
                    optimize=False, background=0)


def save_sheet(frames, path):
    rows = (len(frames) + 3) // 4
    sheet = Image.new("RGB", (1600, 430 * rows), "white")
    for index, frame in enumerate(frames):
        sheet.paste(frame.resize((400, 430), Image.Resampling.LANCZOS),
                    ((index % 4) * 400, (index // 4) * 430))
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "memory_animation")
    args = parser.parse_args()
    converter = shutil.which("rsvg-convert")
    if converter is None:
        raise SystemExit("rsvg-convert が見つかりません。SVGからPNGへの変換に必要です。")
    sys.path.insert(0, str(args.project.resolve()))
    from memory import MemoryCircuitBuilder

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    full_dir = out / "full_sequence"
    full_dir.mkdir(exist_ok=True)
    circuit = MemoryCircuitBuilder(distance=5, rounds=3).build()
    circuit.detector_error_model()
    circuit = drawing_coordinates(circuit)

    names = ["Reset ancillas", "H on X ancillas", "CNOT layer 1",
             "CNOT layer 2", "CNOT layer 3", "CNOT layer 4",
             "H on X ancillas", "Measure ancillas"]
    # 現在のBuilderでは初期化1区間 + 3ラウンド x 8区間 + 最終読み出し1区間。
    titles = ["Initialize data in |0>"]
    for round_number in range(1, 4):
        titles.extend(f"Round {round_number} / 3 | Step {i} / 8: {name}"
                      for i, name in enumerate(names, start=1))
    titles.append("Final Z readout of data")
    if circuit.num_ticks != len(titles):
        raise ValueError("TICK構成が変わっています。表示する区間とタイトルを更新してください。")

    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 23)
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    frames = []
    for tick, title in enumerate(titles):
        svg = prepare_svg(str(circuit.diagram(
            "detslice-with-ops-svg", tick=range(tick, tick + 1)
        )))
        svg_path = full_dir / f"step_{tick+1:02}.svg"
        png_path = full_dir / f"step_{tick+1:02}.png"
        svg_path.write_text(svg, encoding="utf-8")
        subprocess.run([converter, "-w", "760", "-o", str(png_path), str(svg_path)],
                       check=True)
        with Image.open(png_path) as source:
            diagram = source.convert("RGB")
        # 大きさが異なる場合にも、説明文の領域からはみ出さないようにする。
        diagram.thumbnail((760, 750), Image.Resampling.LANCZOS)
        frame = Image.new("RGB", (800, 860), "white")
        draw = ImageDraw.Draw(frame)
        draw.text((20, 14), title, font=font, fill="black")
        draw.text((20, 47), "Detector regions after the displayed operations",
                  font=small, fill="#555555")
        frame.paste(diagram, ((800-diagram.width)//2, 75))
        draw.text((22, 833), "X: red   Y: green   Z: blue   |   No injected noise",
                  font=small, fill="#444444")
        frames.append(frame)
        # 従来の中央ラウンドの個別SVG/PNGも更新する。
        if 9 <= tick < 17:
            shutil.copyfile(svg_path, out / f"step_{tick-8:02}.svg")
            shutil.copyfile(png_path, out / f"step_{tick-8:02}.png")

    # 0番フレームはデータ初期化を実行した直後。
    save_gif(frames, out / "memory_from_initialization.gif")
    # Finderが古いプレビューをキャッシュしている場合に開き直すための別名。
    shutil.copyfile(out / "memory_from_initialization.gif",
                    out / "memory_from_initialization_opaque.gif")
    save_gif(frames[:9], out / "memory_first_round.gif")
    save_gif(frames[9:17], out / "memory_cycle.gif")
    save_sheet(frames[:9], out / "memory_first_round_steps.png")
    save_sheet(frames[9:17], out / "memory_steps.png")
    overview = prepare_svg(str(circuit.diagram(
        "detslice-with-ops-svg", tick=range(9, 17), rows=2
    )))
    (out / "memory_round.svg").write_text(overview, encoding="utf-8")
    frames[0].save(out / "initialization.png")
    print(f"保存先: {out}")
    print("memory_from_initialization.gif: 初期化から最終読み出しまで26コマ")
    print("memory_first_round.gif: 初期化から最初のラウンド終了まで9コマ")
    print("memory_cycle.gif: 中央のラウンド8コマ")


if __name__ == "__main__":
    main()
