#!/usr/bin/env bash

main (){

    local PARTICIPANT_LABEL="${1}"
    local SESSION_LABEL="${2}"
    local QSIPREPDIR="${3}"
    local QSIRECONDIR="${4}"
    local ROIPREPDIR="${5}"
    local OUTDIR="${6}"
    local LICENSE="${7}"

    ### Questions...

    ## Should bedpostx be it's own app? It takes ~30-60min (using gpu version) or > 20 hrs (non gpu)


    ###########################################################################################################
    ## STEP ?? : Prepare mask files (before moving into subjects)

        ## This is done only once, not subject-wise, so where to put??


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
    --interpolation "${transform}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output}".nii.gz

    ## Binarize the full mask
    fslmaths ${output}.nii.gz -bin ${output}_bin.nii.gz

    ###########################################################################################################
    ## STEP 0: Define paths/files (qsiprep and qsirecon-FSL)

    ## Redefine subject paths
    local dir_qsirecon="${QSIRECONDIR}"/"${PARTICIPANT_LABEL}"/"${SESSION_LABEL}"/dwi
    local dir_qsiprep_dwi="${QSIPREPDIR}"/"${PARTICIPANT_LABEL}"/"${SESSION_LABEL}"/dwi
    local dir_qsiprep_anat="${QSIPREPDIR}"/"${PARTICIPANT_LABEL}"/anat

    ## Define qsiprep files
    local fname_qsiprep_anat="${PARTICIPANT_LABEL}"_desc-preproc_T1w
    local fname_qsiprep_anat_mask="${PARTICIPANT_LABEL}"_desc-brain_mask
    local fname_qsiprep_xfm_mni2dwi="${PARTICIPANT_LABEL}"_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm
    local fname_qsiprep_dwi="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_desc-preproc_dwi
    local fname_qsiprep_dwi_ref="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_dwiref
    local fname_qsiprep_dwi_mask="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_desc-brain_mask

    local qsiprep_anat="${dir_qsiprep_anat}"/"${fname_qsiprep_anat}".nii.gz
    local qsiprep_anat_mask="${dir_qsiprep_anat}"/"${fname_qsiprep_anat_mask}".nii.gz
    local qsiprep_xfm_mni2dwi="${dir_qsiprep_anat}"/"${fname_qsiprep_xfm_mni2dwi}".h5
    local qsiprep_dwi="${dir_qsiprep_dwi}"/"${fname_qsiprep_dwi}".nii.gz
    local qsiprep_dwi_ref="${dir_qsiprep_dwi}"/"${fname_qsiprep_dwi_ref}".nii.gz
    local qsiprep_dwi_mask="${dir_qsiprep_dwi}"/"${fname_qsiprep_dwi_mask}".nii.gz

    ## Define qsireconFSL files
    local fname_qsireconFSL_mask="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_mask
    local fname_qsireconFSL_dwi="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_dwi

    local qsireconFSL_mask="${dir_qsirecon}"/"${fname_qsireconFSL_mask}".nii.gz
    local qsireconFSL_dwi="${dir_qsirecon}"/"${fname_qsireconFSL_dwi}".nii.gz
    local qsireconFSL_bvals="${dir_qsirecon}"/"${fname_qsireconFSL_dwi}".bval
    local qsireconFSL_bvecs="${dir_qsirecon}"/"${fname_qsireconFSL_dwi}".bvec

    ###########################################################################################################
    ## STEP 1: Move masks from MNI to native (preproc)

    ## Define mask files
    local mask_modall_pref="modules_all"
    local mask_index_MNI1mm="${ROIPREPDIR}"/"${mask_modall_pref}"_in_MNI152NLin2009cAsym_brain.nii.gz
    local mask_bin_MNI1mm="${ROIPREPDIR}"/"${mask_modall_pref}"_in_MNI152NLin2009cAsym_brain_bin.nii.gz

    ## Create output dir
    local dir_move_masks="${OUTDIR}"/move_masks/"${PARTICIPANT_LABEL}"
    mkdir -p "${dir_move_masks}"

    ## Define variables
    local fname_mask_pref="${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_space-T1w_desc-mask
    local mask_index_pref="modules_all_index" # created/used here
    local mask_bin_pref="modules_all_bin" # created/used here

    ## 1a: Move mask (bin) to native anat (preproc)

    local ref="${qsiprep_anat}"
    local transform="${qsiprep_xfm_mni2dwi}"
    local mask="${mask_bin_MNI1mm}"
    local output_T1w="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_pref}"_in_T1w
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
    local output_dwi_bin="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_bin_pref}"_in_dwi
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    antsApplyTransforms -d 3 \
    -i "${mask}" \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output_dwi_bin}".nii.gz

    fslswapdim "${output_dwi_bin}".nii.gz x -y z "${output_dwi_bin}"_fslstd.nii.gz
    fslorient -swaporient "${output_dwi_bin}"_fslstd.nii.gz


    ## 1c: Move mask (index) to native dwi (preproc) and reorient to qsirecon-FSL

    local ref="${qsiprep_dwi_ref}"
    local transform="${qsiprep_xfm_mni2dwi}"
    local mask="${mask_index_MNI1mm}"
    local output_dwi_index="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_index_pref}"_in_dwi
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    antsApplyTransforms -d 3 \
    -i "${mask}" \
    --interpolation "${interp}" \
    -t "${transform}" \
    -r "${ref}" \
    -o "${output_dwi_index}".nii.gz

    ## 1c: Reorient mask in native (preproc) dwi to match qsirecon-FSL
    fslswapdim "${output_dwi_index}".nii.gz x -y z "${output_dwi_index}"_fslstd.nii.gz
    fslorient -swaporient "${output_dwi_index}"_fslstd.nii.gz



    ###########################################################################################################
    ## STEP 2: Split mask (native DWI fslstd) into separate voxel seed files

    ## create output dir
    local dir_split_masks="${dir_move_masks}"/mask_voxels
    mkdir -p "${dir_split_masks}"

    ## binary mask in native DWI fslstd
    local mask_pref="${dir_move_masks}"/"${fname_mask_pref}"_"${mask_bin_pref}"_in_dwi_fslstd

    ## add voxelwise index to mask
    fslmaths "${mask_pref}".nii.gz -index "${mask_pref}"_voxindex.nii.gz

    ## get number of voxels by finding max voxel index
    local num_voxels=$(fslstats "${mask_pref}"_voxindex.nii.gz -R | awk '{print $2}')
    local num_voxels="${num_voxels:0:5}" # remove the ".0000"

    ## split mask into separate voxels

    for (( i=1; i<=num_voxels; i++ )); do

    echo $i

    # Extract each voxel into a separate nii file (binarized output)
    fslmaths "${mask_pref}"_voxindex.nii.gz -thr "${i}" -uthr "${i}" -bin "${mask_pref}"_voxindex_vox-"${i}"_bin.nii.gz

    # Extract each voxel into a separate nii file (indexed output)
    mkdir -p "${split_dir}"/vox_index
    fslmaths "${mask_pref}"_voxindex.nii.gz -thr "${i}" -uthr "${i}" "${mask_pref}"_voxindex_vox-"${i}"_index.nii.gz

    done


    ###########################################################################################################
    ## STEP 4: Probtrackx (tractography, voxelwise seeds)

    ## Define input dir
    local dir_probtrackx_input="${dir_bedpostx_input}".bedpostX

    ## Define output dir
    local dir_probtrackx_output="${OUTDIR}"/probtrackx/"${PARTICIPANT_LABEL}"/"${SESSION_LABEL}"/modules_all_voxseeds
    mkdir -p "${dir_probtrackx_output}"

    ## Define mask
    local mask="${dir_bedpostx_input}"/nodif_brain_mask.nii.gz
    

    ## Run voxelwise tractography
    for (( i=1; i<=num_voxels; i++ )); do # note, num_voxels created in Step 2

    echo "running voxel " "${i}"

    local seed="${dir_split_masks}"/"${mask_pref}"_voxindex_vox-"${i}"_bin.nii.gz
    local tractdir="${dir_probtrackx_output}"/vox-${i}
        mkdir -p "${tractdir}"

    probtrackx2 -x ${seed} -l --onewaycondition -c 0.2 -S 2000 --steplength=0.5 -P 5000 --fibthresh=0.01 --distthresh=0.0 --sampvox=0.0 --forcedir --opd --ompl -s "${dir_probtrackx_input}"/merged -m "${mask}" --dir="${tractdir}" --modeuler
        ## not including distance correction (would be --pd), doing in matlab instead
        
    done

    ## NOTES

        ## will need to remove all voxelwise tract outputs after postproc and merging
        ## rm -R ${probtrackxdir}/modules_all_voxseeds/vox-*


    ###########################################################################################################
    ## STEP 5: Postprocessing of probtrackx outputs

    ## 5a: Reorient to qsiprep (space-T1w)

    for (( i=1; i<=num_voxels; i++ )); do

    echo "voxel " "${i}"

    local tractdir="${dir_probtrackx_output}"/modules_all_voxseeds/vox-${i}
    local tract_paths="${tractdir}"/fdt_paths
    local tract_lengths="${tractdir}"/fdt_paths_lengths

    ## convert tract paths from dwi (fslstd) to dwi (qsiprep)
    fslswapdim "${tract_paths}".nii.gz x -y z "${tract_paths}"_space-T1w.nii.gz
    fslorient -swaporient "${tract_paths}"_space-qsiprep.nii.gz

    ## convert tract lengths from dwi (fslstd) to dwi (qsiprep)
    fslswapdim "${tract_lengths}".nii.gz x -y z "${tract_lengths}"_space-T1w.nii.gz
    fslorient -swaporient "${tract_lengths}"_space-qsiprep.nii.gz

    done

    ## 5b: Merge into 4D files

    ## merge all (fdt_paths)
    output="${dir_probtrackx_output}"/"${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_probtrackx_voxseeds_fdtpaths_all.nii.gz
    fslmerge -t "${output}" "${dir_probtrackx_output}"/vox-*/fdt_paths.nii.gz

    ## merge all (fdt_lengths)
    output="${dir_probtrackx_output}"/"${PARTICIPANT_LABEL}"_"${SESSION_LABEL}"_probtrackx_voxseeds_fdtlengths_all.nii.gz
    fslmerge -t "${output}" "${dir_probtrackx_output}"/vox-*/fdt_paths_lengths.nii.gz

}

export -f main

main "$@"