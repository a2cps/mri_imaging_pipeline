
close all
clear all

%% Set paths

roi.subj.path = fullfile(OUTDIR, "move_masks", PARTICIPANT_LABEL);
tract.subj.path = fullfile(OUTDIR, "probtrackx", PARTICIPANT_LABEL, SESSION_LABEL, "modules_all_voxseeds");

%% Step 1: Get voxels and coords for the mask

% Define file/path of mask in native dwi (fslstd)
roi_filename = sprintf("modules_all_index_in_%s_DWI_fslstd.nii.gz", PARTICIPANT_LABEL);
roi_filepath = fullfile(roi.subj.path, roi_filename);
    % seed/target mask in native DWI (used for probtrackx)
    % voxel values are the module # to which each voxel belongs

% Mask in native dwi (fslstd) - convert the string scalar to a character vector
fname00 = char(roi_filepath); 

% load mask in native dwi (fslstd)
d00 = load_untouch_nii(fname00); % single matrix

% extract matrix image
dmask = d00.img;

% extracts the matrix dimensions as a row vector
s = size(dmask);

% define number of clusters within the mask
nroi = 3;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% determing the coordinates of roi

% initialize an empty matrix
idx_roi_all = []; 

% idx_roi_all (n x 3 matrix of voxel coords in native DWI (fslstd))
for i = 1:nroi; % loop through the ROIs

    row = []; col = []; idx_roi =[]; % initialize empty matrix
    [row,col] = find(dmask==i);idx_roi(:,1) = row; idx_roi(:,2)  = mod(col,s(2));idx_roi(:,3) = ceil(col/s(2));
    idx_roi_all = [idx_roi_all; idx_roi];

    %  loop creates idx_roi_all (nvox x 3 matrix of voxel coordinates
    %  in native DWI (fslstd) space, where rows are the voxels and 3 cols are the x,y,z coords)

end

