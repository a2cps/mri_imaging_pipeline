#!/usr/bin/env bash

main (){
    local BIDSDIR="${1}"
    local WORKDIR="${2}"
    local RECON_OUTDIR="${3}"
    local RECON_ONLY="${4}"
    local RECON_SPEC="${5}"
    local QSIPREP_DIR="${6}"
    local PARTICIPANT_LABEL="${7}"
    local FREESURFER_DIR="${8}"
    local NTHREADS="${9}"
    local MEMMB="${10}"
    local OUTPUT_RESOLUTION="${11}"

    qsiprep \
        --participant_label "${PARTICIPANT_LABEL}" \
        --work-dir "${WORKDIR}" \
        "${BIDSDIR}"
    # remaining arguments here

    ## How to define $subj and $ses??

    local recon_dir="${RECON_OUTPUT}"/qsirecon/sub-${subj}/ses-${ses}/dwi

    local data=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_dwi.nii.gz
    local mask=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_mask.nii.gz
    local bvecs=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_dwi.bvec
    local bvals=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_dwi.bval

    ## "DTIFIT_OUTPUT_OLS"
    ## e.g., /corral-secure/projects/A2CPS/products/mris/${site}/dtifit_ols/sub-${subj}/ses-${ses}/sub-${subj}_ses-${ses}

    dtifit -k ${data} -o "${DTIFIT_OUTPUT_OLS}" -m ${mask} -r ${bvecs} -b ${bvals} --ols --sse --save_tensor


    ## "DTIFIT_OUTPUT_WLS"
    ## e.g., /corral-secure/projects/A2CPS/products/mris/${site}/dtifit_wls/sub-${subj}/ses-${ses}/sub-${subj}_ses-${ses}
    dtifit -k ${data} -o "${DTIFIT_OUTPUT_WLS}" -m ${mask} -r ${bvecs} -b ${bvals} --wls --sse --save_tensor


}
export -f main

main "$@"


