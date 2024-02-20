#!/usr/bin/env bash
set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

read -ra bids_ins <<< "${BIDSDIR}"
read -ra qsiprep_ins <<< "${QSIPREP_DIR}"
read -ra freesurfer_ins <<< "${FREESURFER_DIR}"
read -ra recon_outs <<< "${RECON_OUTDIR}"
read -ra work_outs <<< "${WORKDIR}"

## Do I need to have if statement across all the dirs?
if [[ ! "${#bids_ins[@]}" == "${#recon_outouts[@]}" ]]; then
        echo "lengh of NIFTI must equal length of OUTDIR"
        exit 1
fi

# run once to confirm that the image has been cached (otherwise, may be downloaded by each job)
singularity run --cleanenv "${CONTAINER_IMAGE}" --help


### EXAMPLE FROM CAT APP
# write launcher file
# shellcheck disable=SC2086
python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" --bidsdir "${ins[@]}" --outdir "${outs[@]}" ${NPROC}

### NEW ATTEMPT
# write launcher file
# shellcheck disable=SC2086
python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" "${bids_ins[@]}" "${recon_outs[@]}" "${work_outs[@]}" "${RECON_ONLY}" "${RECON_SPEC}" "${qsiprep_ins[@]}" "${PARTICIPANT_LABEL}" "${freesurfer_ins[@]}" ${NTHREADS} ${MEMMB} ${OUTPUT_RESOLUTION}

# run all jobs
"${LAUNCHER_DIR}"/paramrun

# copy main .err/.out to each output dir and delete
# the container will only deposit images into the output directory if the run was successful
# if any of the output folders do not have output (i.e., they failed), say that the entire job failed
exit_code=0
for o in "${outs[@]}"; do
    if [[ $(compgen -G "${o}"/*gz) ]]; then
        cp -t "${o}" ./*{out,err}
    else
        echo "output files not found!" >&2
        exit_code=1
    fi
done
rm ./*{out,err} launchfile

exit $exit_code