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
# shellcheck disable=SC2086
python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" --bidsdir "${ins[@]}" --outdir "${outs[@]}" ${NPROC}

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