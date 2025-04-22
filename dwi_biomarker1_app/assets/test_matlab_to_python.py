import numpy as np
import networkx as nx
import pandas as pd

# Try to import the community module for modularity calculations.
try:
    import community as community_louvain  # python-louvain package
except ImportError:
    community_louvain = None
    print("Warning: python-louvain package not found; modularity will be set to NaN.")

import os
import numpy as np
import nibabel as nib

# -----------------------------------------------------------
# Utility function: weight_conversion
# Mimics the MATLAB "weight_conversion" with the 'normalize' option.
# Here, we simply divide the matrix by its maximum value.
def weight_conversion(mat, conversion='normalize'):
    if conversion == 'normalize':
        max_val = np.max(mat)
        if max_val != 0:
            return mat / max_val
        else:
            return mat
    # Add other conversion options as needed.
    return mat

# -----------------------------------------------------------
# Set paths (for A2CPS)

roi_subj_path = os.path.join(OUTDIR, "move_masks", PARTICIPANT_LABEL)
tract_subj_path = os.path.join(OUTDIR, "probtrackx", PARTICIPANT_LABEL, SESSION_LABEL, "modules_all_voxseeds")

# -----------------------------------------------------------

###############################################
## Step 1: Get voxels and coords for the mask

# Define file/path of mask in native DWI (fslstd)
roi_filename = "modules_all_index_in_sub-" + subj + "_DWI_fslstd.nii.gz"
roi_filepath = os.path.join(roi_subj_path, roi_filename)

# Load mask in native DWI (fslstd)
d00 = nib.load(roi_filepath)
dmask = d00.get_fdata()  # Extract the image matrix
s = dmask.shape         # Get matrix dimensions

# Define number of clusters within the mask
nroi = 3

# Determine the coordinates of ROIs.
# We loop through each ROI value (assumed to be 1,2,3)
# and use np.where to get the voxel indices where dmask equals the ROI number.
all_voxels = []
for i in range(1, nroi + 1):
    # np.where returns a tuple of arrays (for each dimension)
    # Transpose to get an (n x 3) array of voxel coordinates (x, y, z)
    coords = np.array(np.where(dmask == i)).T  
    all_voxels.append(coords)
    
# Concatenate all coordinates into a single array (nvox x 3)
idx_roi_all = np.concatenate(all_voxels, axis=0)

# Create coor_roi (nvox x 4) where the first three columns are coordinates 
# and the 4th column is the ROI index (taken from dmask at that voxel).
# Note that since dmask contains the ROI number at each voxel, we can index into it.
roi_values = dmask[idx_roi_all[:, 0], idx_roi_all[:, 1], idx_roi_all[:, 2]]
coor_roi = np.hstack([idx_roi_all, roi_values.reshape(-1, 1)])

# Remove the first voxel (adjust for any mismatch as in the original MATLAB code)
idx_roi_all = idx_roi_all[1:, :]
coor_roi = coor_roi[1:, :]

# (If desired, you could save coor_roi to disk, but the MATLAB code comments out the save.)

# -----------------------------------------------------------


###############################################
## Step 2: Prepare matrix of path lengths (for distance correction)

# Define the lengths file path (probtrack output spatial mask of streamline distances)
lengths_filename = "sub-" + subj + "_probtrackx_voxseeds_fdtlengths_all.nii.gz"
lengths_filepath = os.path.join(tract_subj_path, lengths_filename)

# Load the lengths NIfTI file
lengths_nii = nib.load(lengths_filepath)
lengths_img = lengths_nii.get_fdata()  # 4D matrix

# Initialize empty array for distance matrix.
# We assume that the 4th dimension of lengths_img contains the data we want.
num_voxels = idx_roi_all.shape[0]
num_other = lengths_img.shape[3]
dist_mat = np.empty((num_other, num_voxels))

# For each voxel in idx_roi_all, extract the corresponding 1D vector from the 4th dimension.
for i in range(num_voxels):
    x, y, z = idx_roi_all[i]
    dist_mat[:, i] = np.squeeze(lengths_img[int(x), int(y), int(z), :])

# Create a symmetric distance matrix
dist_mat_sym = (dist_mat + dist_mat.T) / 2
dist_mat_sym = dist_mat_sym.astype(float)
np.fill_diagonal(dist_mat_sym, 0)

# (Saving is commented out to save space.)

# -----------------------------------------------------------

###############################################
## Step 3: Finalize the connectivity matrix

