#!/bin/bash

# Import Agave runtime extensions
# shellcheck disable=SC1091
. _lib/extend-runtime.sh

# Unzip dicoms locally 
LOCAL_DICOM=$(basename "${FILES}")
# remove zip suffix
#shellcheck disable=SC2086
LOCAL_DICOM=/tmp/${LOCAL_DICOM%.*}
#shellcheck disable=SC2086
unzip ${FILES} -d ${LOCAL_DICOM}

case "${SITE}" in
  SH | RU | WS)
    echo singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      python exclude_derived-dwi_xa30.py "${LOCAL_DICOM}"

    singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      python exclude_derived-dwi_xa30.py "${LOCAL_DICOM}"

    #shellcheck disable=SC2086
    echo singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM}  --minmeta \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
          
    #shellcheck disable=SC2086
    singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM}  --minmeta \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}

    # heudiconv is unable to find the acquisition datetime, so we fill them manually
    # note that this script does not currently add the exact time, just the acq_date
    echo singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      python add_date_to_xa30.py "${LOCAL_DICOM}" "${OUTDIR}"

    singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      python add_date_to_xa30.py "${LOCAL_DICOM}" "${OUTDIR}"
    ;;

  *)
    #shellcheck disable=SC2086
    echo singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}

    #shellcheck disable=SC2086
    singularity run \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
    ;;
esac


# Remove local dicom directory
#shellcheck disable=SC2086
rm -rf ${LOCAL_DICOM}

# add bval, bvec, betc to .bidsignore
cat bids_ignore >> "${OUTDIR}"/.bidsignore && cat .agave.archive >> "${OUTDIR}"/.bidsignore

# Phantom-specific post-processing
if [[ "${LIST_OF_SUBJECTS}" == *phantom* ]]; then
  PHANTOM="--phantom"
  case "${SITE}" in
    NS) 
      # dcm2niix generates several extra scans, derivatives from NS.
      singularity run --cleanenv \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python clean_nsphantom.py "${OUTDIR}"
      ;;
    UC)
      # For UC, dcm2niix generates extra "ADC" scans, which are derived volumes. They could be 
      # avoided by using the -i y flag, except that flag would also cause dcm2niix to skip the anat 
      # scans from NS
      find "${OUTDIR}" -name "*ADC*" -delete
      ;;
    WS)
      # heuristic can result in run-1 tag, unlike all other sites
      singularity run --cleanenv  \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python clean_wsphantom.py "${OUTDIR}"
      ;;
  esac
  else
  PHANTOM="--no-phantom"
fi

# The UM2 traveling scan had these ADC files
find "${OUTDIR}" -name "*ADC*" -delete

# Need to inject IntendedFor field into some jsons, and in the case of GE images
# generate the AP/PA fieldmaps. Heudiconv outputs them as readonly, so temporarily
# give write access to user, read to group
chmod +640 "${OUTDIR}"/sub-*/ses-*/*/*

# Delete duplicate scans if flag is set
echo "delete duplicates flag set to: ${DELETE_DUPLICATES}"

mapfile -t dups < <(find "${OUTDIR}" -type f -name "*dup*")
if (( ${#dups[@]} > 1 )); then
  # post about found duplicates to slack channel
  msg="duplicate scans found: ${dups[*]}"

  #shellcheck disable=SC2086
  singularity run \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    --cleanenv docker://"${CONTAINER_IMAGE}" python log.py "${msg}" ${POST}
  if [[ ${DELETE_DUPLICATES} == 1 ]]; then
    # delete duplicte scans
    echo "removing duplicate scans" 
    rm -rf "${dups[@]}"
  else
    echo "adding duplicate scans to bids ignore"
    # otherwise add to bids ignore
    echo "${OUTDIR}/sub-*/ses-*/*/*_dup*" >> .bidsignore
  fi
  # remove duplicate scans from scans.tsv
  sed -i '/_dup/d' "${OUTDIR}"/sub-*/ses-*/*scans.tsv
  else
    echo "no duplicate scans found"
fi

if [[ "${PHANTOM}" == "--no-phantom" ]]; then
  case "${SITE}" in
    UI | UM)
      echo singularity run \
        --cleanenv \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python create_fieldmaps_GE.py "${OUTDIR}"

      singularity run \
        --cleanenv \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python create_fieldmaps_GE.py "${OUTDIR}"

      echo singularity run \
        --cleanenv \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python handle_ge_bvalbvecs.py "${OUTDIR}"

      singularity run \
        --cleanenv \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python handle_ge_bvalbvecs.py "${OUTDIR}"
    ;;
  esac
else
  case "${SITE}" in
    UI | UM)
      echo "INFO: phantom scan detected. not creating fieldmaps and not replacing bvals/bvecs"
      # NOTE: not replacing bvals/bvecs for phantom scans because we don't know what they 
      # should be (and it's not clear that these values will be helpful)
    ;;    
  esac
  case "${SITE}" in
    UM)
      echo "overwritting coil_QA with final volume"
      singularity run \
        --cleanenv \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        python index_coilqa.py "${OUTDIR}"/sub-umphantom/ses*/anat/*T1w.nii.gz
    ;;
  esac
fi

echo singularity run \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" \
  python edit_json.py "${OUTDIR}"

singularity run \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" \
  python edit_json.py "${OUTDIR}"


# resting state scans do not require events files (there are no events)
# so delete any that are found
find "${OUTDIR}" -type f -name '*task-rest*events.tsv' -delete

set -x
if [[ ${CHECK_JSONS} == 1 ]]; then
  # the check is a bit messy. Previously, $SITE could reliably distinguish acquisition protocol. Now, sites
  # have both a patient protocol and a phantom protocol, which always differ. So, the checks must
  # be divided by whether we're dealing with a phantom scan or not.
  #shellcheck disable=SC2086
  singularity run \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://"${CONTAINER_IMAGE}" \
    python check_acq.py "${OUTDIR}" "${SITE}" ${PHANTOM} ${POST}
else
  echo "Skipping check of jsons"
fi

echo "cleaning *scans.tsv"
singularity run \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" \
  python edit_scanstsv.py "${OUTDIR}"


echo "ensuring that dir-[dir] entities match PhaseEncodingDirection"
singularity run \
  --cleanenv \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" \
  python conform_dir.py "${OUTDIR}"

# end with check of newly created directory. if the output is not valid, the job will fail
singularity run \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" bids-validator --ignoreWarnings "${OUTDIR}"
