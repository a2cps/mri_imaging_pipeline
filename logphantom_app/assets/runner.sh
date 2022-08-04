#!/bin/bash

set -x

date

# shellcheck disable=SC2086
singularity run \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    ${CONTAINER_IMAGE} \
    init ${PRODUCTS} ${URL}

# shellcheck disable=SC2086
singularity run \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    ${CONTAINER_IMAGE} \
    write-and-post ${URL} ${POST} 

