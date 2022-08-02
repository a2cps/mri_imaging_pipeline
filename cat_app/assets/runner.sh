#!/usr/bin/env bash
set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

read -ra ins <<< "${BIDS}"
read -ra outs <<< "${OUTDIR}"

if [[ ! "${#ins[@]}" == "${#outs[@]}" ]]; then
        echo "lengh of NIFTI must equal length of OUTDIR"
        exit 1
fi

# run once to confirm that the image has been cached (otherwise, may be downloaded by each job)
singularity run --cleanenv "${CONTAINER_IMAGE}" --help

# write launcher file
python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" "${BATCH}" --bidsdir "${ins[@]}" --a1 "${A1}" --outdir "${outs[@]}"

# run all jobs
"${LAUNCHER_DIR}"/paramrun
