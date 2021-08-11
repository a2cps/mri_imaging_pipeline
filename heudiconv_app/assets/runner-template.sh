#!/bin/bash

# Import Agave runtime extensions
. _lib/extend-runtime.sh

# Allow CONTAINER_IMAGE over-ride via local file
if [ -z "${CONTAINER_IMAGE}" ]; then
    if [ -f "./_lib/CONTAINER_IMAGE" ]; then
        CONTAINER_IMAGE=$(cat ./_lib/CONTAINER_IMAGE)
    fi
    if [ -z "${CONTAINER_IMAGE}" ]; then
        echo "CONTAINER_IMAGE was not set via the app or CONTAINER_IMAGE file"
        CONTAINER_IMAGE="jurrutia/ubuntu17"
    fi
fi


if [[ "${SITE}" == "UC" ]]; then
    echo singularity exec \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://${CONTAINER_IMAGE} python3 run_delete_trigger_tag_philips.py ${FILES}

    singularity exec \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://${CONTAINER_IMAGE} python3 run_delete_trigger_tag_philips.py ${FILES}
    export DICOM='--files dicom'
else 
    export DICOM="${FILES}"
fi

echo singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://${CONTAINER_IMAGE} \
    heudiconv \
    ${DICOM_DIR_TEMPLATE} ${DICOM} \
    ${LIST_OF_SUBJECTS} \
    ${CONVERTER} \
    --outdir ${OUTDIR} \
    ${LOCATOR} ${ANON_CMD} \
    ${HEURISTIC} \
    ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
    ${DATALAD} ${DCMCONFIG}

singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://${CONTAINER_IMAGE} \
    heudiconv \
    ${DICOM_DIR_TEMPLATE} ${DICOM} \
    ${LIST_OF_SUBJECTS} \
    ${CONVERTER} \
    --outdir ${OUTDIR} \
    ${LOCATOR} ${ANON_CMD} \
    ${HEURISTIC} \
    ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
    ${DATALAD} ${DCMCONFIG}

# add bval, bvec, betc to .bidsignore
cat bids_ignore >> "${OUTDIR}"/.bidsignore

# Need to inject IntendedFor field into some jsons, and in the case of GE images
# generate the AP/PA fieldmaps. Heudiconv outputs them as readonly, so temporarily
# give write access to user, read to group
readonly JSONS=("${OUTDIR}"/sub-*/ses-*/*/*.json) \
  && chmod +640 "${JSONS[@]}"

case "${SITE}" in
  UI | UM)
    echo singularity exec \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://${CONTAINER_IMAGE} python3 create_fieldmaps_GE.py "${OUTDIR}"

    singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://${CONTAINER_IMAGE} python3 create_fieldmaps_GE.py "${OUTDIR}"
    ;;
esac

echo singularity exec \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://${CONTAINER_IMAGE} python3 edit_json.py "${OUTDIR}"

singularity exec \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://${CONTAINER_IMAGE} python3 edit_json.py "${OUTDIR}"

# Clean up edited dicoms
if [[ "${SITE}" == "UC" ]]; then
    rm -rf dicom
fi

# quick python to remove null values from participants.tsv
echo singularity exec \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://${CONTAINER_IMAGE} python3 participants.py "${OUTDIR}"

singularity exec \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://${CONTAINER_IMAGE} python3 participants.py "${OUTDIR}"


  