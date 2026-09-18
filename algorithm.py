import numpy as np
from shapely.affinity import translate
import rasterio
from rasterio.windows import from_bounds
from rasterio import features
from skimage.filters import sobel
from skimage.color import rgb2gray
from scipy.ndimage import zoom

def extract_patch(geom, raster_src, padding=25.0):
    """
    Extracts a raster patch around a geometry with the given padding (in meters).
    Returns the numpy array and the window's affine transform.
    """
    minx, miny, maxx, maxy = geom.bounds
    window = from_bounds(minx - padding, miny - padding, maxx + padding, maxy + padding, transform=raster_src.transform)
    
    # Bound the window to the raster dimensions
    window = window.intersection(rasterio.windows.Window(0, 0, raster_src.width, raster_src.height))
    
    # Ensure window is valid
    if window.width <= 0 or window.height <= 0:
        return None, None
        
    patch = raster_src.read(window=window)
    win_transform = raster_src.window_transform(window)
    return patch, win_transform

def process_imagery_patch(img_patch):
    """
    Converts 3-band RGB patch (3, H, W) to grayscale and applies Sobel filter.
    Returns normalized edge magnitude map (H, W).
    """
    if img_patch is None or img_patch.shape[0] != 3:
        return None
    
    # transpose from (3, H, W) to (H, W, 3)
    img_rgb = np.transpose(img_patch, (1, 2, 0)).astype(np.float32) / 255.0
    gray = rgb2gray(img_rgb)
    edges = sobel(gray)
    
    # Normalize to 0-1
    if edges.max() > 0:
        edges = edges / edges.max()
    return edges

def process_boundaries_patch(bound_patch):
    """
    Processes the boundaries patch (1, H, W).
    Returns normalized boundary map (H, W).
    """
    if bound_patch is None or bound_patch.shape[0] != 1:
        return None
    
    bound_map = bound_patch[0].astype(np.float32)
    if bound_map.max() > 0:
        bound_map = bound_map / 255.0  # Assuming uint8 0-255
    return bound_map

def evaluate_alignment(geom, edge_map, bound_map, transform):
    """
    Evaluates alignment by rasterizing the geometry boundary and computing the score.
    Returns a combined score.
    """
    try:
        lines = [geom.exterior]
    except AttributeError:
        lines = [geom.boundary]
        
    try:
        # Note: we use the shape of edge_map because boundary_map is resized to match it
        rasterized = features.rasterize(
            lines,
            out_shape=edge_map.shape,
            transform=transform,
            fill=0,
            default_value=1,
            dtype='uint8'
        )
    except Exception:
        return 0.0

    overlap_pixels = np.sum(rasterized)
    if overlap_pixels == 0:
        return 0.0
    
    # Evaluate score on imagery edges
    img_score = np.sum(rasterized * edge_map) / overlap_pixels
    
    # Evaluate score on provided boundaries hint
    bnd_score = np.sum(rasterized * bound_map) / overlap_pixels
    
    # Combined score (weighted average, weighting imagery edges slightly higher as it's the primary source of truth)
    combined_score = 0.7 * img_score + 0.3 * bnd_score
    return combined_score

