# Import Agave runtime extensions
. _lib/extend-runtime.sh

# BUG Input Directory ${BIDS_DIRECTORY} not defined
# using some bash tricks to get if from the participant label
#DIR=*/${PARTICIPANT_LABEL}
#DIR=$(echo ${DIR} | cut -d "/" -f1)
echo Input is ${BIDS_DIRECTORY}

# Usage: container_exec IMAGE COMMAND OPTIONS
#   Example: docker run centos:7 uname -a
#            container_exec centos:7 uname -a

mkdir -p  ${OUTPUT_DIR}/work
PYTHONPATH=""
# Echo command to std out
echo singularity exec \
        -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
        -e \
        docker://${CONTAINER_IMAGE} \
        fmriprep \
        ${BIDS_DIRECTORY} \
        ${OUTPUT_DIR} \
        participant --participant_label ${PARTICIPANT_LABEL} \
        -w  ${OUTPUT_DIR}/work \
        --write-graph \
        --n-cpus 16 \
        --notrack \
        --mem_mb 48000 \
        ${IGNORE_FIELD_MAPS} ${IGNORE_SLICE_TIMING} ${HEAD_MOTION} ${DUMMY_SCANS} \
        ${ICA_AROMA_USE} ${ICA_AROMA_DIMENSIONALITY} ${FD_SPIKE} ${CIFTI_OUTPUT} ${ANAT_ONLY} \
        ${BIDS_FILTER_FILE} ${FS_NO_RECONALL} ${FS_SUBJECTS_DIR} ${SKIP_BIDS_VALIDATION} \
        --fs-license-file /opt/freesurfer_license/license.txt

singularity exec \
        -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
        -e \
        docker://${CONTAINER_IMAGE} \
        fmriprep \
        ${BIDS_DIRECTORY} \
        ${OUTPUT_DIR} \
        participant --participant_label ${PARTICIPANT_LABEL} \
        -w  ${OUTPUT_DIR}/work \
        --write-graph \
        --n-cpus 16 \
        --notrack \
        --mem_mb 48000 \
        ${IGNORE_FIELD_MAPS} ${IGNORE_SLICE_TIMING} ${HEAD_MOTION} ${DUMMY_SCANS} \
        ${ICA_AROMA_USE} ${ICA_AROMA_DIMENSIONALITY} ${FD_SPIKE} ${CIFTI_OUTPUT} ${ANAT_ONLY} \
        ${BIDS_FILTER_FILE} ${FS_NO_RECONALL} ${FS_SUBJECTS_DIR} ${SKIP_BIDS_VALIDATION} \
        --fs-license-file /opt/freesurfer_license/license.txt

