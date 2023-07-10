#!/bin/bash
set -x

date

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
