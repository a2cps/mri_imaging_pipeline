#!/bin/bash

# Import Agave runtime extensions
# shellcheck disable=SC1091
. _lib/extend-runtime.sh

set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

read -ra ins <<< "${BIDS_DIR}"
read -ra outs <<< "${OUTPUT_DIR}"

if [[ ! "${#ins[@]}" == "${#outs[@]}" ]]; then
    echo "lengh of BIDS_DIR must equal length of OUTPUT_DIR"
    exit 1
fi

# run once to confirm that the image has been cached (otherwise, may be downloaded by each job)
singularity run --cleanenv docker://"${CONTAINER_IMAGE}" --help &> /dev/null

# write launcher file
# shellcheck disable=SC2086
python3 make_launcher.py \
  --launchfile "${LAUNCHER_JOB_FILE}" \
  --binddir "${BINDDIR}" \
  --container "${CONTAINER_IMAGE}" \
  ${N_WORKERS} \
  --bids-dir "${ins[@]}" \
  --output-dir "${outs[@]}" 
   

# run all jobs
"${LAUNCHER_DIR}"/paramrun

# need the main tapis out/err logs copied into
# each output directory
for o in "${outs[@]}"; do
    if [[ -d ${o} ]]; then
        cp -t "${o}" ./*{out,err}
    fi
done
# rm ./*{out,err} "${LAUNCHER_JOB_FILE}"

