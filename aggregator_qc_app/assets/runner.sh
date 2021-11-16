#!/bin/bash
set -ex

date

readonly OUT_MRIQC="${OUTROOT}/mriqc-group/a2cps"
readonly OUT_BIDS="${OUTROOT}/bids/a2cps"

[[ ! -d "${OUT_MRIQC}" ]] && mkdir -p "${OUT_MRIQC}"

# create symlinks to all new outputs in the bids and mriqc folders
for site in ${SITES}; do

  # copy any html reports into out directory
  find "${INROOT}/${site}/mriqc" -name "work" -prune -o -type f -name "*html" -exec cp -svu -t "${OUT_MRIQC}" -- '{}' \+

  # also copy json files, and the folders they're stored in
  find "${INROOT}/${site}/mriqc" -type d -name "sub-*" -exec cp -vau -t "${OUT_MRIQC}" -- '{}' \+

done


# since bids and mriqc files are only symlinks, the targets of the 
# symlinks must also be bound (hence -B for INROOT)
singularity run \
  --cleanenv \
  -B "${INROOT}":"${INROOT}":ro \
  -B "${OUT_BIDS}":/bids:ro \
  -B "${OUT_MRIQC}":/mriqc \
  docker://"${CONTAINER_IMAGE}" \
  /bids /mriqc group

singularity exec \
  --cleanenv \
  -B "${OUT_MRIQC}":"${OUT_MRIQC}":ro \
  docker://psadil/mriqc:latest \
  python check_qc.py "${OUT_MRIQC}"/group_T1w.tsv "${OUT_MRIQC}"/group_bold.tsv "${OUT_MRIQC}"/group_dwi.csv \
  --token "$(<.token)" --pem "confluence-a2cps-org-chain.pem"

singularity exec \
  --cleanenv \
  -B "${OUT_MRIQC}":"${OUT_MRIQC}":ro \
  docker://psadil/mriqc:latest \
  jupyter nbconvert qc_report.ipynb --to html --no-input --no-prompt --output qc_report.html --execute

date
