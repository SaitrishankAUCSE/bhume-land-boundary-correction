import sys
import rasterio
from tqdm import tqdm
from utils import load_village_data, write_predictions, evaluate_predictions
from algorithm import local_boundary_alignment

def process_village(village_name, eval_only=False):
    print(f"Processing village: {village_name} (eval_only={eval_only})")
    gdf_input, gdf_truth, imagery_path, boundaries_path = load_village_data(village_name)
    
    if eval_only and gdf_truth is not None:
        truth_plots = set(gdf_truth['plot_number'].astype(str))
        gdf_input = gdf_input[gdf_input['plot_number'].astype(str).isin(truth_plots)]
        print(f"Filtering to {len(gdf_input)} plots for evaluation.")
    
    corrected_geometries = []
    statuses = []
    confidences = []
    
    with rasterio.open(imagery_path) as imagery_src, rasterio.open(boundaries_path) as boundaries_src:
        for idx, row in tqdm(gdf_input.iterrows(), total=len(gdf_input)):
            plot_geom = row['geometry']
            
            new_geom, status, confidence = local_boundary_alignment(plot_geom, imagery_src, boundaries_src)
            
            corrected_geometries.append(new_geom)
            statuses.append(status)
            confidences.append(confidence)
            
    # Update GDF
    gdf_preds = gdf_input.copy()
    gdf_preds['geometry'] = corrected_geometries
    gdf_preds['status'] = statuses
    gdf_preds['confidence'] = confidences
    
    # Evaluate if truths exist
    if gdf_truth is not None:
        evaluate_predictions(gdf_preds, gdf_truth)
        
    # Write output
    if not eval_only:
        write_predictions(gdf_preds, village_name)
        print(f"Finished {village_name}\n")
    else:
        print(f"Finished evaluation on {village_name}\n")

if __name__ == "__main__":
    eval_only = "--eval-only" in sys.argv
    villages = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if not villages:
        villages = ["vadnerbhairav", "malatavadi"]
        
    for village in villages:
        process_village(village, eval_only=eval_only)