% coor_roi (n x 4 matrix of voxel coords in native DWI (fslstd))
for i = 1: length(idx_roi_all); % loop through voxels (rows of idx_roi_all)

    coor_roi(i,1:3) = idx_roi_all(i,1:3); % extracts the coords
    coor_roi(i,4)  = dmask(idx_roi_all(i,1),idx_roi_all(i,2), idx_roi_all(i,3));

    % loop creates coor_roi (n x 4 matrix of vox coords in native
    % DWI space (fslstd), where rows are voxels and first 3 cols are coords
    % (x,y,z) and 4th col is the ROI index #)
    
end

% remove the first voxel (adjust for the mismatch #nvox created from fslmaths -index in Step 2 of entrypoint.sh)
idx_roi_all(1, :) = [];
coor_roi(1, :) = [];

% Save coordinates of mask clusters in native dwi (fslstd)
coor_roi_filename = 'coor_masks_modules_all_index.txt';
coor_roi_filepath = fullfile(roi.subj.path, coor_roi_filename);
coor_roi_filepath = char(coor_roi_filepath); % Convert the string scalar to a character vector
save(coor_roi_filepath, 'coor_roi', '-ascii', '-tabs');


%% Step 2: Prepare matrix of path lengths (to be used for distance correction)

% load the fdt lengths data (probtrack output spatial mask of streamline distances)
lengths_filename = sprintf("%s_%s_probtrackx_voxseeds_fdtlengths_all.nii.gz", PARTICIPANT_LABEL, SESSION_LABEL);
lengths_filepath = fullfile(tract.subj.path, lengths_filename);
lengths_filepath = char(lengths_filepath); % Convert the string scalar to a character vector
lengths_nii = load_untouch_nii(lengths_filepath);
    % d02 (4D matrix of probtrack tract lengths output in native DWI image)
    % same as d00 above (the ROI mask in DWI space)

% extracts just the matrix image
lengths_img = lengths_nii.img;       

% initialize empty array
dist_mat = []; 

% match mask roi coords to tract length voxels
for i = 1:length(idx_roi_all) % loops through all voxels of the coords matrix ("idx_roi_all")
    dist_mat(:,i)=squeeze(lengths_img(idx_roi_all(i,1),idx_roi_all(i,2), idx_roi_all(i,3),:));

        % matches the coords from "idx_roi_all" to the coords of the
        % probtrack spatial output (the 4D merged file of all voxseeds tract lengths) and
        % extracts the voxel value from the probtrack output (from the same
        % voxel in each 3D fdtpaths across the 4D merged file

        % loop creates dti_all (nvox x nvox matrix)

        % Within the loop, the following actions are performed:

            % idx_roi_all(i, :) retrieves the i-th row from idx_roi_all, which contains three indices.
            % These three indices are used to access a specific point in the first three dimensions of the 4D array db.
    
            % db(idx_roi_all(i,1), idx_roi_all(i,2), idx_roi_all(i,3), :) extracts a 1D array from the 4th dimension of db at the specified 3D coordinates.
    
            % squeeze removes any singleton dimensions from the extracted array, ensuring it becomes a column vector.
    
            % dti_all(:,i) = ... assigns this column vector to the i-th column of dti_all.

        % Note, given that voxseeds outputs get fslmerge into 4D file, this
        % loop extracts the voxel value from all 3D images (the probtrackx
        % fslmaths for all seed voxel) and builds up the dti_all
        % connectivity matrix
end

% Create symmetric matrix
dist_mat_sym = (dist_mat + dist_mat')/2;
dist_mat_sym = double(dist_mat_sym);
dist_mat_sym(eye(size(dist_mat_sym))~=0)=0;

% Save matrix of lengths in native dwi (fslstd)
dist_mat_sym_filename = 'distance_matrix.txt';
dist_mat_sym_filepath = fullfile(tract.subj.path, dist_mat_sym_filename);
dist_mat_sym_filepath = char(dist_mat_sym_filepath); % Convert the string scalar to a character vector
save(dist_mat_sym_filepath, 'dist_mat_sym', '-ascii', '-tabs');


%% Step 3: Finalize the connectivity matrix

% load the vox coords
filepath_temp = fullfile(roi.subj.path, 'coor_masks_modules_all_index.txt');
coor_roi=load(filepath_temp);

% load the distance matrix
filepath_temp = fullfile(tract.subj.path, 'distance_matrix.txt');
dist_mat=load(filepath_temp);

% load the fdt data (probtrack output spatial mask of streamline counts)
tracts_filename = sprintf("%s_%s_probtrackx_voxseeds_fdtpaths_all.nii.gz", PARTICIPANT_LABEL, SESSION_LABEL); % (probtrack output spatial mask of streamline counts)
tracts_filepath = fullfile(tract.subj.path, tract_filename);
tracts_filepath = char(tracts_filepath); % Convert the string scalar to a character vector
tracts_nii = load_untouch_nii(fname02);
    % d02 (4D matrix 95 x 116 x 101 dimensions of probtrack output in native DWI image)
    % same as d00 above (the ROI mask in DWI space)

% extracts just the matrix image
tracts_img = tracts_nii.img;
        
% initialize empty array
tracts_mat = []; 

% match coords of mask clusters to coords of the tracts
for i = 1:length(idx_roi_all) % loops through all voxels of the coords matrix ("idx_roi_all")
    tracts_mat(:,i)=squeeze(db(idx_roi_all(i,1),idx_roi_all(i,2), idx_roi_all(i,3),:));

        % matches the coords from "idx_roi_all" to the coords of the
        % probtrack spatial output (the 4D merged file of all voxseeds paths) and
        % extracts the voxel value from the probtrack output (from the same
        % voxel in each 3D fdtpaths across the 4D merged file)

        % loop above creates dti_all (nvox x nvox matrix)

        % Within the loop, the following actions are performed:
            % idx_roi_all(i, :) retrieves the i-th row from idx_roi_all, which contains three indices.
            % These three indices are used to access a specific point in the first three dimensions of the 4D array db.
            % db(idx_roi_all(i,1), idx_roi_all(i,2), idx_roi_all(i,3), :) extracts a 1D array from the 4th dimension of db at the specified 3D coordinates.
            % squeeze removes any singleton dimensions from the extracted array, ensuring it becomes a column vector.
            % tracts_mat_sym(:,i) = ... assigns this column vector to the i-th column of dti_all.
    
            % Note, given that voxseeds outputs get fslmerge into 4D file, this
            % loop extracts the voxel value from all 3D images (the probtrackx
            % fslmaths for all seed voxel) and builds up the dti_all
            % connectivity matrix
end

% save tracts matrix (unsymmetric, not distance corrected, not normalized)
tracts_mat_filename = 'tracts_matrix.txt';
tracts_mat_filepath = fullfile(tract.subj.path, tracts_mat_filename);
tracts_mat_filepath = char(tracts_mat_filepath); % Convert the string scalar to a character vector
save(tracts_mat_filepath, 'tracts_mat', '-ascii', '-tabs');

% Create symmetric matrix
tracts_mat_sym = (tracts_mat + tracts_mat')/2;
tracts_mat_sym = double(tracts_mat_sym);
    % tracts_mat_sym is a nvox x nvox matrix that is symmetric and redundant with
    % identical values from dti_all above (e.g., dti_all vox 1 = 5675 same
    % as dti_all2 vox1 <-> vox1 = 5675)

% Save tract matrix (symmetric, not distance corrected, not normalized)
tracts_mat_sym_filename = 'tracts_matrix_sym.txt';
tracts_mat_sym_filepath = fullfile(tract.subj.path, tracts_mat_sym_filename);
tracts_mat_sym_filepath = char(tracts_mat_sym_filepath); % Convert the string scalar to a character vector
save(tracts_mat_sym_filepath, 'tracts_mat_sym', '-ascii', '-tabs');

% Distance correction
tracts_mat_sym_distcorr = tracts_mat_sym.*dist_mat;
tracts_mat_sym_distcorr(eye(size(tracts_mat_sym_distcorr))~=0)=0; % forces diagonal = 0
    % tracts_mat_sym_distcorr created by multiplying the streamline counts (tracts_mat_sym, 1466
    % x 1466 matrix) with the distances (dist_mat, 1466 x 1466 matrix)

% Save tract matrix (symmetric, distance corrected, not normalized)
tracts_mat_sym_distcorr_filename = 'tracts_matrix_sym_distcorr.txt';
tracts_mat_sym_distcorr_filepath = fullfile(tract.subj.path, tracts_mat_sym_distcorr_filename);
tracts_mat_sym_distcorr_filepath = char(tracts_mat_sym_distcorr_filepath); % Convert the string scalar to a character vector
save(tracts_mat_sym_distcorr_filepath, 'tracts_mat_sym_distcorr', '-ascii', '-tabs');

% Normalize (weight) the matrix
tracts_mat_sym_distcorr_norm = weight_conversion(tracts_mat_sym_distcorr,'normalize'); % normalize
    % weight_conversion (download from here: https://github.com/fieldtrip/fieldtrip/blob/master/external/bct/weight_conversion.m)
    % tracts_mat_sym_distcorr_norm created by normalizing the streamline x distance matrix

% Save tract matrix (symmetric, distance corrected, normalized)
tracts_mat_sym_distcorr_norm_filename = 'tracts_matrix_sym_distcorr_norm.txt';
tracts_mat_sym_distcorr_norm_filepath = fullfile(tract.subj.path, tracts_mat_sym_distcorr_norm_filename);
tracts_mat_sym_distcorr_norm_filepath = char(tracts_mat_sym_distcorr_norm_filepath); % Convert the string scalar to a character vector
save(tracts_mat_sym_distcorr_norm_filepath, 'tracts_mat_sym_distcorr_norm', '-ascii', '-tabs');


%% Step 4: Threshold the network matrix based on target density

% Note, tries to find a threshold that brings a certain density measure D as close as possible to a target_density.
% Note, if observed density < target density at thresh = 0, then the matrix remains unthresholded

% desired density of final graph
target_density = 0.1;

% initialize matrix
D = [];

% threshold range
thr_rang = (0.0:0.0001:0.3);

% test thresholds
for i = 1:length(thr_rang);

   tracts_mat_sym_distcorr_norm_bin=im2bw(tracts_mat_sym_distcorr_norm,thr_rang(i)); % binarize with current threshold
   tracts_mat_sym_distcorr_norm_bin=double(tracts_mat_sym_distcorr_norm_bin); % ensures double matrix
   d = density_und(tracts_mat_sym_distcorr_norm_bin); % calculates density of threshed/binarized graph
   D = [D;d]; % adds density (d) from current thresh to array of densities across all thresholds

end

% initialize empty arrays
I =[]; J=[]; DD=[]; 

% calculates the absolute difference between the density D and the target_density.
DD = abs(D - target_density);

% finds the indices of the elements in DD that are equal to the minimum value of DD
[I,J] = find(DD(:) == min(DD));

% select final threshold
thr_final = thr_rang(I(1));
    % This line selects the threshold value corresponding to the first index in I. 
    % It uses I(1) to get the index of the first occurrence of the minimum difference and then uses this index 
    % to select the corresponding threshold from the thr_rang array.


% threshold the matrix based on this final threshold (if thr_final = 0, then no change)
tracts_mat_sym_distcorr_norm_bin=im2bw(tracts_mat_sym_distcorr_norm,thr); % binarize with current threshold
tracts_mat_sym_distcorr_norm_bin=double(tracts_mat_sym_distcorr_norm_bin); % ensures double matrix


%% Step 5: calculate summary connectome measures (of whole network)

% calculate various connectome measures

Eglob_network = efficiency_bin(tracts_mat_sym_distcorr_norm_bin); %computing global efficiency

Ccoef_all_network = clustering_coef_bu(tracts_mat_sym_distcorr_norm_bin);
Ccoef_network = mean(Ccoef_all_network); % mean (global)  clustering coef

Betw_all_network = betweenness_bin(tracts_mat_sym_distcorr_norm_bin);
Betw_network = mean(Betw_all_network); % computing the in betweeness

Dist_network = 1/Eglob_network; % estimating the mean distance of the network

Mod_all_network = modularity_und(tracts_mat_sym_distcorr_norm_bin);
Mod_network = max(Mod_all_network); % computing the modularity

% calculates all degrees
Degree_vox_network = degrees_und(tracts_mat_sym_distcorr_norm_bin);  
    % calculate the degree of each node in an undirected graph. The degree of a node is the number of edges connected to it
    % note, this counts bidirections twice! (since it's computed on the
    % whole matrix instead of the upper or lower half)

% calculates average degree
Deg_network = mean(Degree_vox_network);
    % note, Deg_vox = mean(Degree_vox); was not part of original code but
    % I added it because it provides an average degree (single value) for
    % each subject (to be used as the biomarker), instead of a separate
    % degree for each voxel (produced by degrees_und)

% calculates density
d_network = density_und(tracts_mat_sym_distcorr_norm_bin);
    % num edges (in upper triangle of matrix, since it's symmetric) / N(N-1)/2

% print summary measures (of whole network)
Eglob_network
Ccoef_network
Betw_network
Dist_network
Mod_network
Degree_vox_network
Deg_network
d_network




%% Step 6: calculate summary connectome measures (of biomarker module)

% identify the biomarker module
biomarker_module_indices = find(coor_roi(:, 4) == 3); % Rows where the 4th column equals 3

% Extract rows and columns corresponding to biomarker module
biomarker_module_mat = tracts_mat_sym_distcorr_norm_bin(biomarker_module_indices, biomarker_module_indices);

% calculate various connectome measures

Eglob_biomarker = efficiency_bin(biomarker_module_mat); %computing global efficiency

Ccoef_all_biomarker = clustering_coef_bu(biomarker_module_mat);
Ccoef_biomarker = mean(Ccoef_all_biomarker); % mean (global)  clustering coef

Betw_all_biomarker = betweenness_bin(biomarker_module_mat);
Betw_biomarker = mean(Betw_all_biomarker); % computing the in betweeness

Dist_biomarker = 1/Eglob_biomarker; % estimating the mean distance of the network

Mod_all_biomarker = modularity_und(biomarker_module_mat);
Mod_biomarker = max(Mod_all_biomarker); % computing the modularity

% calculates all degrees
Degree_vox_biomarker = degrees_und(biomarker_module_mat);  
    % calculate the degree of each node in an undirected graph. The degree of a node is the number of edges connected to it
    % note, this counts bidirections twice! (since it's computed on the
    % whole matrix instead of the upper or lower half)

% calculates average degree
Deg_biomarker = mean(Degree_vox_biomarker);
    % note, Deg_vox = mean(Degree_vox); was not part of original code but
    % I added it because it provides an average degree (single value) for
    % each subject (to be used as the biomarker), instead of a separate
    % degree for each voxel (produced by degrees_und)

% calculates density
d_biomarker = density_und(biomarker_module_mat);
    % num edges (in upper triangle of matrix, since it's symmetric) / N(N-1)/2

% calculate biomarker final metric ("WM connections" in Vachon-Presseau et al. 2016)
Deg_vox_sum_biomarker = sum(Degree_vox_biomarker); % total of edges
num_vox_biomarker = size(biomarker_module_mat, 1);
max_edges_biomarker = num_vox_biomarker*(num_vox_biomarker-1)/2;
WM_connections_biomarker = Deg_vox_sum_biomarker / max_edges_biomarker;

% print summary measures (of whole network)
Eglob_biomarker
Ccoef_biomarker
Betw_biomarker
Dist_biomarker
Mod_biomarker
Degree_vox_biomarker
Deg_biomarker
d_biomarker
WM_connections_biomarker



