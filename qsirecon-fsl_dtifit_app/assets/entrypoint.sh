#!/usr/bin/env bash

main (){
    local BIDSDIR="${1}"
    local WORKDIR="${2}"
    local QSIPREPDIR="${3}"
    local FREESURFERDIR="${4}"
    local OUTDIR="${5}"
    local PARTICIPANT_LABEL="${6}"
    local NTHREADS="${7}"
    local MEMMB="${8}"
    local LICENSE="${9}"

    ## RUN QSIRECON
    qsiprep \
        --participant_label "${PARTICIPANT_LABEL}" \
        --work-dir "${WORKDIR}" \
        --recon-only \
        --recon_spec reorient_fslstd \
        --recon_input "${QSIPREPDIR}" \
        --freesurfer-input "${FREESURFERDIR}" \
        --output-resolution 1.7 \
        --nthreads "${NTHREADS}" \
        --mem_mb "${MEMMB}" \
        --fs-license-file "${LICENSE}" \
        "${BIDSDIR}" "${OUTDIR}" participant
    
    echo "qsiprep recon finished!"

    # ## DEFINE ARGS FOR DTIFIT
    # local qsirecon_dir="${OUTDIR}"/qsirecon/"${PARTICIPANT_LABEL}"/dwi
    #     ## check, does qsirecon outpout for traveling data include "_ses-" by default?
    # local data="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_space-T1w_desc-preproc_fslstd_dwi.nii.gz
    # local mask="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_space-T1w_desc-preproc_fslstd_mask.nii.gz
    # local bvecs="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_space-T1w_desc-preproc_fslstd_dwi.bvec
    # local bvals="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_space-T1w_desc-preproc_fslstd_dwi.bval

    # local DTIFIT_OUTDIR_OLS="${OUTDIR}"/dtifit/ols
    # local DTIFIT_OUTDIR_WLS="${OUTDIR}"/dtifit/wls

    # ## RUN DTIFIT (OLS)
    # dtifit -k ${data} -o "${DTIFIT_OUTDIR_OLS}" -m ${mask} -r ${bvecs} -b ${bvals} --ols --sse --save_tensor

    # ## RUN DTIFIT (WLS)
    # dtifit -k ${data} -o "${DTIFIT_OUTDIR_WLS}" -m ${mask} -r ${bvecs} -b ${bvals} --wls --sse --save_tensor

}

export -f main

main "$@"