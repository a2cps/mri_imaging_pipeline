#!/usr/bin/env bash

# run once to confirm that the image has been cached (otherwise, may be downloaded by each job)
singularity run --cleanenv "${container_image}" --help

# run the qsiprep_recon step
singularity run \
-e \
--bind "${BIND_DIR}":"${BIND_DIR}" \
"${CONTAINER}" \
"${BIDSDIR}" \
"${RECON_OUTDIR}" \
"${WORKDIR}" \
"${RECON_ONLY}" \
"${RECON_SPEC}" \
"${QSIPREP_DIR}" \
"${PARTICIPANT_LABEL}" \
"${FREESURFER_DIR}" \
"${NTHREADS}" \
"${MEMMB}" \
"${OUTPUT_RESOLUTION}"

## "${RECON_OUTPUT}"
## e.g., /corral-secure/projects/A2CPS/products/mris/${site}/qsirecon-fsl/${subj}


## How to define $subj and $ses??

recon_dir="${RECON_OUTPUT}"/qsirecon/sub-${subj}/ses-${ses}/dwi

data=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_dwi.nii.gz
mask=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_mask.nii.gz
bvecs=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_dwi.bvec
bvals=$recon_dir/sub-${subj}_ses-${ses}_space-T1w_desc-preproc_fslstd_dwi.bval


## "DTIFIT_OUTPUT_OLS"
## e.g., /corral-secure/projects/A2CPS/products/mris/${site}/dtifit_ols/sub-${subj}/ses-${ses}/sub-${subj}_ses-${ses}

dtifit -k ${data} -o "${DTIFIT_OUTPUT_OLS}" -m ${mask} -r ${bvecs} -b ${bvals} --ols --sse --save_tensor


## "DTIFIT_OUTPUT_WLS"
## e.g., /corral-secure/projects/A2CPS/products/mris/${site}/dtifit_wls/sub-${subj}/ses-${ses}/sub-${subj}_ses-${ses}
dtifit -k ${data} -o "${DTIFIT_OUTPUT_WLS}" -m ${mask} -r ${bvecs} -b ${bvals} --wls --sse --save_tensor

