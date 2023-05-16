#!/bin/bash

# Import Agave runtime extensions
# shellcheck disable=SC1091
. _lib/extend-runtime.sh

set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

read -ra ins <<< "${BIDS_DIRECTORY}"
read -ra outs <<< "${OUTPUT_DIR}"
read -ra fsdirs <<< "${FS_SUBJECTS_DIR}"

if [[ ! "${#ins[@]}" == "${#outs[@]}" ]]; then
    echo "lengh of BIDS_DIRECTORY must equal length of OUTPUT_DIR"
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
  --bidsdir "${ins[@]}" \
  --outdir "${outs[@]}" \
  --fs-subjects-dir "${fsdirs[@]}" \
  ${MEMMB} \
  ${NTHREADS} \
  ${IGNORE_FIELD_MAPS} ${IGNORE_SLICE_TIMING} ${HEAD_MOTION} ${DUMMY_SCANS} \
  ${ICA_AROMA_USE} ${ICA_AROMA_DIMENSIONALITY} ${FD_SPIKE} ${CIFTI_OUTPUT} ${ANAT_ONLY} \
  ${BIDS_FILTER_FILE} ${FS_NO_RECONALL} ${SKIP_BIDS_VALIDATION} 

# run all jobs
"${LAUNCHER_DIR}"/paramrun

# need the main tapis out/err logs copied into
# each output directory
for o in "${outs[@]}"; do
    if [[ -d ${o} ]]; then
        cp -t "${o}" ./*{out,err}
        rm -r "${o}"/work &
    fi
done
wait
rm ./*{out,err}
echo "${LAUNCHER_JOB_FILE}" >> .agave.archive

# have seen a few cases where the .nii.gz files are corrupted. 
# unclear why or when that happens
# so test all gzip files and exit with error, which prevents archiving
exit_code=0
for o in "${outs[@]}"; do    
    if ! find "${o}" -name work -prune -o -name "*nii.gz" -print0 | xargs -0 -P 50 gunzip -t; then
        exit_code=1
    fi
done

exit $exit_code
