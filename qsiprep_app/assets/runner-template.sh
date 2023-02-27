#!/bin/bash

set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

read -ra ins <<< "${BIDS}"
read -ra outs <<< "${OUTDIR}"

if [[ ! "${#ins[@]}" == "${#outs[@]}" ]]; then
    echo "lengh of BIDS must equal length of OUTDIR"
    exit 1
fi

# run once to confirm that the image has been cached (otherwise, may be downloaded by each job)
singularity run --cleanenv docker://"${CONTAINER_IMAGE}" --help

# write launcher file
# shellcheck disable=SC2086
python3 make_launcher.py --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" \
    --bidsdir "${ins[@]}" \
    --outdir "${outs[@]}" \
    ${MEMMB} \
    ${NTHREADS} 

# run all jobs
"${LAUNCHER_DIR}"/paramrun

# need the main tapis out/err logs copied into
# each output directory
for o in "${outs[@]}"; do
    if [[ -d ${o} ]]; then
        cp -t "${o}" ./*{out,err}
    fi
done
rm ./*{out,err} "${LAUNCHER_JOB_FILE}"

# have seen a few cases where the .nii.gz files are corrupted. 
# unclear why or when that happens
# so test all gzip files and exit with error, which prevents archiving
exit_code=0
for o in "${outs[@]}"; do    
    if ! find "${o}"/qsiprep -name "*nii.gz" -print0 | xargs -P50 -0 gunzip -t; then
        exit_code=1
    fi
done

exit $exit_code