def local_boundary_alignment(plot_geom, imagery_src, boundaries_src,
                             max_shift=25.0, step=3.0,
                             min_score=0.15, min_improvement=0.05,
                             min_bnd_agreement=0.10, min_confidence=0.50):
    """
    Attempts to correct the plot geometry by translating it locally.
    
    Checks applied:
    1. Compares best candidate against the ORIGINAL position.
    2. Requires meaningful score improvement (>= min_improvement).
    3. Compares best candidate against second-best distinct candidate (margin).
    4. Continuous distance penalty on candidates (penalizes large translations).
    5. Requires reasonable agreement between satellite edges and boundaries.tif (min_bnd_agreement).
    6. Requires calibrated confidence >= min_confidence; otherwise flags.
    7. Conservative if original geometry already has strong alignment evidence.
    8. Strictly bounds search to configured maximum radius (Euclidean distance <= max_shift).
    """
    padding = max_shift + 5.0
    img_patch, img_transform = extract_patch(plot_geom, imagery_src, padding=padding)
    bnd_patch, bnd_transform = extract_patch(plot_geom, boundaries_src, padding=padding)
    
    if img_patch is None or bnd_patch is None:
        return plot_geom, "flagged", 0.0

    edge_map = process_imagery_patch(img_patch)
    bnd_map = process_boundaries_patch(bnd_patch)
    
    if edge_map is None or bnd_map is None:
        return plot_geom, "flagged", 0.0

    # Match boundaries.tif resolution to edge_map resolution
    if bnd_map.shape != edge_map.shape:
        zoom_factors = (edge_map.shape[0] / bnd_map.shape[0], edge_map.shape[1] / bnd_map.shape[1])
        bnd_map = zoom(bnd_map, zoom_factors, order=1)

    def eval_geom(geom):
        try:
            lines = [geom.exterior]
        except AttributeError:
            lines = [geom.boundary]
        try:
            rasterized = features.rasterize(
                lines,
                out_shape=edge_map.shape,
                transform=img_transform,
                fill=0,
                default_value=1,
                dtype='uint8'
            )
            overlap = np.sum(rasterized)
            if overlap == 0:
                return 0.0, 0.0, 0.0
            img_s = float(np.sum(rasterized * edge_map) / overlap)
            bnd_s = float(np.sum(rasterized * bnd_map) / overlap)
            comb = 0.7 * img_s + 0.3 * bnd_s
            return comb, img_s, bnd_s
        except Exception:
            return 0.0, 0.0, 0.0

    orig_score, orig_img, orig_bnd = eval_geom(plot_geom)
    
    # 8. Never allow candidate beyond max search radius
    shifts = np.arange(-max_shift, max_shift + 0.1, step)
    candidates = []
    
    for dx in shifts:
        for dy in shifts:
            dist = float(np.hypot(dx, dy))
            if dist > max_shift:
                continue
            if dx == 0 and dy == 0:
                continue
                
            shifted_geom = translate(plot_geom, xoff=dx, yoff=dy)
            c_score, c_img, c_bnd = eval_geom(shifted_geom)
            if c_score == 0.0:
                continue
                
            # 4. Continuous distance penalty (up to 20% penalty at max_shift)
            dist_factor = 1.0 - 0.20 * (dist / max_shift)
            pen_score = c_score * dist_factor
            
            candidates.append({
                'pen_score': pen_score,
                'raw_score': c_score,
                'img': c_img,
                'bnd': c_bnd,
                'dx': dx,
                'dy': dy,
                'dist': dist,
                'geom': shifted_geom
            })
            
    if not candidates:
        return plot_geom, "flagged", 0.0
        
    candidates.sort(key=lambda x: x['pen_score'], reverse=True)
    best = candidates[0]
    
    # 3. Compare best candidate against second-best distinct candidate (>= 4m away)
    second = None
    for c in candidates[1:]:
        if np.hypot(c['dx'] - best['dx'], c['dy'] - best['dy']) >= 4.0:
            second = c
            break
    if second is None and len(candidates) > 1:
        second = candidates[1]
    second_pen = second['pen_score'] if second else 0.0
    
    # 1. Compare best candidate against original position
    improvement = best['pen_score'] - orig_score
    margin = best['pen_score'] - second_pen
    
    # Confidence calculation: 4 explainable components
    c_imp = float(np.clip(improvement / 0.10, 0.0, 1.0))
    c_margin = float(np.clip(margin / 0.02, 0.0, 1.0))
    c_img = float(np.clip(best['img'] / 0.25, 0.0, 1.0))
    c_bnd = float(np.clip(best['bnd'] / 0.25, 0.0, 1.0))
    confidence = round(0.35 * c_imp + 0.25 * c_margin + 0.20 * c_img + 0.20 * c_bnd, 2)
    
    # Restraint & Quality checks:
    # 1 & 2. Minimum raw quality and meaningful improvement
    if best['pen_score'] < min_score or improvement < min_improvement:
        return plot_geom, "flagged", 0.0
        
    # 5. Require reasonable agreement with boundaries.tif
    if best['bnd'] < min_bnd_agreement:
        return plot_geom, "flagged", 0.0
        
    # 7. Conservative if original geometry already has strong alignment
    if orig_score >= 0.15 and improvement < 0.05:
        return plot_geom, "flagged", 0.0
    if orig_img >= 0.12 and best['dist'] > 15.0 and best['bnd'] < 0.15:
        return plot_geom, "flagged", 0.0

    # 6. Validated confidence threshold
    if confidence < min_confidence:
        return plot_geom, "flagged", 0.0
        
    return best['geom'], "corrected", confidence
