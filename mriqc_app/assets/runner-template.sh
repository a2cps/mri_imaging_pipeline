#!/usr/bin/env bash


# BUG Input Directory ${BIDS_DIRECTORY} not defined
# using some bash tricks to get if from the participant label
# DIR=*/*-${PARTICIPANT_LABEL}
# DIR=$(echo ${DIR} | cut -d "/" -f1)
# echo Input is ${DIR}

mkdir -p  "${OUTPUT_DIR}"

# Usage: container_exec IMAGE COMMAND OPTIONS
#   Example: docker run centos:7 uname -a
#            container_exec centos:7 uname -a

# Echo command to std out
echo    mriqc \
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

