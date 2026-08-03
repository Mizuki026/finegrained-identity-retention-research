#!/usr/bin/env python3
"""Create a non-overwriting DOCX snapshot of a versioned Chinese research record.

This utility is local-only and uses only the Python standard library. It does
not read research data, videos, models, or network resources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def paragraph(text: str, style: str | None = None) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def markdown_to_document_xml(source: str) -> str:
    parts: list[str] = []
    for raw in source.splitlines():
        if raw.startswith("### "):
            parts.append(paragraph(raw[4:], "Heading3"))
        elif raw.startswith("## "):
            parts.append(paragraph(raw[3:], "Heading2"))
        elif raw.startswith("# "):
            parts.append(paragraph(raw[2:], "Title"))
        elif raw.startswith("- "):
            parts.append(paragraph("• " + raw[2:]))
        elif raw.startswith("| "):
            parts.append(paragraph(raw.replace("|", "  |  ").strip()))
        elif raw.startswith("|"):
            parts.append(paragraph(raw.replace("|", "  |  ").strip()))
        elif raw:
            parts.append(paragraph(raw))
        else:
            parts.append("<w:p/>")
    body = "".join(parts) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            + body + '</w:body></w:document>')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    if not args.source.is_file() or args.source.is_symlink():
        raise SystemExit("FAIL: source must be a regular Markdown file")
    if args.output.exists() or args.log.exists():
        raise SystemExit("FAIL: refusing to overwrite existing output or log")
    if args.output.suffix.lower() != ".docx":
        raise SystemExit("FAIL: output must have .docx suffix")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source_text = args.source.read_text(encoding="utf-8")
    document = markdown_to_document_xml(source_text)
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    styles = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="Heading 2"/><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="Heading 3"/><w:rPr><w:b/><w:sz w:val="22"/></w:rPr></w:style>'
              '</w:styles>')
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
    with zipfile.ZipFile(args.output) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise SystemExit(f"FAIL: DOCX ZIP validation failed at {bad}")
    payload = {
        "status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
        "cpu_only": True,
        "network_used": False,
        "models_loaded": False,
        "frozen_artifacts_read": False,
    }
    with args.log.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
