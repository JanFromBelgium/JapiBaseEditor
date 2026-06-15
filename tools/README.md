# tools/

Helper scripts for maintaining this repository. You do not need any of these to
build or run the editor — they only regenerate documentation assets. Run them
from the repository root.

| File | What it does |
|---|---|
| `make_pdf.py` | Builds `JBE_MANUAL.pdf` from `JBE_MANUAL.md`: a dependency-free Markdown-to-HTML step, the Roboto Mono font embedded, printed to PDF by headless Chrome. Needs `google-chrome`. |
| `mkhelp.py` | Builds `editor/help_text.h` from `JBE_MANUAL.md`: the screen-wrapped, CP437-encoded text and the anchor table behind the editor's built-in **F1 help**. The header is committed (so the firmware/sim build needs no code-gen step) — regenerate it whenever the manual changes. Python standard library only. |
| `make-screenshots.sh` | Regenerates the README screenshots in `images/` from the **real** Japi Base 8×12 font and 6-bit palette, so the pictures match the hardware exactly. Builds `screenshot.c`, then converts with `ffmpeg`. |
| `screenshot.c` | Source for the screenshot generator. It renders a few editor scenes to a `.ppm`; `make-screenshots.sh` compiles it and turns the output into PNGs. |
| `fonts/` | The Roboto Mono web-font subsets used by `make_pdf.py`, with an Apache-2.0 attribution note. |

## Regenerate the manual and the in-editor help

Both come from the single source `JBE_MANUAL.md`, so run these after editing it:

```sh
python3 tools/make_pdf.py        # -> JBE_MANUAL.pdf
python3 tools/mkhelp.py          # -> editor/help_text.h  (the F1 help)
```

## Regenerate the screenshots

```sh
tools/make-screenshots.sh        # -> images/*.png  (needs gcc + ffmpeg)
```

The compiled `screenshot` binary is a build artifact and is not committed.
