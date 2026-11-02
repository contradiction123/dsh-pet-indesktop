"""将已批准的 3×2 原生 RGBA 动作图集拆成角色包（需要已有 Pillow）。

只做确定性的分格、登记、固定画布装配与无损编码，不抠图或补画。
仅为已确认的站立待机固定双脚；走路保留一整组的固定原点，不能逐帧贴地。
源图始终保留在角色的 sources/ 下，便于回溯与重新装配。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pet.character_pack import NATIVE_ENCODER  # noqa: E402
from pet.pack_download import frame_digest  # noqa: E402


def read_cells(root: Path, source: str) -> list[Image.Image]:
    """优先读取配对的十二姿态修订图，缺一张时拒收，防止混用两代素材。"""
    revised = [root / "sources" / f"{source}-{part}-v2.png" for part in ("a", "b")]
    if any(path.exists() for path in revised):
        if not all(path.is_file() for path in revised):
            raise ValueError(f"{source}: v2 动作必须包含 a/b 两张图集")
        paths = revised
    else:
        paths = [root / "sources" / f"{source}.png"]
    cells = []
    for path in paths:
        with Image.open(path) as original:
            sheet = original.convert("RGBA")
        if sheet.size != (1536, 1024):
            raise ValueError(f"{path.name}: 需要 1536×1024 图集，实际 {sheet.size}")
        for i in range(6):
            x, y = (i % 3) * 512, (i // 3) * 512
            cells.append(sheet.crop((x, y, x + 512, y + 512)))
    return cells


def foot_anchor(cell: Image.Image) -> tuple[float, int, int]:
    """本角色站立素材的双鞋底锚点和轮廓高度，不用于跳跃/飞行动作。

    只测已检查过的鞋底最后十三行实心像素，避免头发摆动改变整图包围框的
    横向中心。输出在构建时使用，运行时不逐帧扫描像素或改变窗口位置。
    """
    solid = cell.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    bounds = solid.getbbox()
    if bounds is None:
        raise ValueError("动作帧为空，无法登记脚底")
    bottom = bounds[3] - 1
    band = solid.crop((0, max(0, bottom - 12), solid.width, bottom + 1))
    xs = sorted(index % band.width for index, value in enumerate(band.tobytes()) if value)
    if not xs:
        raise ValueError("动作帧没有可识别的鞋底")
    middle = len(xs) // 2
    center = (xs[middle] + xs[(len(xs) - 1) // 2]) / 2
    return center, bottom, bounds[3] - bounds[1]


def registered_cells(cells: list[Image.Image], reference: Image.Image,
                     *, pin_feet: bool) -> list[Image.Image]:
    """全动作共用一次缩放；待机固定脚，走路只登记首帧并沿用同一原点。"""
    target_x, target_y, target_height = foot_anchor(reference)
    _, _, height = foot_anchor(cells[0])
    factor = target_height / height
    if not 0.85 <= factor <= 1.15:
        raise ValueError("动作与待机的比例差异过大，需要重新制作素材")
    scaled = [cell.resize((round(cell.width * factor), round(cell.height * factor)),
                          Image.Resampling.LANCZOS) for cell in cells]
    origin_x, origin_y, _ = foot_anchor(scaled[0])
    result = []
    for cell in scaled:
        x, y, _ = foot_anchor(cell) if pin_feet else (origin_x, origin_y, 0)
        frame = Image.new("RGBA", (512, 512))
        frame.alpha_composite(cell, (round(target_x - x), round(target_y - y)))
        result.append(frame)
    return result


def assemble(root: Path) -> None:
    """按固定原点拆帧；元数据只在全部帧写好后发布。"""
    canvas = (1280, 720)
    recipes = [
        ("blink", "眨眼呼吸", "idle", [1500, 70, 110, 70, 250, 700]),
        ("tilt", "歪头张望", "idle", [800, 100, 100, 100, 100, 300,
                                            200, 100, 100, 100, 100, 800]),
        ("sway", "轻晃铃铛", "idle", [700, 140, 180, 140, 180, 700]),
        ("yawn", "困倦哈欠", "idle", [900, 90, 90, 100, 120, 300,
                                            220, 120, 100, 90, 90, 900]),
        ("walk", "轻步漫游", "move", [70] * 12),
        ("wave", "挥手问好", "click", [300, 150, 180, 180, 180, 700]),
        ("blink", "拖拽待机", "drag", [1500, 70, 110, 70, 250, 700]),
        ("blink", "转向过渡", "turn", [180]),
    ]
    base = read_cells(root, "blink")[0]
    base_x, base_y, _ = foot_anchor(base)
    neutral = Image.new("RGBA", (512, 512))
    # 1280 画布的中轴为 x=640，脚底为 y=660；对应装配格内 (256, 472)。
    neutral.alpha_composite(base, (round(256 - base_x), 472 - base_y))
    clips = []
    for source, name, category, durations in recipes:
        cells = read_cells(root, source)
        if len(durations) > len(cells):
            raise ValueError(f"{source}: 需要 {len(durations)} 帧，素材只有 {len(cells)} 帧")
        cells = registered_cells(
            cells, neutral, pin_feet=source in {"blink", "tilt", "sway", "yawn", "wave"})
        if category in {"idle", "drag", "turn"}:
            # 共用完全相同的中性姿态，切动作和首尾续播不会换脸/改变落脚高度。
            cells[0] = neutral.copy()
            cells[-1] = neutral.copy()
        relative = Path("animations") / category / source
        destination = root / relative
        destination.mkdir(parents=True, exist_ok=True)
        total_bytes = 0
        for i in range(len(durations)):
            cell = cells[i]
            if source == "walk":
                # 项目默认素材朝左，朝右时由现有渲染层镜像。
                cell = ImageOps.mirror(cell)
            frame = Image.new("RGBA", canvas)
            frame.alpha_composite(cell, (384, 188))
            path = destination / f"f_{i + 1:04d}.webp"
            frame.save(path, "WEBP", lossless=True, exact=True, method=2)
            total_bytes += path.stat().st_size
        # 修订的动作可增减帧数，只清理由本装配器编号生成的多余帧。
        for previous in destination.glob("f_*.webp"):
            if previous.name not in {f"f_{i + 1:04d}.webp" for i in range(len(durations))}:
                previous.unlink()
        content_sha = frame_digest(destination)
        metadata = {"frames": len(durations), "fps": 12.0, "canvas": canvas,
                    "durations_ms": durations, "encoder": NATIVE_ENCODER,
                    "content_sha": content_sha}
        (destination / "meta.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        clips.append({"name": name, "category": category, "dir": relative.as_posix(),
                      "frames": len(durations), "key_every": 1, "part": "core",
                      "content_sha": content_sha, "bytes": total_bytes})
    index = {"schema": 1, "id": "sleepbell", "name": "睡铃雪影娃娃",
             "canvas": canvas, "fps": 12.0, "pipeline": "native-rgba-v1",
             "format": "lossless-frame-v1", "parts": ["core"], "clips": clips}
    (root / "character.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    # 固定身体框按所有姿势的公共画布给出，不把动态头饰作为落地锚点。
    manifest = {"name": "睡铃雪影娃娃", "body_box": [448, 208, 832, 660],
                "head_box": [480, 208, 800, 450],
                "no_mirror": [clip["name"] for clip in clips if clip["category"] != "move"]}
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "text_clips.json").write_text(
        json.dumps({"no_mirror": manifest["no_mirror"]}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (root / "move_strides.json").write_text(
        json.dumps({"轻步漫游": 80}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="含 sources/<动作>.png 的角色目录")
    assemble(parser.parse_args().root)
