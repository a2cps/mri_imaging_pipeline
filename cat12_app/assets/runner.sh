#!/usr/bin/env bash
set -x

singularity exec \
        -B "${BIDS_DIRECTORY}":"${BIDS_DIRECTORY}" \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        --cleanenv \
        docker://${CONTAINER_IMAGE} \
        mriqc \
        ${BIDS_DIRECTORY} \
        ${OUTPUT_DIR} \
        participant --participant-label ${PARTICIPANT_LABEL} \
        ${WORK_DIR} \
        --no-sub \
        --n_procs 50 \
        --mem_gb 180 \
        ${ICA} \
        ${STOP_IDX} \
        ${START_IDX} \
        ${FFT_SPIKES} \
        ${WRITE_GRAPH} \
        ${CORRECT_SLICE_TIMING} \
        ${FD_THRESHOLD} \
        ${TASK_ID} \
        ${MODALITIES} \
        --verbose-reports
