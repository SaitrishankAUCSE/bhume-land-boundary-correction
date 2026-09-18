import os
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
import numpy as np
from shapely.geometry import Polygon

def load_village_data(village_name, base_dir="data"):
    """
    Loads the GeoJSON inputs and truths, converting to EPSG:3857 for meter-based alignment.
    Returns: gdf_input, gdf_truth, imagery_path, boundaries_path
    """
    village_dir = os.path.join(base_dir, village_name)
    input_path = os.path.join(village_dir, "input.geojson")
    truth_path = os.path.join(village_dir, "example_truths.geojson")
    imagery_path = os.path.join(village_dir, "imagery.tif")
    boundaries_path = os.path.join(village_dir, "boundaries.tif")
    
    gdf_input = gpd.read_file(input_path).to_crs(epsg=3857)
    
    if os.path.exists(truth_path):
        gdf_truth = gpd.read_file(truth_path).to_crs(epsg=3857)
    else:
        gdf_truth = None
        
    return gdf_input, gdf_truth, imagery_path, boundaries_path

def write_predictions(gdf_preds, village_name, base_dir="predictions"):
    """
    Writes predictions back to EPSG:4326 GeoJSON.
    """
    os.makedirs(os.path.join(base_dir, village_name), exist_ok=True)
    out_path = os.path.join(base_dir, village_name, "predictions.geojson")
    
    # Ensure correct CRS
    gdf_out = gdf_preds.to_crs(epsg=4326)
    
    # Write
    gdf_out.to_file(out_path, driver="GeoJSON")
    print(f"Predictions saved to {out_path}")

def score_iou(geom1, geom2):
    """
    Intersection over Union of two Shapely geometries.
    """
    if not geom1.is_valid or not geom2.is_valid:
        return 0.0
    inter = geom1.intersection(geom2).area
    union = geom1.union(geom2).area
    if union == 0:
        return 0.0
    return inter / union

def score_centroid_error(geom1, geom2):
    """
    Distance between centroids of two Shapely geometries in meters (assuming EPSG:3857).
    """
    return geom1.centroid.distance(geom2.centroid)

def evaluate_predictions(gdf_preds, gdf_truth):
    """
    Evaluates predictions against example_truths.
    Returns average IoU and average Centroid Error for plots that have valid ground truth.
    """
    # Merge by plot_number
    merged = gdf_preds.merge(gdf_truth[['plot_number', 'geometry']], on='plot_number', suffixes=('', '_truth'))
    
    ious = []
    centroid_errors = []
    
    for idx, row in merged.iterrows():
        pred_g = row['geometry']
        truth_g = row['geometry_truth']
        
        # Only evaluate if truth geometry is provided (sometimes they might be flagged without geom, though usually truth is the goal)
        if truth_g is not None and not truth_g.is_empty:
            ious.append(score_iou(pred_g, truth_g))
            centroid_errors.append(score_centroid_error(pred_g, truth_g))
            
    avg_iou = np.mean(ious) if ious else 0.0
    avg_ce = np.mean(centroid_errors) if centroid_errors else 0.0
    
    print(f"Evaluation Results ({len(ious)} plots):")
    print(f"  Average IoU: {avg_iou:.4f}")
    print(f"  Average Centroid Error: {avg_ce:.2f} meters")
    
    return avg_iou, avg_ce
