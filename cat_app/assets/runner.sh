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

# write launcher file
python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" "${BATCH}" "${ins[@]}" --a1 "${A1}" --outdir "${outs[@]}"

# run all jobs
"${LAUNCHER_DIR}"/paramrun
