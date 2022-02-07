#!/usr/bin/env bash
set -ux
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

read -ra gzs <<< "${NIFTI}"
read -ra outs <<< "${OUTDIR}"

if [[ ! "${#gzs[@]}" == "${#outs[@]}" ]]; then
        echo "lengh of NIFTI must equal length of OUTDIR"
        exit 1
fi

# cat12 has poor control over where results are placed; it's always relative to the input image
# so, we manually create the output directory, then move the input image into it, and the
# resulting copied file will be fed to cat12
niftis=()
for f in "${!gzs[@]}"; do
  if [[  ! -d "${outs[f]}" ]]; then 
    mkdir -p "${outs[f]}" \
      && cp -sL "${gzs[f]}" "${outs[f]}"  \
      && niftis+=("${outs[f]}"/*nii.gz)
  else
    echo "not writing to ${outs[f]} since folder already exists"
  fi
done

# write launcher file
python3 make_launcher.py  --launchfile "${LAUNCHER_JOB_FILE}" \
    "${BIND_DIR}" "${CONTAINER_IMAGE}" "${BATCH}" "${niftis[@]}" --a1 "${A1}"

# run all jobs
"${LAUNCHER_DIR}"/paramrun
