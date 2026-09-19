"""Generated application icons for the desktop shell and installer.

The icons are drawn in code rather than committed as binary assets. Two reasons:

  * one source of truth -- the tray icon, the window icon and the packaged
    installer all derive from the same drawing, so they cannot drift apart;
  * no binary blobs in the repository for something this simple.

The motif is a production pipeline: three connected nodes feeding a fourth, on a
dark plinth. That is what this tool is -- a prompt goes in one end and a playable
vertical slice comes out the other -- and it stays legible at 16px, which a more
literal illustration would not.

Note: the name of the test game this tool is pointed at (Beyond the Fog) is
deliberately *not* referenced here. That game is an output of the pipeline, not
the identity of the tool, and branding the tool after its own test subject would
be confusing the moment a different target is used.

All sizes are derived from one master render, so a change to ``draw_pipeline``
shows up everywhere at once.
"""

from __future__ import annotations

from pathlib import Path

# Rendered at 4x the largest needed size, then downsampled. Pillow's LANCZOS
# filter needs the extra samples to keep the small sizes legible -- drawing a
# 16px icon directly produces mush.
MASTER_SIZE = 1024

ICON_SIZES = (16, 20, 24, 32, 48, 64, 128, 256)
ICO_SIZES = [(size, size) for size in ICON_SIZES]

# Palette: a dark slate plinth with a single accent for the active node, so the
# icon still reads when the taskbar renders it at 16px.
PLINTH_TOP = (44, 50, 68)
PLINTH_BOTTOM = (22, 26, 38)
NODE_IDLE = (122, 134, 162)
NODE_ACTIVE = (86, 196, 162)
LINK = (74, 86, 116)


def _require_pillow():
    try:
        # Imported here, not at module scope: Pillow is an optional extra, and
        # the launcher must stay importable without it installed.
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError as exc:  # pragma: no cover - dependency is declared in [desktop]
        raise RuntimeError(
            "Icon generation needs Pillow. Install the desktop extra: `pip install -e .[desktop]`"
        ) from exc
    return Image, ImageDraw, ImageFilter


def draw_pipeline(size: int = MASTER_SIZE) -> object:
    """Render the master icon and return a Pillow ``Image``.

    A three-stage pipeline: two idle nodes and one active node along a rail,
    with the finished artefact leaving to the right.
    """
    Image, ImageDraw, ImageFilter = _require_pillow()

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = size / 1024.0

    def px(value: float) -> float:
        return value * scale

    # Plinth: a vertical gradient, drawn as bands.
    band_height = max(1, int(px(8)))
    for top in range(0, size, band_height):
        ratio = top / size
        color = tuple(
            int(PLINTH_TOP[i] + (PLINTH_BOTTOM[i] - PLINTH_TOP[i]) * ratio) for i in range(3)
        )
        draw.rectangle([0, top, size, min(top + band_height, size)], fill=(*color, 255))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=px(220), fill=255)
    img.putalpha(mask)

    # Soft halo behind the active node, so the "work happening here" reads first.
    halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([px(330), px(300), px(700), px(670)], fill=(*NODE_ACTIVE, 105))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=px(72)))
    img = Image.alpha_composite(img, halo)

    draw = ImageDraw.Draw(img)

    # The rail the nodes sit on.
    rail_y = px(512)
    draw.rounded_rectangle(
        [px(150), rail_y - px(16), px(874), rail_y + px(16)],
        radius=px(16),
        fill=(*LINK, 255),
    )

    # Three pipeline nodes. The middle one is active.
    for index, centre_x in enumerate((280, 512, 744)):
        radius = px(96) if index != 1 else px(112)
        fill = NODE_ACTIVE if index == 1 else NODE_IDLE
        draw.ellipse(
            [
                px(centre_x) - radius,
                rail_y - radius,
                px(centre_x) + radius,
                rail_y + radius,
            ],
            fill=(*fill, 255),
        )

    # The artefact leaving the rail: a rounded square, the "slice" the pipeline
    # produces. Kept small and at the edge so it does not fight the nodes.
    draw.rounded_rectangle(
        [px(742), px(736), px(878), px(872)],
        radius=px(34),
        fill=(*NODE_ACTIVE, 255),
    )

    return img


def write_ico(path: Path, size: int = MASTER_SIZE) -> Path:
    """Write a multi-resolution ``.ico`` for Windows."""
    master = draw_pipeline(size)
    path.parent.mkdir(parents=True, exist_ok=True)
    master.save(path, format="ICO", sizes=ICO_SIZES)
    return path


def write_png(path: Path, *, size: int = 256, master_size: int = MASTER_SIZE) -> Path:
    """Write a single ``.png`` at ``size``, downsampled from the master render."""
    Image, _, _ = _require_pillow()
    master = draw_pipeline(master_size)
    resized = master.resize((size, size), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    resized.save(path, format="PNG")
    return path


def write_icon_set(directory: Path, *, master_size: int = MASTER_SIZE) -> dict[str, Path]:
    """Write the icon files the desktop shell and installers expect.

    Returns a mapping of logical name to written path so callers (and tests) do
    not have to reconstruct the filenames.
    """
    Image, _, _ = _require_pillow()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    master = draw_pipeline(master_size)
    written: dict[str, Path] = {}

    ico = directory / "fantasy-agent.ico"
    master.save(ico, format="ICO", sizes=ICO_SIZES)
    written["ico"] = ico

    for size in (256, 512):
        png = directory / f"fantasy-agent-{size}.png"
        master.resize((size, size), Image.LANCZOS).save(png, format="PNG")
        written[f"png_{size}"] = png

    # The window icon is a small png; keeping it separate makes it obvious which
    # file the shell loads at runtime.
    window_png = directory / "fantasy-agent-window.png"
    master.resize((128, 128), Image.LANCZOS).save(window_png, format="PNG")
    written["window_png"] = window_png

    return written


def default_icon_dir() -> Path:
    """Where generated icons live: alongside the studio app, gitignored."""
    return Path(__file__).resolve().parents[2] / "generated" / "desktop" / "icons"


def ensure_icons(directory: Path | None = None) -> dict[str, Path]:
    """Generate the icon set if it is missing, then return the paths.

    Called at startup rather than committing the files: regenerating is cheap
    and it keeps the drawing as the single source of truth.
    """
    target = Path(directory) if directory else default_icon_dir()
    ico = target / "fantasy-agent.ico"
    if ico.exists() and (target / "fantasy-agent-window.png").exists():
        return {
            "ico": ico,
            "window_png": target / "fantasy-agent-window.png",
            "png_256": target / "fantasy-agent-256.png",
            "png_512": target / "fantasy-agent-512.png",
        }
    return write_icon_set(target)


if __name__ == "__main__":
    written = write_icon_set(default_icon_dir())
    for name, path in sorted(written.items()):
        print(f"{name}: {path}")
