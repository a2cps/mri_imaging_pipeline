#!/usr/bin/env bash

main (){

    local BIDSDIR="${1}"
    local WORKDIR="${2}"
    local QSIPREPDIR="${3}"
    local OUTDIR="${4}"
    local PARTICIPANT_LABEL="${5}"
    local NTHREADS="${6}"
    local MEMMB="${7}"
    local LICENSE="${8}"

    ## RUN QSIRECON

    ## Note, submit example
    
    
    qsiprep \
        --participant_label "${PARTICIPANT_LABEL}" \
        --work-dir "${WORKDIR}" \
        --recon-only \
        --recon_spec reorient_fslstd \
        --recon_input "${QSIPREPDIR}" \
        --nthreads "${NTHREADS}" \
        --mem_mb "${MEMMB}" \
        --fs-license-file "${LICENSE}" \
        "${BIDSDIR}" "${OUTDIR}" participant

    echo "qsiprep recon finished!"

    ## DEFINE ARGS FOR DTIFIT
    local qsirecon_dir="${OUTDIR}"/qsirecon/"${PARTICIPANT_LABEL}"/ses-V1/dwi
    
    local data="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi.nii.gz
    local mask="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_mask.nii.gz
    local bvecs="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi.bvec
    local bvals="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi.bval

    local DTIFIT_OUTDIR_OLS="${OUTDIR}"/dtifit/dtifit_ols/"${PARTICIPANT_LABEL}"
    local DTIFIT_OUTDIR_WLS="${OUTDIR}"/dtifit/dtifit_wls/"${PARTICIPANT_LABEL}"

    ## Need to make output dirs first
    mkdir -p "${DTIFIT_OUTDIR_OLS}"
    mkdir -p "${DTIFIT_OUTDIR_WLS}"

    # ## RUN DTIFIT (OLS)
    dtifit -k ${data} -o "${DTIFIT_OUTDIR_OLS}"/"${PARTICIPANT_LABEL}"_ses-V1 -m ${mask} -r ${bvecs} -b ${bvals} --sse --save_tensor

    # ## RUN DTIFIT (WLS)
    dtifit -k ${data} -o "${DTIFIT_OUTDIR_WLS}"/"${PARTICIPANT_LABEL}"_ses-V1 -m ${mask} -r ${bvecs} -b ${bvals} --wls --sse --save_tensor

}

export -f main

main "$@"