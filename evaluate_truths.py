import sys
import numpy as np
import geopandas as gpd
import rasterio
from utils import load_village_data, score_iou, score_centroid_error
from algorithm import local_boundary_alignment

def evaluate_village(village_name):
    print(f"\n{'='*75}\nEVALUATING {village_name.upper()}\n{'='*75}")
    gdf_input, gdf_truth, imagery_path, boundaries_path = load_village_data(village_name)
    
    if gdf_truth is None or len(gdf_truth) == 0:
        print(f"No truths found for {village_name}")
        return
        
    truth_plots = set(gdf_truth['plot_number'].astype(str))
    gdf_eval = gdf_input[gdf_input['plot_number'].astype(str).isin(truth_plots)]
    
    print(f"{'Plot':<6} | {'Orig IoU':<8} | {'Corr IoU':<8} | {'Orig CE(m)':<10} | {'Corr CE(m)':<10} | {'Improv(m)':<9} | {'Status':<10} | {'Conf':<6} | {'dx':<6} | {'dy':<6}")
    print("-" * 105)
    
    orig_ious, corr_ious = [], []
    orig_ces, corr_ces = [], []
    corrected_count, flagged_count = 0, 0
    
    with rasterio.open(imagery_path) as img_src, rasterio.open(boundaries_path) as bnd_src:
        for idx, row in gdf_eval.iterrows():
            plot = str(row['plot_number'])
            orig_geom = row['geometry']
            
            # Run algorithm
            new_geom, status, conf = local_boundary_alignment(orig_geom, img_src, bnd_src)
            
            # Get truth
            truth_row = gdf_truth[gdf_truth['plot_number'].astype(str) == plot].iloc[0]
            truth_geom = truth_row['geometry']
            
            # Calculate metrics
            orig_iou = score_iou(orig_geom, truth_geom)
            corr_iou = score_iou(new_geom, truth_geom)
            
            orig_ce = score_centroid_error(orig_geom, truth_geom)
            corr_ce = score_centroid_error(new_geom, truth_geom)
            improv_ce = orig_ce - corr_ce
            
            orig_ious.append(orig_iou)
            corr_ious.append(corr_iou)
            orig_ces.append(orig_ce)
            corr_ces.append(corr_ce)
            
            if status == "corrected":
                corrected_count += 1
            else:
                flagged_count += 1
                
            dx = new_geom.centroid.x - orig_geom.centroid.x
            dy = new_geom.centroid.y - orig_geom.centroid.y
            
            print(f"{plot:<6} | {orig_iou:<8.4f} | {corr_iou:<8.4f} | {orig_ce:<10.2f} | {corr_ce:<10.2f} | {improv_ce:<9.2f} | {status:<10} | {conf:<6.2f} | {dx:<6.1f} | {dy:<6.1f}")
            
    print("-" * 105)
    print(f"Summary for {village_name}:")
    print(f"  Average IoU: Baseline = {np.mean(orig_ious):.4f} -> Corrected = {np.mean(corr_ious):.4f} (Change: {np.mean(corr_ious)-np.mean(orig_ious):+.4f})")
    print(f"  Average CE : Baseline = {np.mean(orig_ces):.2f}m -> Corrected = {np.mean(corr_ces):.2f}m (Reduction: {np.mean(orig_ces)-np.mean(corr_ces):+.2f}m)")
    print(f"  Status Count: Corrected = {corrected_count}, Flagged = {flagged_count}")

if __name__ == "__main__":
    evaluate_village("vadnerbhairav")
    evaluate_village("malatavadi")
