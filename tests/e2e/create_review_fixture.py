"""Create deterministic PDF-signoff files for browser-process E2E tests."""

import json
import sys
from pathlib import Path

import pymupdf

directory = Path(sys.argv[1])
directory.mkdir(parents=True, exist_ok=True)
input_pdf = directory / "input.pdf"
signature = directory / "signature.png"
profile = directory / "profile.json"

with pymupdf.open() as document:
    page = document.new_page(width=600, height=800)
    page.insert_text((50, 60), "Approval form for browser review")
    document.save(input_pdf)

pixels = bytes((17, 62, 145, 255)) * (120 * 30)
signature.write_bytes(
    pymupdf.Pixmap(pymupdf.csRGB, 120, 30, pixels, True).tobytes("png")
)
profile.write_text(
    json.dumps(
        {
            "version": 1,
            "created_from": {"sha256": "reusable-template"},
            "match": {
                "page_count": 1,
                "pages": [
                    {
                        "page": 1,
                        "width_pt": 600,
                        "height_pt": 800,
                        "rotation": 0,
                    }
                ],
                "required_text": [
                    {"page": 1, "text": "Approval form for browser review"}
                ],
            },
            "placements": [
                {
                    "page": 1,
                    "x": 0.15,
                    "y": 0.2,
                    "width": 0.25,
                    "height": 0.046875,
                }
            ],
        }
    ),
    encoding="utf-8",
)
