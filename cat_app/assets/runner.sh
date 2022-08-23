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
echo python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" "${BATCH}" --bidsdir "${ins[@]}" --a1 "${A1}" --outdir "${outs[@]}"

python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" "${BATCH}" --bidsdir "${ins[@]}" --a1 "${A1}" --outdir "${outs[@]}"


# run all jobs
"${LAUNCHER_DIR}"/paramrun

# copy main .err/.out and launchfile to each output dir and delete
for o in "${outs[@]}"; do
    cp -t "${o}" ./*{out,err}
    cp -t "${o}" launchfile
done
rm ./*{out,err} launchfile
