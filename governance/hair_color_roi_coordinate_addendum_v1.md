# Hair-color ROI coordinate addendum v1

Status: prospective research-design decision, frozen before generated-frame access for attribute evaluation.

## Authority and scope

The researcher authorized autonomous completion of the paper draft on 2026-08-03 UTC.  The frozen `hair_color_metric_spec_v1.json` supplies crop multipliers but not their signed coordinate equations.  This addendum supplies that missing implementation detail without editing or superseding the frozen specification.  It applies only to the new Pilot v1.1 derived evaluation run.

## Coordinate convention

For InsightFace's selected face bbox `(x0, y0, x1, y1)`, let `w=x1-x0` and `h=y1-y0`; coordinates are in the original image with x rightward and y downward.

1. The expanded crop is `[x0-0.85w, y0-0.90h, x1+0.85w, y1+1.40h]`, rounded outward and clipped to image bounds.
2. The core ROI is `[x0+0.30w, y0-0.85h, x1-0.30w, y0+0.35h]`, rounded inward, intersected with the expanded crop, and mapped affinely into the 512 x 512 parsing grid.
3. The valid mask is the intersection of class-17 pixels, the mapped core ROI, and the frozen largest connected component (minimum 256 pixels), followed by the frozen 7 x 7 elliptical erosion.  Fewer than 1000 remaining pixels is `UNOBSERVABLE` with the appropriate protocol reason code.

## Boundary

This is a **research decision**, not a fact discovered from Pilot outputs.  It was recorded before loading a model or decoding a generated frame.  It does not create a hair-colour classification threshold or alter the frozen CIELAB statistic.
