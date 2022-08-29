#!/usr/bin/env bash

set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

# shellcheck disable=SC2153
read -ra bids <<< "${BIDS}"
read -ra outs <<< "${OUTDIR}"

if [[ ! "${#bids[@]}" == "${#outs[@]}" ]]; then
        echo "lengh of BIDS must equal length of OUTDIR"
        exit 1
fi

# run once to confirm that the image has been cached (otherwise, may be downloaded by each job)
singularity run --cleanenv "${CONTAINER_IMAGE}" --help

# write launcher file
# shellcheck disable=SC2086
python3 make_launcher.py  \
    --launchfile "${LAUNCHER_JOB_FILE}" \
    ${BIND_DIR} \
    --container "${CONTAINER_IMAGE}" \
    --bids "${bids[@]}"  \
    --out "${outs[@]}" 

# run all jobs
"${LAUNCHER_DIR}"/paramrun