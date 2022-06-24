# Allow CONTAINER_IMAGE over-ride via local file
if [ -z "${CONTAINER_IMAGE}" ]
then
    if [ -f "./_lib/CONTAINER_IMAGE" ]; then
        CONTAINER_IMAGE=$(cat ./_lib/CONTAINER_IMAGE)
    fi
    if [ -z "${CONTAINER_IMAGE}" ]; then
        echo "CONTAINER_IMAGE was not set via the app or CONTAINER_IMAGE file"
        CONTAINER_IMAGE="qsiprep-0.13.0RC2.sif"
    fi
fi
# Write an excution command below that will run a script or binary inside the
# requested container, assuming that the current working directory is
# mounted in the container as its WORKDIR. In place of 'docker run'
# use 'container_exec' which will handle setup of the container on
# a variety of host environments.
#
# Here is a template:
#
# container_exec ${CONTAINER_IMAGE} COMMAND OPTS INPUTS
#
# Here is an example of counting words in local file 'poems.txt',
# outputting to a file 'wc_out.txt'
#
# container_exec ${CONTAINER_IMAGE} wc poems.txt > wc_out.txt
#

# set -x

# set +x

# In QSIPrep you need to pass the bids filter file
# for specifying which session to run. The function
# below adds the session to the bids.json file which is
# responsible for providing the information about the
# session.
# Ref https://github.com/PennLINC/qsiprep/issues/282

echo adding the session to the bids filter file
singularity exec -e \
-B ${BIND_DIR}:${BIND_DIR} \
 docker://${CONTAINER_IMAGE} \
 python3 edit_session.py ${BIDS_FILTER} ${SESSION_FOR_LONGITUDINAL}

echo singularity run -e --nv \
 -B ${BIND_DIR}:${BIND_DIR} \
  docker://${CONTAINER_IMAGE} \
  ${BIDS_DIRECTORY} $(realpath ${OUTPUT_DIR}) \
  participant \
  --output-resolution ${OUTPUT_RESOLUTION} \
  --bids-filter-file ${BIDS_FILTER} \
  --denoise-method patch2self \
  --unringing-method mrdegibbs \
  --hmc_model eddy ${EDDY_PARAMS} \
  ${FSL_license} -w $(realpath ${OUTPUT_DIR}) \
  --participant_label ${PARTICIPANT_LABEL} -vvv

singularity run -e --nv \
-B ${BIND_DIR}:${BIND_DIR} \
 docker://${CONTAINER_IMAGE} \
 ${BIDS_DIRECTORY} $(realpath ${OUTPUT_DIR}) \
 participant \
 --output-resolution ${OUTPUT_RESOLUTION} \
 --bids-filter-file ${BIDS_FILTER} \
 --denoise-method patch2self \
 --unringing-method mrdegibbs \
 --hmc_model eddy ${EDDY_PARAMS} \
 ${FSL_license} -w $(realpath ${OUTPUT_DIR}) \
 --participant_label ${PARTICIPANT_LABEL} -vvv

echo computing DTI measures...
echo singularity exec -e \
 -B ${BIND_DIR}:${BIND_DIR} \
  docker://${CONTAINER_IMAGE} \
  python3 compute_dwi_measures.py ${OUTPUT_DIR} ${PARTICIPANT_LABEL} ${SESSION_FOR_LONGITUDINAL}

singularity exec -e \
 -B ${BIND_DIR}:${BIND_DIR} \
  docker://${CONTAINER_IMAGE} \
  python3 compute_dwi_measures.py ${OUTPUT_DIR} ${PARTICIPANT_LABEL} ${SESSION_FOR_LONGITUDINAL}

echo finished!
