
close all
clear all

%% Set paths

roi.subj.path = fullfile(OUTDIR, "move_masks", PARTICIPANT_LABEL, SESSION_LABEL);
tract.subj.path = fullfile(OUTDIR, "probtrackx", PARTICIPANT_LABEL, SESSION_LABEL, "DWIbiomarker1_modules_all_voxseeds");

%% Step 1: Get voxels and coords for the mask

% Define file/path of mask in native dwi (fslstd)
roi_filename = sprintf("%s_%s_desc-mask_modules_all_index_space-dwi-fslstd.nii.gz", PARTICIPANT_LABEL, SESSION_LABEL);
roi_filepath = fullfile(roi.subj.path, roi_filename);
    % seed/target mask in native DWI (split up and used for probtrackx)
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


%% Step 2: Prepare matrix of path lengths (to be used for distance correction)

% load the fdt lengths data (probtrack output spatial mask of streamline distances)
lengths_filename = sprintf("%s_%s_DWIbiomarker1_fdtlengths_all.nii.gz", PARTICIPANT_LABEL, SESSION_LABEL);
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


%% Step 3: Finalize the connectivity matrix

% load the vox coords
    % note, already has "coor_roi" loaded from Step 1
    %filepath_temp = fullfile(roi.subj.path, 'coor_masks_modules_all_index.txt');
    %coor_roi=load(filepath_temp);

% load the distance matrix
dist_mat=dist_mat_sym
    %filepath_temp = fullfile(tract.subj.path, 'distance_matrix.txt');
    %dist_mat=load(filepath_temp);

% load the fdt data (probtrack output spatial mask of streamline counts)
tracts_filename = sprintf("%s_%s_DWIbiomarker1_fdtpaths_all.nii.gz", PARTICIPANT_LABEL, SESSION_LABEL); % (probtrack output spatial mask of streamline counts)
tracts_filepath = fullfile(tract.subj.path, tract_filename);
tracts_filepath = char(tracts_filepath); % Convert the string scalar to a character vector
tracts_nii = load_untouch_nii(tracts_filepath);
    % d02 (4D matrix 95 x 116 x 101 dimensions of probtrack output in native DWI image)
    % same as d00 above (the ROI mask in DWI space)

% extracts just the matrix image
tracts_img = tracts_nii.img;
        
% initialize empty array
tracts_mat = []; 

% match coords of mask clusters to coords of the tracts
for i = 1:length(idx_roi_all) % loops through all voxels of the coords matrix ("idx_roi_all")
    tracts_mat(:,i)=squeeze(tracts_img(idx_roi_all(i,1),idx_roi_all(i,2), idx_roi_all(i,3),:));

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

