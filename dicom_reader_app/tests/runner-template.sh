# Import Agave runtime extensions
. _lib/extend-runtime.sh

# BUG Input Directory ${BIDS_DIRECTORY} not defined
# using some bash tricks to get if from the participant label
DIR=*/${PARTICIPANT_LABEL}
DIR=$(echo ${DIR} | cut -d "/" -f1)
echo Input is ${DIR}

# Usage: container_exec IMAGE COMMAND OPTIONS
#   Example: docker run centos:7 uname -a
#            container_exec centos:7 uname -a

mkdir -p  ${OUTPUT_DIR}/work
PYTHONPATH=""
# Echo command to std out
echo container_exec ${CONTAINER_IMAGE} \
               fmriprep \
               ${DIR} \
               ${OUTPUT_DIR} \
               participant --participant_label ${PARTICIPANT_LABEL} \
               -w  ${OUTPUT_DIR}/work \
               --write-graph \
               --n-cpus 16 \
               --notrack \
               --mem_mb 48000 \
               ${FIELDMAPS} ${SLICE_TIMING} ${HEAD_MOTION} ${DUMMY_SCANS} \
               ${ICA_AROMA_USE} ${ICA_AROMA_DIMENSIONALITY} ${FD_SPIKE} ${CIFTI_OUTPUT} \
               --fs-license-file /opt/freesurfer_license/license.txt

container_exec ${CONTAINER_IMAGE} \
               fmriprep \
               ${DIR} \
               ${OUTPUT_DIR} \
               participant --participant_label ${PARTICIPANT_LABEL} \
               -w  ${OUTPUT_DIR}/work \
               --write-graph \
               --n-cpus 16 \
               --notrack \
               --mem_mb 48000 \
               ${FIELDMAPS} ${SLICE_TIMING} ${HEAD_MOTION} ${DUMMY_SCANS} \
               ${ICA_AROMA_USE} ${ICA_AROMA_DIMENSIONALITY} ${FD_SPIKE} ${CIFTI_OUTPUT} \
               --fs-license-file /opt/freesurfer_license/license.txt

rm -rf ${DIR}
