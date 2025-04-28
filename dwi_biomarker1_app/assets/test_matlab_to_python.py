import os
import numpy as np
import nibabel as nib
import bct
import pandas as pd

# ------------------------------
# User-defined variables (edit these)
# ------------------------------
OUTDIR = "/path/to/output"
PARTICIPANT_LABEL = "sub-XX"
SESSION_LABEL = "ses-YY"

# Paths
roi_path = os.path.join(OUTDIR, "move_masks", PARTICIPANT_LABEL, SESSION_LABEL)
tract_path = os.path.join(OUTDIR, "probtrackx", PARTICIPANT_LABEL, SESSION_LABEL, "DWIbiomarker1_modules_all_voxseeds")

# ------------------------------
# Step 1: Load mask and get voxel coordinates
# ------------------------------
roi_filename = f"{PARTICIPANT_LABEL}_{SESSION_LABEL}_desc-mask_modules_all_index_space-dwi-fslstd.nii.gz"
mask_img = nib.load(os.path.join(roi_path, roi_filename))
dmask = mask_img.get_fdata().astype(int)
s = dmask.shape

# Number of ROIs (clusters)
nroi = int(dmask.max())

# Collect voxel indices and ROI labels
idx_list = []
labels = []
for roi_id in range(1, nroi+1):
    coords = np.argwhere(dmask == roi_id)
    idx_list.append(coords)
    labels.append(np.full(len(coords), roi_id, dtype=int))

# Concatenate all
idx_roi_all = np.vstack(idx_list)
labels_all = np.concatenate(labels)

# Combine to coor_roi: x, y, z, roi_id
coor_roi = np.hstack([idx_roi_all, labels_all[:, None]])

# Remove first voxel if needed (MATLAB did this to fix index mismatch)
# coor_roi = coor_roi[1:]
# idx_roi_all = idx_roi_all[1:]

# Number of voxels
nvox = coor_roi.shape[0]

# ------------------------------
# Step 2: Build distance matrix
# ------------------------------
lengths_filename = f"{PARTICIPANT_LABEL}_{SESSION_LABEL}_DWIbiomarker1_fdtlengths_all.nii.gz"
lengths_img = nib.load(os.path.join(tract_path, lengths_filename)).get_fdata()

# Preallocate
dist_mat = np.zeros((nvox, nvox))
for i, (x, y, z, _) in enumerate(coor_roi):
    dist_mat[i, :] = lengths_img[x, y, z, :nvox].squeeze()

# Symmetrize and zero-diagonal
dist_mat_sym = (dist_mat + dist_mat.T) / 2.0
np.fill_diagonal(dist_mat_sym, 0)

dist_mat_sym = dist_mat_sym.astype(float)

# ------------------------------
# Step 3: Build tractography (streamline count) matrix
# ------------------------------
tracts_filename = f"{PARTICIPANT_LABEL}_{SESSION_LABEL}_DWIbiomarker1_fdtpaths_all.nii.gz"
tracts_img = nib.load(os.path.join(tract_path, tracts_filename)).get_fdata()

tracts_mat = np.zeros((nvox, nvox))
for i, (x, y, z, _) in enumerate(coor_roi):
    tracts_mat[i, :] = tracts_img[x, y, z, :nvox].squeeze()

# Symmetrize and zero-diagonal
tracts_mat_sym = (tracts_mat + tracts_mat.T) / 2.0
np.fill_diagonal(tracts_mat_sym, 0)
tracts_mat_sym = tracts_mat_sym.astype(float)

# Distance correction: multiply by distances
tracts_mat_sym_distcorr = tracts_mat_sym * dist_mat_sym
np.fill_diagonal(tracts_mat_sym_distcorr, 0)

# Normalize weights
tracts_mat_sym_distcorr_norm = bct.weight_conversion(tracts_mat_sym_distcorr, 'normalize')