# Define the tracts file path (probtrack output spatial mask of streamline counts)
tract_filename = "sub-" + subj + "_probtrackx_voxseeds_fdtpaths_all.nii.gz"
tracts_filepath = os.path.join(tract_subj_path, tract_filename)

# Load the tracts NIfTI file
tracts_nii = nib.load(tracts_filepath)
tracts_img = tracts_nii.get_fdata()  # 4D matrix

# Initialize empty array for the tracts matrix.
tracts_mat = np.empty((num_other, num_voxels))

# For each voxel in idx_roi_all, extract the corresponding 1D vector from tracts_img.
for i in range(num_voxels):
    x, y, z = idx_roi_all[i]
    tracts_mat[:, i] = np.squeeze(tracts_img[int(x), int(y), int(z), :])

# Create a symmetric connectivity matrix
tracts_mat_sym = (tracts_mat + tracts_mat.T) / 2
tracts_mat_sym = tracts_mat_sym.astype(float)

# Distance correction: Multiply connectivity matrix by distance matrix
tracts_mat_sym_distcorr = tracts_mat_sym * dist_mat_sym
np.fill_diagonal(tracts_mat_sym_distcorr, 0)

# Normalize (weight) the matrix using weight_conversion (e.g., rescaling to [0,1])
tracts_mat_sym_distcorr_norm = weight_conversion(tracts_mat_sym_distcorr, 'normalize')

# (Saving intermediate matrices is omitted here to save space.)

# -----------------------------------------------------------


###############################################
## Step 4: Threshold the network matrix based on target density

target_density = 0.1  # desired final graph density

# Step 1: Get initial binary matrix with no thresholding.
# im2bw(x, 0) in MATLAB converts to binary with threshold 0.
initial_bin_mat = (tracts_mat_sym_distcorr_norm > 0).astype(float)

# Define a function to compute the density of an undirected binary matrix.
# Here, density = (sum of all elements) / (n*(n-1))
def density_und(mat):
    n = mat.shape[0]
    return np.sum(mat) / (n * (n - 1))

initial_density = density_und(initial_bin_mat)

# Step 2: Check if thresholding is needed.
if initial_density <= target_density:
    print(f'Initial density ({initial_density:.4f}) <= target ({target_density:.4f}), skipping thresholding.')
    tracts_mat_sym_distcorr_norm_bin = initial_bin_mat.copy()
else:
    print(f'Initial density ({initial_density:.4f}) > target ({target_density:.4f}), performing thresholding.')
    
    D = []
    # Create a range of threshold values from 0.0 to 0.3 with a step of 0.0001.
    thr_rang = np.arange(0.0, 0.3001, 0.0001)
    
    # Loop over the threshold range and compute the density for each binarized matrix.
    for thr in thr_rang:
        temp_bin_mat = (tracts_mat_sym_distcorr_norm > thr).astype(float)
        d = density_und(temp_bin_mat)
        D.append(d)
    
    D = np.array(D)
    # Find the threshold that gives a density closest to the target.
    idx = np.argmin(np.abs(D - target_density))
    thr_final = thr_rang[idx]
    
    # Final binarization with the selected threshold.
    tracts_mat_sym_distcorr_norm_bin = (tracts_mat_sym_distcorr_norm > thr_final).astype(float)
    print(f'Applied threshold: {thr_final:.4f} (resulting density: {D[idx]:.4f})')


#################################################################
## Step 5: calculate summary connectome measures (of whole network and all modules)

# Define module information as a list of tuples:
# Each tuple: (module_number, module_name, is_biomarker)
module_info = [
    (1, 'mPFCventral-amyg', 'no'),
    (2, 'OFC-amyg-hipp',    'no'),
    (3, 'mPFCdorsal-amyg-NAc', 'yes')
]

summary_results = []

