#!/usr/bin/env bash

main (){

    local PARTICIPANT_LABEL="${1}"
    local SESSION_LABEL="${2}"
    local QSIPREPDIR="${3}"
    local BEDPOSTXDIR="${4}"
    local ROIPREPDIR="${5}"
    local OUTDIR="${6}"
    
    mkdir -p "${OUTDIR}"

    ###########################################################################################################
    ## STEP 0: Prepare mask files (before moving into subjects)

        ## This is done only once, not subject-wise, does it make sense to include here or can it be run separately just once?

        ## $roiprepdir is in my /shared/maj folder, should there be an official product dir for these?

    ## Resample/register the original masks from old 4mm MNI to new 1mm MNI
    local mask_modall_pref="modules_all"
    local input="${ROIPREPDIR}"/"${mask_modall_pref}"
    local ref="${ROIPREPDIR}"/tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w.nii.gz
    local transform="${ROIPREPDIR}"/tpl-MNI152NLin2009cAsym_from-MNI152NLin6Asym_mode-image_xfm.h5
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)
    local refname="MNI152NLin2009cAsym_brain"
    local output="${input}"_in_"${refname}"

    antsApplyTransforms -d 3 \
    -i "${input}".nii.gz \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output}".nii.gz

    ## Binarize the full mask
    fslmaths ${output}.nii.gz -bin ${output}_bin.nii.gz

    ###########################################################################################################
    ## STEP 1: Define paths/files (qsiprep and qsirecon-FSL)

    ## Redefine subject paths
    local dir_qsiprep_dwi="${QSIPREPDIR}"/"${PARTICIPANT_LABEL}"/"${SESSION_LABEL}"/dwi
    local dir_qsiprep_anat="${QSIPREPDIR}"/"${PARTICIPANT_LABEL}"/anat

    ## Define qsiprep files
    local fname_qsiprep_anat="${PARTICIPANT_LABEL}"_desc-preproc_T1w
    local fname_qsiprep_xfm_mni2dwi="${PARTICIPANT_LABEL}"_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm
    local fname_qsiprep_dwi_ref="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_dwiref

    local qsiprep_anat="${dir_qsiprep_anat}"/"${fname_qsiprep_anat}".nii.gz
    local qsiprep_xfm_mni2dwi="${dir_qsiprep_anat}"/"${fname_qsiprep_xfm_mni2dwi}".h5
    local qsiprep_dwi_ref="${dir_qsiprep_dwi}"/"${fname_qsiprep_dwi_ref}".nii.gz


    ###########################################################################################################
    ## STEP 2: Move masks from MNI to native (preproc)

    ## Define mask files
    local mask_modall_pref="modules_all"
    local mask_index_MNI1mm="${ROIPREPDIR}"/"${mask_modall_pref}"_in_MNI152NLin2009cAsym_brain.nii.gz
    local mask_bin_MNI1mm="${ROIPREPDIR}"/"${mask_modall_pref}"_in_MNI152NLin2009cAsym_brain_bin.nii.gz

    ## Create output dir
    local dir_move_masks="${OUTDIR}"/move_masks/"${PARTICIPANT_LABEL}"/"${SESSION_LABEL}"
    mkdir -p "${dir_move_masks}"

    ## Define variables
    local fname_mask_pref="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_desc-mask
    local mask_index_pref="modules_all_index" # created/used here
    local mask_bin_pref="modules_all_bin" # created/used here

    ## 1a: Move mask (bin) to native anat (preproc)

    local ref="${qsiprep_anat}"
    local transform="${qsiprep_xfm_mni2dwi}"
    local mask="${mask_bin_MNI1mm}"
    local output_T1w="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_bin_pref}"_space-T1w
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    antsApplyTransforms -d 3 \
    -i "${mask}" \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output_T1w}".nii.gz

    ## 1b: Move mask (bin) to native dwi (preproc) and reorient to qsirecon-FSL

    local ref="${qsiprep_dwi_ref}"
    local transform="${qsiprep_xfm_mni2dwi}"
    local mask="${mask_bin_MNI1mm}"
    local output_dwi_bin="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_bin_pref}"_space-dwi
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    antsApplyTransforms -d 3 \
    -i "${mask}" \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output_dwi_bin}".nii.gz

    ## Reorient mask in native (preproc) dwi to match qsirecon-FSL
    fslswapdim "${output_dwi_bin}".nii.gz x -y z "${output_dwi_bin}"-fslstd.nii.gz
    fslorient -swaporient "${output_dwi_bin}"-fslstd.nii.gz

    ## 1c: Move mask (index) to native anat (preproc)

    local ref="${qsiprep_anat}"
    local transform="${qsiprep_xfm_mni2dwi}"
    local mask="${mask_index_MNI1mm}"
    local output_T1w="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_index_pref}"_space-T1w
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    antsApplyTransforms -d 3 \
    -i "${mask}" \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output_T1w}".nii.gz

    ## 1d: Move mask (index) to native dwi (preproc) and reorient to qsirecon-FSL

    local ref="${qsiprep_dwi_ref}"
    local transform="${qsiprep_xfm_mni2dwi}"
    local mask="${mask_index_MNI1mm}"
    local output_dwi_index="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_index_pref}"_space-dwi
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    antsApplyTransforms -d 3 \
    -i "${mask}" \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output_dwi_index}".nii.gz

    ## Reorient mask in native (preproc) dwi to match qsirecon-FSL
    fslswapdim "${output_dwi_index}".nii.gz x -y z "${output_dwi_index}"-fslstd.nii.gz
    fslorient -swaporient "${output_dwi_index}"-fslstd.nii.gz



    ###########################################################################################################
    ## STEP 3: Split mask (native DWI fslstd) into separate voxel seed files

    ## create output dir
    local dir_split_masks="${dir_move_masks}"/seed_voxels
    mkdir -p "${dir_split_masks}"

    ## define binary mask in native DWI fslstd
    local mask_pref="${fname_mask_pref}"_"${mask_bin_pref}"_space-dwi-fslstd

    ## add voxelwise index to mask
    fslmaths "${dir_move_masks}"/"${mask_pref}".nii.gz -index "${dir_move_masks}"/"${mask_pref}"_voxindex.nii.gz

    ## get number of voxels by finding max voxel index
    local num_voxels=$(fslstats ""${dir_move_masks}"/${mask_pref}"_voxindex.nii.gz -R | awk '{print $2}')
    local num_voxels="${num_voxels:0:5}" # remove the ".0000"

    ## split mask into separate voxels

        ## QUESTION: should this be split into batches / parallelized?

    for (( i=1; i<=num_voxels; i++ )); do

    echo $i

    # Extract each voxel into a separate nii file (binarized output)
    fslmaths "${dir_move_masks}"/"${mask_pref}"_voxindex.nii.gz -thr "${i}" -uthr "${i}" -bin "${dir_split_masks}"/"${mask_pref}"_voxindex_vox-"${i}"_bin.nii.gz

    # Extract each voxel into a separate nii file (indexed output)

    fslmaths "${dir_move_masks}"/"${mask_pref}"_voxindex.nii.gz -thr "${i}" -uthr "${i}" "${dir_split_masks}"/"${mask_pref}"_voxindex_vox-"${i}"_index.nii.gz

    done


    ###########################################################################################################
    ## STEP 4: Probtrackx (tractography, voxelwise seeds)

    ## Define output dir
    local dir_probtrackx_output="${OUTDIR}"/probtrackx/"${PARTICIPANT_LABEL}"/"${SESSION_LABEL}"/DWIbiomarker1_modules_all_voxseeds
    mkdir -p "${dir_probtrackx_output}"

    ## define binary mask in native DWI fslstd
    local mask_pref="${fname_mask_pref}"_"${mask_bin_pref}"_space-dwi-fslstd


    ## Run voxelwise tractography
    for (( i=1; i<=num_voxels; i++ )); do # note, num_voxels created in Step 2

    echo "running voxel " "${i}"

    # Define mask
    local mask="${BEDPOSTXDIR}"/nodif_brain_mask.nii.gz

    # Define seed
    local seed="${dir_split_masks}"/"${mask_pref}"_voxindex_vox-"${i}"_bin.nii.gz

    # Define output tract dir
    local tractdir="${dir_probtrackx_output}"/vox-${i}
        mkdir -p "${tractdir}"

    # Run tractography
    probtrackx2 -x ${seed} -l --onewaycondition -c 0.2 -S 2000 --steplength=0.5 -P 5000 --fibthresh=0.01 --distthresh=0.0 --sampvox=0.0 --forcedir --opd --ompl -s "${BEDPOSTXDIR}"/merged -m "${mask}" --dir="${tractdir}" --modeuler
        ## not including distance correction (would be --pd), doing in matlab instead
        
    done


    ###########################################################################################################
    ## STEP 5: Postprocessing of probtrackx outputs

        ## NOTE: no need to reorient to space-T1w first (ideal to keep in native tractography space, but have code if needed)

    ## Merge into 4D files

    ## merge all (fdt_paths)
    output="${dir_probtrackx_output}"/"${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_DWIbiomarker1_fdtpaths_all.nii.gz
    fslmerge -t ${output} $(ls -d -v "${dir_probtrackx_output}"/vox-*/fdt_paths.nii.gz)

    ## merge all (fdt_lengths)
    output="${dir_probtrackx_output}"/"${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_DWIbiomarker1_fdtlengths_all.nii.gz
    fslmerge -t ${output} $(ls -d -v "${dir_probtrackx_output}"/vox-*/fdt_paths_lengths.nii.gz)


    ###########################################################################################################
    ## STEP 6: Cleanup files

    # Remove seed voxels (>10k per subj)
    rm -R "${dir_split_masks}"

    # Remove voxelwise probtrackx outputs (>10k per subj)
    rm -R "${dir_probtrackx_output}"/vox-*

}

export -f main

main "$@"