#!/bin/bash

set -ex

main (){

    local -r SUB=${1}
    local -r SES=${2}
    local -r QSIPREPDIR=${3}
    local -r BEDPOSTXDIR=${4}
    local -r OUTDIR=${5}
    local -r ROIPREPDIR=${6:-/opt/tapis/rois}

    mkdir -p "${OUTDIR}"
    local -r participant_label=sub-"${SUB}"
    local -r session_label=ses-"${SES}"

    ###########################################################################################################
    ## STEP 1: Define paths/files (qsiprep and qsirecon-FSL)

    ## Redefine subject paths
    local -r qsiprep_participant="${QSIPREPDIR}"/"${participant_label}"
    local -r dir_qsiprep_dwi="${qsiprep_participant}"/"${session_label}"/dwi
    local -r dir_qsiprep_anat="${qsiprep_participant}"/anat

    ## Define qsiprep files
    local -r qsiprep_xfm_mni2dwi="${dir_qsiprep_anat}"/"${participant_label}"_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5
    local -r qsiprep_dwi_ref="${dir_qsiprep_dwi}"/"${participant_label}"_"${session_label}"_space-T1w_dwiref.nii.gz

    ###########################################################################################################
    ## STEP 2: Move masks from MNI to native (preproc)

    ## Create output dir
    local -r dir_move_masks="${OUTDIR}"/move_masks/"${participant_label}"/"${session_label}"/dwi
    mkdir -p "${dir_move_masks}"

    ## Move mask (index) to native dwi (preproc) and reorient to qsirecon-FSL
    local -r dwi_ind="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwi_desc-modules_dseg.nii.gz
    local -r dwifslstd_ind="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-modules_dseg.nii.gz

    # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)
    antsApplyTransforms -d 3 \
        -i "${ROIPREPDIR}"/modules_all_in_MNI152NLin2009cAsym_brain.nii.gz \
        --interpolation NearestNeighbor \
        -t "${qsiprep_xfm_mni2dwi}" \
        -r "${qsiprep_dwi_ref}" \
        -o "${dwi_ind}"

    ## Reorient mask in native (preproc) dwi to match qsirecon-FSL
    fslswapdim "${dwi_ind}" x -y z "${dwifslstd_ind}"
    fslorient -swaporient "${dwifslstd_ind}"

    ## put each roi into separate nifti for use by probtrackx2
    local -r mask0="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-module0_dseg.nii.gz
    local -r mask1="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-module1_dseg.nii.gz
    local -r mask2="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-module2_dseg.nii.gz
    fslmaths "${dwifslstd_ind}" -uthr 1 -bin "${mask0}"
    fslmaths "${dwifslstd_ind}" -thr 2 -uthr 2 -bin "${mask1}"
    fslmaths "${dwifslstd_ind}" -thr 3 -bin "${mask2}"
    rm "${dwifslstd_ind}"
    local -r masks="${dir_move_masks}"/"${participant_label}"_"${session_label}"_masks
    echo "${mask0} ${mask1} ${mask2}" > "${masks}"

    ###########################################################################################################
    ## STEP 3: Probtrackx (tractography, voxelwise seeds)

    local -r bedpost_subses="${BEDPOSTXDIR}"/"${participant_label}"/"${session_label}"/dwi.bedpostx
    
    ## Run voxelwise tractography
    local -r prob_out="${OUTDIR}/probtrackx/${participant_label}/${session_label}/dwi"
    probtrackx2 \
        -x "${masks}" \
        -l \
        --onewaycondition \
        -c 0.2 \
        -S 2000 \
        --steplength=0.5 \
        -P 5000 \
        --fibthresh=0.01 \
        --distthresh=0.0 \
        --sampvox=0.0 \
        --forcedir \
        --opd \
        --pd \
        -s "${bedpost_subses}"/merged \
        -m "${bedpost_subses}"/nodif_brain_mask.nii.gz \
        --dir="${prob_out}" \
        --modeuler \
        --omatrix1

    gzip "${prob_out}"/fdt_matrix1.dot

    echo "finished probtrackx"

}

export -f main

main "$@"
