#!/bin/bash

set -x

date

singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://"${CONTAINER_IMAGE}" \
    python make_dataset.py "${OUTDIR}"  --inroot "${INROOT}"
