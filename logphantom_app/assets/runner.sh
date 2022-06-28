#!/bin/bash

set -x

date

# shellcheck disable=SC2086
singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    "${CONTAINER_IMAGE}" \
    python log.py --bidsroot "${BIDS}" --products "${PRODUCTS}" ${POST}

