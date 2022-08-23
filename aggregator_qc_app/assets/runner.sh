#!/bin/bash
set -x

date

[[ ! -d "${OUTDIR}" ]] && mkdir -p "${OUTDIR}"

# create symlinks to all new outputs in the bids and mriqc folders
for site in ${SITES}; do

  # copy any html reports into out directory
  find "${INROOT}/products/mris/${site}/mriqc" -name "*work*" -prune -o -type f -name "sub-[12]*html" -exec cp -svu -t "${OUTDIR}" -- '{}' \+

  # also copy json files, and the folders they're stored in
  find "${INROOT}/products/mris/${site}/mriqc" -name "*work*" -prune -o -type d -name "sub-[12]*" -exec cp -vau -t "${OUTDIR}" -- '{}' \+

done

set -e
# since bids and mriqc files are only symlinks, the targets of the 
# symlinks must also be bound (hence -B for INROOT)
singularity exec \
  --cleanenv \
  -B "${INROOT}":"${INROOT}" \
  -B "${BIDS}":/bids:ro \
  -B "${OUTDIR}":/mriqc \
  docker://"${CONTAINER_IMAGE}" \
  mriqc /bids /mriqc group

singularity exec \
  --cleanenv \
  -B "${INROOT}":"${INROOT}" \
  -B "${OUTDIR}":"${OUTDIR}" \
  docker://"${CONTAINER_IMAGE}" \
  python check_qc.py "${OUTDIR}"/group_T1w.tsv "${OUTDIR}"/group_bold.tsv \
  --outdir "${LOGDIR}" \
  --token "$(<token)" \
  --json_dir /corral-secure/projects/A2CPS/shared/psadil/qclog/mriqc-reviews \
  --imaging_log /corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv

date