% Create symmetric matrix
tracts_mat_sym = (tracts_mat + tracts_mat')/2;
tracts_mat_sym = double(tracts_mat_sym);
    % tracts_mat_sym is a nvox x nvox matrix that is symmetric and redundant with
    % identical values from dti_all above (e.g., dti_all vox 1 = 5675 same
    % as dti_all2 vox1 <-> vox1 = 5675)

% Distance correction
tracts_mat_sym_distcorr = tracts_mat_sym.*dist_mat;
tracts_mat_sym_distcorr(eye(size(tracts_mat_sym_distcorr))~=0)=0; % forces diagonal = 0
    % tracts_mat_sym_distcorr created by multiplying the streamline counts (tracts_mat_sym, 1466
    % x 1466 matrix) with the distances (dist_mat, 1466 x 1466 matrix)

% Normalize (weight) the matrix
tracts_mat_sym_distcorr_norm = weight_conversion(tracts_mat_sym_distcorr,'normalize'); % normalize
    % weight_conversion (download from here: https://github.com/fieldtrip/fieldtrip/blob/master/external/bct/weight_conversion.m)
    % tracts_mat_sym_distcorr_norm created by normalizing the streamline x distance matrix



%% Step 4: Threshold the network matrix based on target density (NEW 4-14-25)

target_density = 0.1;  % desired final graph density

% Step 4a: Get initial binary matrix (no thresholding)
initial_bin_mat = im2bw(tracts_mat_sym_distcorr_norm, 0);  % binarize with thresh = 0
initial_bin_mat = double(initial_bin_mat);
initial_density = density_und(initial_bin_mat);  % compute initial density

% Step 4b: Check if thresholding is needed
if initial_density <= target_density

    % If initial density is already below or equal to target, keep unthresholded
    fprintf('Initial density (%.4f) <= target (%.4f), skipping thresholding.\n', ...
        initial_density, target_density);
    
    tracts_mat_sym_distcorr_norm_bin = initial_bin_mat;
    tracts_mat_sym_distcorr_norm_bin = double(tracts_mat_sym_distcorr_norm_bin);

    % Save final connectivity matrix (symmetric, distance corrected, normalized)
    tracts_mat_sym_distcorr_norm_bin_filename = 'DWIbiomarker1_matrix_sym_distcorr_norm_bin.txt';
    tracts_mat_sym_distcorr_norm_bin_filepath = fullfile(tract.subj.path, tracts_mat_sym_distcorr_norm_bin_filename);
    tracts_mat_sym_distcorr_norm_bin_filepath = char(tracts_mat_sym_distcorr_norm_bin_filepath); % Convert the string scalar to a character vector
    save(tracts_mat_sym_distcorr_norm_bin_filepath, 'tracts_mat_sym_distcorr_norm_bin', '-ascii', '-tabs');

else

    % Perform thresholding loop to find best threshold
    fprintf('Initial density (%.4f) > target (%.4f), performing thresholding.\n', ...
        initial_density, target_density);
    
    D = [];
    thr_rang = (0.0:0.0001:0.3);

    for i = 1:length(thr_rang)
        temp_bin_mat = im2bw(tracts_mat_sym_distcorr_norm, thr_rang(i));
        temp_bin_mat = double(temp_bin_mat);
        D(i) = density_und(temp_bin_mat);
    end

    DD = abs(D - target_density);
    [~, I] = min(DD);  % index of closest match
    thr_final = thr_rang(I);

    % Final binarization with selected threshold
    tracts_mat_sym_distcorr_norm_bin = im2bw(tracts_mat_sym_distcorr_norm, thr_final);
    tracts_mat_sym_distcorr_norm_bin = double(tracts_mat_sym_distcorr_norm_bin);

    fprintf('Applied threshold: %.4f (resulting density: %.4f)\n', ...
        thr_final, D(I));
    
    % Save final connectivity matrix (symmetric, distance corrected, normalized)
    tracts_mat_sym_distcorr_norm_bin_filename = 'DWIbiomarker1_matrix_sym_distcorr_norm_bin.txt';
    tracts_mat_sym_distcorr_norm_bin_filepath = fullfile(tract.subj.path, tracts_mat_sym_distcorr_norm_bin_filename);
    tracts_mat_sym_distcorr_norm_bin_filepath = char(tracts_mat_sym_distcorr_norm_bin_filepath); % Convert the string scalar to a character vector
    save(tracts_mat_sym_distcorr_norm_bin_filepath, 'tracts_mat_sym_distcorr_norm_bin', '-ascii', '-tabs');

end




%% Step 5: calculate summary connectome measures (of all modules and whole network)

%%%%%%%%%%%%%%%%%%%%%%%
% Step 5a (all modules)

% Define module names and biomarker status
module_info = {
    1, 'mPFCventral-amyg', 'no';
    2, 'OFC-amyg-hipp',    'no';
    3, 'mPFCdorsal-amyg-NAc', 'yes'
};

% Initialize summary table
summary_results = [];

% Loop through module numbers 1 to 3
for module_num = 1:3
    % Get the indices for the current module
    module_indices = find(coor_roi(:, 4) == module_num);
    
    % Extract submatrix for the current module
    module_mat = tracts_mat_sym_distcorr_norm_bin(module_indices, module_indices);

    % Compute network metrics
    Eglob = efficiency_bin(module_mat);
    Ccoef_all = clustering_coef_bu(module_mat);
    Ccoef = mean(Ccoef_all);
    Betw_all = betweenness_bin(module_mat);
    Betw = mean(Betw_all);
    Dist = 1 / Eglob;
    Mod_all = modularity_und(module_mat);
    Mod = max(Mod_all);
    Deg_vox = degrees_und(module_mat);
    Deg_mean = mean(Deg_vox);
    density = density_und(module_mat);
    Deg_vox_sum = sum(Deg_vox);
    num_vox = size(module_mat, 1);
    max_edges = num_vox * (num_vox - 1) / 2;
    WM_connections = Deg_vox_sum / max_edges;

    % Append to summary results
    summary_results = [summary_results; {
        module_num, ...
        module_info{module_num, 2}, ...      % module name
        module_info{module_num, 3}, ...      % biomarker status
        Eglob, ...
        Ccoef, ...
        Betw, ...
        Dist, ...
        Mod, ...
        Deg_mean, ...
        density, ...
        WM_connections ...
    }];
    
    % Optionally print intermediate results
    fprintf('Module %d (%s):\n', module_num, module_info{module_num, 2});
    fprintf(' - Global Efficiency: %.4f\n', Eglob);
    fprintf(' - Clustering Coefficient: %.4f\n', Ccoef);
    fprintf(' - Betweenness Centrality: %.4f\n', Betw);
    fprintf(' - Mean Distance: %.4f\n', Dist);
    fprintf(' - Modularity: %.4f\n', Mod);
    fprintf(' - Mean Degree: %.4f\n', Deg_mean);
    fprintf(' - Density: %.4f\n', density);
    fprintf(' - WM Connections: %.4f\n\n', WM_connections);
end

% Convert summary to table for easy viewing
summary_table = cell2table(summary_results, ...
    'VariableNames', {'ModuleNumber', 'ModuleName', 'IsBiomarker', ...
    'Eglob', 'Ccoef', 'Betw', 'Dist', 'Mod', 'Deg_mean', 'Density', 'WM_connections'});

% Display the summary table
disp(summary_table);


%%%%%%%%%%%%%%%%%%%%%%%
% Step 5b (whole network)

% === Append whole-network summary ===

% Calculate whole-network connectome measures
Eglob_network = efficiency_bin(tracts_mat_sym_distcorr_norm_bin);
Ccoef_all_network = clustering_coef_bu(tracts_mat_sym_distcorr_norm_bin);
Ccoef_network = mean(Ccoef_all_network);

try
    Betw_all_network = betweenness_bin(tracts_mat_sym_distcorr_norm_bin);
    Betw_network = mean(Betw_all_network);
catch ME
    warning('Betweenness calculation failed: %s', ME.message);
    Betw_network = NaN;  % or some placeholder
end

    %Betw_all_network = betweenness_bin(tracts_mat_sym_distcorr_norm_bin);
    %Betw_network = mean(Betw_all_network);

Dist_network = 1 / Eglob_network;
Mod_all_network = modularity_und(tracts_mat_sym_distcorr_norm_bin);
Mod_network = max(Mod_all_network);
Deg_vox_network = degrees_und(tracts_mat_sym_distcorr_norm_bin);
Deg_mean_network = mean(Deg_vox_network);
density_network = density_und(tracts_mat_sym_distcorr_norm_bin);
Deg_vox_sum_network = sum(Deg_vox_network);
num_vox_network = size(tracts_mat_sym_distcorr_norm_bin, 1);
max_edges_network = num_vox_network * (num_vox_network - 1) / 2;
WM_connections_network = Deg_vox_sum_network / max_edges_network;

% Append to summary table
summary_results = [summary_results; {
    0, ...                              % ModuleNumber
    'WholeNetwork', ...                % ModuleName
    'n/a', ...                         % IsBiomarker
    Eglob_network, ...
    Ccoef_network, ...
    Betw_network, ...
    Dist_network, ...
    Mod_network, ...
    Deg_mean_network, ...
    density_network, ...
    WM_connections_network ...
}];

% Convert to table
summary_table = cell2table(summary_results, ...
    'VariableNames', {'ModuleNumber', 'ModuleName', 'IsBiomarker', ...
    'Eglob', 'Ccoef', 'Betw', 'Dist', 'Mod', 'Deg_mean', 'Density', 'WM_connections'});

% Display full summary
disp(summary_table);