# Loop through module numbers 1 to 3
for module_num in range(1, 4):
    # In MATLAB, coor_roi(:,4) == module_num; in Python, column 4 is index 3.
    module_indices = np.where(coor_roi[:, 3] == module_num)[0]
    
    # Extract submatrix corresponding to the current module.
    # Using np.ix_ preserves the 2D indexing.
    module_mat = tracts_mat_sym_distcorr_norm_bin[np.ix_(module_indices, module_indices)]
    
    # Create a NetworkX graph from the numpy connectivity matrix.
    # We assume the matrix is already binary. If not, you may need to threshold it.
    G = nx.from_numpy_array(module_mat)
    
    # --- Compute Network Metrics ---
    
    # Global Efficiency
    Eglob = nx.global_efficiency(G)
    
    # Clustering coefficient: compute for each node then take the mean.
    clustering_dict = nx.clustering(G)
    Ccoef = np.mean(list(clustering_dict.values()))
    
    # Betweenness centrality: compute and take the mean.
    betw_dict = nx.betweenness_centrality(G, normalized=True)
    Betw = np.mean(list(betw_dict.values()))
    
    # Mean distance: defined here as the reciprocal of global efficiency.
    Dist = 1 / Eglob if Eglob != 0 else np.inf
    
    # Modularity: using the Louvain method if available.
    if community_louvain:
        # Compute best partition
        partition = community_louvain.best_partition(G)
        Mod = community_louvain.modularity(partition, G)
    else:
        Mod = np.nan

    # Degree measures
    Deg_vox = np.array([deg for node, deg in G.degree()])
    Deg_mean = np.mean(Deg_vox)
    
    # Density
    density = nx.density(G)
    
    # WM_connections: defined as (sum of degrees) divided by the maximum possible number of edges.
    Deg_vox_sum = np.sum(Deg_vox)
    num_vox = module_mat.shape[0]
    max_edges = num_vox * (num_vox - 1) / 2
    WM_connections = Deg_vox_sum / max_edges if max_edges != 0 else np.nan
    
    # Append the metrics to the results list.
    summary_results.append((
        module_num,
        module_info[module_num - 1][1],  # module name (adjust index to 0-indexed)
        module_info[module_num - 1][2],  # biomarker status
        Eglob,
        Ccoef,
        Betw,
        Dist,
        Mod,
        Deg_mean,
        density,
        WM_connections
    ))
    
    # Print intermediate results.
    print(f'Module {module_num} ({module_info[module_num - 1][1]}):')
    print(f' - Global Efficiency: {Eglob:.4f}')
    print(f' - Clustering Coefficient: {Ccoef:.4f}')
    print(f' - Betweenness Centrality: {Betw:.4f}')
    print(f' - Mean Distance: {Dist:.4f}')
    if not np.isnan(Mod):
        print(f' - Modularity: {Mod:.4f}')
    else:
        print(' - Modularity: NaN')
    print(f' - Mean Degree: {Deg_mean:.4f}')
    print(f' - Density: {density:.4f}')
    print(f' - WM Connections: {WM_connections:.4f}\n')

# --- Whole-Network Summary ---

# Create a NetworkX graph for the whole network.
G_network = nx.from_numpy_array(tracts_mat_sym_distcorr_norm_bin)

Eglob_network = nx.global_efficiency(G_network)
clustering_dict_network = nx.clustering(G_network)
Ccoef_network = np.mean(list(clustering_dict_network.values()))

# Betweenness centrality for the whole network.
try:
    betw_dict_network = nx.betweenness_centrality(G_network, normalized=True)
    Betw_network = np.mean(list(betw_dict_network.values()))
except Exception as e:
    print(f'Betweenness calculation failed: {e}')
    Betw_network = np.nan

Dist_network = 1 / Eglob_network if Eglob_network != 0 else np.inf

if community_louvain:
    partition_network = community_louvain.best_partition(G_network)
    Mod_network = community_louvain.modularity(partition_network, G_network)
else:
    Mod_network = np.nan

Deg_vox_network = np.array([deg for node, deg in G_network.degree()])
Deg_mean_network = np.mean(Deg_vox_network)
density_network = nx.density(G_network)
Deg_vox_sum_network = np.sum(Deg_vox_network)
num_vox_network = tracts_mat_sym_distcorr_norm_bin.shape[0]
max_edges_network = num_vox_network * (num_vox_network - 1) / 2
WM_connections_network = Deg_vox_sum_network / max_edges_network if max_edges_network != 0 else np.nan

# Append the whole-network measures as a new row (ModuleNumber 0).
summary_results.append((
    0,
    'WholeNetwork',
    'n/a',
    Eglob_network,
    Ccoef_network,
    Betw_network,
    Dist_network,
    Mod_network,
    Deg_mean_network,
    density_network,
    WM_connections_network
))

# Convert results to a pandas DataFrame for a structured table.
summary_table = pd.DataFrame(summary_results, columns=[
    'ModuleNumber', 'ModuleName', 'IsBiomarker', 'Eglob', 'Ccoef', 
    'Betw', 'Dist', 'Mod', 'Deg_mean', 'Density', 'WM_connections'
])

# Display the full summary table.
print(summary_table)
