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

# Unzip dicoms locally 
LOCAL_DICOM=$(basename ${FILES})
# remove zip suffix
LOCAL_DICOM=${LOCAL_DICOM%.*}
unzip ${FILES} -d ${LOCAL_DICOM}


echo singularity exec \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://${CONTAINER_IMAGE} \
  heudiconv \
  ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
  ${LIST_OF_SUBJECTS} \
  ${CONVERTER} \
  --outdir ${OUTDIR} \
  ${LOCATOR} ${ANON_CMD} \
  ${HEURISTIC} \
  ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
  ${DATALAD} ${DCMCONFIG}

if [[ ${SITE} == UC ]]; then
  # UC needs custom version of dcm2niix
  # see https://confluence.a2cps.org/display/WG/2021-12-21+DIRC+Meeting+notes
  # if/else can be removed when dcm2niix updated for Spring 2022 release
  singularity exec \
    --cleanenv \
    --env PREPEND_PATH=/opt/dcm-UC/bin \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://${CONTAINER_IMAGE} \
    heudiconv \
    ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
    ${LIST_OF_SUBJECTS} \
    ${CONVERTER} \
    --outdir ${OUTDIR} \
    ${LOCATOR} ${ANON_CMD} \
    ${HEURISTIC} \
    ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
    ${DATALAD} ${DCMCONFIG}
else
  singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://${CONTAINER_IMAGE} \
    heudiconv \
    ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
    ${LIST_OF_SUBJECTS} \
    ${CONVERTER} \
    --outdir ${OUTDIR} \
    ${LOCATOR} ${ANON_CMD} \
    ${HEURISTIC} \
    ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
    ${DATALAD} ${DCMCONFIG}
fi 

# Remove local dicom directory
rm -rf ${LOCAL_DICOM}

# add bval, bvec, betc to .bidsignore
cat bids_ignore >> "${OUTDIR}"/.bidsignore

# Need to inject IntendedFor field into some jsons, and in the case of GE images
# generate the AP/PA fieldmaps. Heudiconv outputs them as readonly, so temporarily
# give write access to user, read to group
readonly FILE_EDITS=("${OUTDIR}"/sub-*/ses-*/*/*) \
  && chmod +640 "${FILE_EDITS[@]}"

# Delete duplicate scans if flag is set
echo "delete duplicates flag set to: ${DELETE_DUPLICATES}"
if [ ${DELETE_DUPLICATES} == 1 ]; then
  # delete duplicte scans
  echo "removing duplicate scans"
  rm -rf ${OUTDIR}/sub-*/ses-*/*/*_dup*
  # remove duplicate scans from scans.tsv
  sed -i '/_dup/d' ${OUTDIR}/sub-*/ses-*/*scans.tsv
else
  echo "adding duplicate scans to bids ignore"
  # otherwise add to bids ignore
  echo "${OUTDIR}/sub-*/ses-*/*/*_dup*" >> .bidsignore
  # remove duplicate scans from scans.tsv
  sed -i '/_dup/d' ${OUTDIR}/sub-*/ses-*/*scans.tsv
fi

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

    # Adding the correct GE bvals and bvec file. Added on Sept 28,2021.
    echo "Replacing correct bval and bvec files..."
    cat correct_bval_GE>"${OUTDIR}"/sub-*/ses-*/dwi/*bval
    cat correct_bvec_GE>"${OUTDIR}"/sub-*/ses-*/dwi/*bvec
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