# ------------------------------
# Step 4: Threshold to target density
# ------------------------------
target_density = 0.1
# initial binary
initial_bin = (tracts_mat_sym_distcorr_norm > 0).astype(int)
initial_density = bct.density_und(initial_bin)

if initial_density <= target_density:
    final_bin = initial_bin
else:
    thr_range = np.arange(0.0, 0.3001, 0.0001)
    densities = []
    for thr in thr_range:
        tmp_bin = (tracts_mat_sym_distcorr_norm >= thr).astype(int)
        densities.append(bct.density_und(tmp_bin))
    densities = np.array(densities)
    idx = np.argmin(np.abs(densities - target_density))
    thr_final = thr_range[idx]
    final_bin = (tracts_mat_sym_distcorr_norm >= thr_final).astype(int)
    print(f"Applied threshold {thr_final:.4f}, resulting density {densities[idx]:.4f}")

# Save binary matrix
np.savetxt(os.path.join(tract_path, 'DWIbiomarker1_matrix_sym_distcorr_norm_bin.txt'), final_bin, fmt='%d', delimiter='\t')

# ------------------------------
# Step 5a: Module-level summary
# ------------------------------
module_info = [
    (1, 'mPFCventral-amyg', False),
    (2, 'OFC-amyg-hipp', False),
    (3, 'mPFCdorsal-amyg-NAc', True)
]

rows = []
for module_num, name, is_bio in module_info:
    inds = np.where(coor_roi[:, 3] == module_num)[0]
    mat = final_bin[np.ix_(inds, inds)]
    Eglob = bct.efficiency_bin(mat)
    Ccoef_all = bct.clustering_coef_bu(mat)
    Ccoef = np.mean(Ccoef_all)
    Betw_all = bct.betweenness_bin(mat)
    Betw = np.mean(Betw_all)
    Dist = 1.0 / Eglob
    Mod_all = bct.modularity_und(mat)
    Mod = np.max(Mod_all)
    Deg = bct.degrees_und(mat)
    Deg_mean = np.mean(Deg)
    density = bct.density_und(mat)
    WM_conn = np.sum(Deg) / (len(inds) * (len(inds) - 1) / 2)
    rows.append({
        'ModuleNumber': module_num,
        'ModuleName': name,
        'IsBiomarker': is_bio,
        'Eglob': Eglob,
        'Ccoef': Ccoef,
        'Betw': Betw,
        'Dist': Dist,
        'Mod': Mod,
        'Deg_mean': Deg_mean,
        'Density': density,
        'WM_connections': WM_conn
    })

summary_df = pd.DataFrame(rows)
print(summary_df)

# ------------------------------
# Step 5b: Whole-network summary
# ------------------------------
Eglob_n = bct.efficiency_bin(final_bin)
Ccoef_all_n = bct.clustering_coef_bu(final_bin)
Ccoef_n = np.mean(Ccoef_all_n)
Betw_all_n = bct.betweenness_bin(final_bin)
Betw_n = np.mean(Betw_all_n)
Dist_n = 1.0 / Eglob_n
Mod_all_n = bct.modularity_und(final_bin)
Mod_n = np.max(Mod_all_n)
Deg_n = bct.degrees_und(final_bin)
Deg_mean_n = np.mean(Deg_n)
density_n = bct.density_und(final_bin)
WM_conn_n = np.sum(Deg_n) / (nvox * (nvox - 1) / 2)

whole_df = pd.DataFrame([{  
    'ModuleNumber': 0,
    'ModuleName': 'WholeNetwork',
    'IsBiomarker': 'n/a',
    'Eglob': Eglob_n,
    'Ccoef': Ccoef_n,
    'Betw': Betw_n,
    'Dist': Dist_n,
    'Mod': Mod_n,
    'Deg_mean': Deg_mean_n,
    'Density': density_n,
    'WM_connections': WM_conn_n
}])

print(whole_df)
