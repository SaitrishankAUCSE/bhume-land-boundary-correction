# BhuMe Land-Boundary Correction

A simple, robust, and interpretable spatial translation method for correcting cadastral land parcel boundaries using satellite imagery and supporting boundary hints.

## 1. The Problem
Official cadastral boundaries (`input.geojson`) frequently suffer from systematic shifts relative to physical field boundaries on the ground. The task is to evaluate each plot, identify whether an unambiguous spatial displacement exists, apply a rigid local translation if strong evidence is present, or safely flag the plot and retain the original geometry if the evidence is ambiguous or weak.

## 2. Input Files
Each village dataset contains:
- `input.geojson`: Official parcel boundaries in EPSG:4326.
- `imagery.tif`: High-resolution satellite imagery (primary signal).
- `boundaries.tif`: Rough model-derived boundary probability hints (supporting evidence).
- `example_truths.geojson`: Hand-verified ground truth plots used for evaluation.

## 3. Simple Algorithm
The pipeline adheres strictly to a local translation grid search without arbitrary polygon deformation:
1. **Reprojection**: Reproject polygon from `EPSG:4326` to `EPSG:3857` (metric coordinates).
2. **Feature Extraction**:
   - Extract a local patch around the plot with padding.
   - Compute gradient magnitude via Sobel filter on grayscale satellite imagery (`imagery.tif`).
   - Resample and normalize the supporting boundary raster (`boundaries.tif`).
3. **Candidate Search**:
   - Evaluate candidate translations $(dx, dy)$ within a strict radius of $25.0\,\text{m}$ at $3.0\,\text{m}$ intervals.
   - For each candidate, evaluate boundary pixel overlap with detected imagery edges ($70\%$ weight) and supporting boundary hints ($30\%$ weight).
   - Apply a continuous distance penalty ($20\%$ at max radius) to favor smaller, conservative shifts.
4. **Restraint & Verification**:
   - Compare the best candidate against the unshifted original geometry.
   - Compare against the second-best candidate from a distinct spatial peak (minimum peak margin).
   - Require corroboration from `boundaries.tif` ($\ge 0.10$) so spurious satellite features (e.g., roads, tree lines) cannot cause bad shifts.
   - Enforce conservatism if the original geometry already aligns well with image features.

## 4. Confidence
Confidence is a calibrated $0.0 - 1.0$ metric derived transparently from four physical factors:
1. **Improvement over original**: Degree of score increase compared to the unshifted state.
2. **Peak distinctness (margin)**: Separation between the best candidate and the next distinct peak.
3. **Satellite edge evidence**: Absolute intensity of detected visual edges.
4. **Boundary hint agreement**: Degree of agreement with supporting cadastral hints.

$$ \text{Confidence} = 0.35 \cdot C_{\text{imp}} + 0.25 \cdot C_{\text{margin}} + 0.20 \cdot C_{\text{img}} + 0.20 \cdot C_{\text{bnd}} $$

- A plot is only accepted as `corrected` if $\text{Confidence} \ge 0.50$ and all quality criteria pass.
- Uncertain, ambiguous, or poorly corroborated candidates are given $\text{Confidence} = 0.0$ and marked as `flagged`.

## 5. Flagging
Plots are conservatively flagged and retain their exact original geometry whenever:
- The candidate score improvement is below threshold ($< 0.05$).
- Several candidate shifts exhibit near-identical scores (ambiguous landscape).
- Satellite edge evidence is weak or obscured.
- `boundaries.tif` has near-zero agreement with the candidate shift.
- The plot is already reasonably well aligned.

## 6. How to Run
Ensure requirements are installed:
```bash
pip install -r requirements.txt
```

To run the complete pipeline and generate predictions for both villages:
```bash
python run.py vadnerbhairav malatavadi
```
Outputs are written to:
- `predictions/vadnerbhairav/predictions.geojson`
- `predictions/malatavadi/predictions.geojson`

## 7. How to Evaluate
To run evaluation against the provided `example_truths.geojson` plots:
```bash
python evaluate_truths.py
```
Or use the `--eval-only` flag on `run.py`:
```bash
python run.py vadnerbhairav malatavadi --eval-only
```

