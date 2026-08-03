# Pilot Attribute Evaluation Preflight Block v1

Status: blocked before model loading or generated-video frame access.

## Trigger

The researcher authorized one CPU-only offline evaluation run over all twelve frozen videos, with local InsightFace, CLIP ViT-B/32, BiSeNet, and frozen single-annotator facial-hair annotation. Local dependency and model-file preflight passed: all packages are installed locally; CLIP weights, InsightFace ONNX models, and parsing_bisenet.pth exist; GPU visibility is explicitly disabled; network and installation are not required.

## Blocking ambiguity

The frozen hair-color metric spec provides these named values:

- expanded crop: left 0.85, right 0.85, top 0.9, bottom 1.4;
- core ROI: left 0.3, right 0.3, top_from_face_top 0.85, bottom_from_face_top 0.35.

It does not provide the signed, pixel-coordinate equations required to map these values from a detected face bbox into the expanded crop and core ROI. A local text/provenance search found no frozen implementation beyond the metric spec and the higher-level evaluation protocol.

This choice materially determines which pixels enter the BiSeNet class-17 mask and therefore the L-star result. It cannot be inferred or selected after inspecting generated frames.

## Proposed formula requiring confirmation

For a face bbox (x0, y0, x1, y1), width w=x1-x0, height h=y1-y0:

1. expanded analysis crop = [x0-0.85w, y0-0.90h, x1+0.85w, y1+1.40h], clipped to image bounds;
2. core ROI in original-image coordinates = [x0+0.30w, y0-0.85h, x1-0.30w, y0+0.35h], intersected with the expanded crop;
3. resize the expanded crop to 512x512 for parsing; map the core ROI into that grid; use only class-17 pixels within the mapped core ROI; then apply the frozen 7x7 erosion and 1000-pixel minimum.

The formula is a proposal, not a frozen fact. It will not be implemented until explicitly approved or replaced by the researcher.

## Preserved boundary

No model weights were loaded, no generated MP4 container was opened, no generated frame/pixel was read, and no attribute output was produced. The one-run authorization remains recorded, but execution is paused pending a coordinate-definition decision.
