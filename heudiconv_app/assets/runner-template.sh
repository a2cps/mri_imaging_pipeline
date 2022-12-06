#!/bin/bash

# Import Agave runtime extensions
. _lib/extend-runtime.sh

# Unzip dicoms locally 
#shellcheck disable=SC2086
LOCAL_DICOM=$(basename ${FILES})
# remove zip suffix
#shellcheck disable=SC2086
LOCAL_DICOM=${LOCAL_DICOM%.*}
#shellcheck disable=SC2086
unzip ${FILES} -d ${LOCAL_DICOM}

# UM occasionally sends duplicated DICOM files, which will break dcmstack.
# A known pattern is that these files are nested inside the folder of the scan that is duplicated 
# (hence -mindepth 2), and the directory of files starts with the letter s.
if [[ ${SITE} == UM ]]; then
#shellcheck disable=SC2086
  duplicate=$(find ${LOCAL_DICOM} -mindepth 2 -type d)
  duplicate_dir=$(basename "${duplicate}")
  if [[ ${duplicate_dir:0:1} == s ]]; then
    echo "deleting UM duplicate $duplicate"
    rm -r "${duplicate}"
  fi
fi

case "${SITE}" in
  UC) 
    echo singularity run \
      --cleanenv \
      --env ENV_NAME=UC \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
      "
      

    singularity run \
      --cleanenv \
      --env ENV_NAME=UC \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
      "
    ;;

  SH)
    echo singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20220720 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && python exclude_derived-dwi_sh.py ${LOCAL_DICOM}
      "

    singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20220720 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && python exclude_derived-dwi_sh.py ${LOCAL_DICOM}
      "

    echo singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20220720 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM}  --minmeta \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
      "

    singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20220720 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM}  --minmeta \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
      "

    # heudiconv is unable to find the acquisition datetime, so we fill them manually
    # note that this script does not currently add the exact time, just the acq_date
    echo singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20220720 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && python add_date_to_sh.py ${LOCAL_DICOM} ${OUTDIR}
      "

    singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20220720 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && python add_date_to_sh.py ${LOCAL_DICOM} ${OUTDIR}
      "
    ;;

  *)
    echo singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20211006 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
      "

    singularity run \
      --cleanenv \
      --env ENV_NAME=v1.0.20211006 \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
        && heudiconv \
          ${DICOM_DIR_TEMPLATE} --files ${LOCAL_DICOM} \
          ${LIST_OF_SUBJECTS} \
          ${CONVERTER} \
          --outdir ${OUTDIR} \
          ${LOCATOR} ${ANON_CMD} \
          ${HEURISTIC} \
          ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
          ${DATALAD} ${DCMCONFIG}
      "
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
      singularity run --cleanenv --env ENV_NAME=v1.0.20211006 \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        bash -c "
          source /usr/local/bin/_activate_current_env.sh && python clean_nsphantom.py ${OUTDIR}
        "
      ;;
    UC)
      # For UC, dcm2niix generates extra "ADC" scans, which are derived volumes. They could be 
      # avoided by using the -i y flag, except that flag would also cause dcm2niix to skip the anat 
      # scans from NS
      find "${OUTDIR}" -name "*ADC*" -delete
      ;;
    WS)
      # heuristic can result in run-1 tag, unlike all other sites
      singularity run --cleanenv --env ENV_NAME=v1.0.20211006 \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        bash -c "
          source /usr/local/bin/_activate_current_env.sh && python clean_wsphantom.py ${OUTDIR}
        "
      ;;
  esac
  else
  PHANTOM="--no-phantom"
fi

# Need to inject IntendedFor field into some jsons, and in the case of GE images
# generate the AP/PA fieldmaps. Heudiconv outputs them as readonly, so temporarily
# give write access to user, read to group
readonly FILE_EDITS=("${OUTDIR}"/sub-*/ses-*/*/*) \
  && chmod +640 "${FILE_EDITS[@]}"

# Delete duplicate scans if flag is set
echo "delete duplicates flag set to: ${DELETE_DUPLICATES}"

mapfile -t dups < <(find "${OUTDIR}" -type f -name "*dup*")
if (( ${#dups[@]} > 1 )); then
  # post about found duplicates to slack channel
  msg="duplicate scans found: ${dups[*]}"

  singularity run \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    --env ENV_NAME=v1.0.20211006 \
    --cleanenv docker://"${CONTAINER_IMAGE}" python log.py "${msg}" "${POST}"
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
        --env ENV_NAME=v1.0.20211006 \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        bash -c "
          source /usr/local/bin/_activate_current_env.sh && python create_fieldmaps_GE.py ${OUTDIR}
          "

      singularity run \
        --cleanenv \
        --env ENV_NAME=v1.0.20211006 \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        bash -c "
          source /usr/local/bin/_activate_current_env.sh && python create_fieldmaps_GE.py ${OUTDIR}
          "

      # Adding the correct GE bvals and bvec file. Added on Sept 28,2021.
      echo "Replacing correct bval and bvec files..."
      cat correct_bval_GE>"${OUTDIR}"/sub-*/ses-*/dwi/*bval
      cat correct_bvec_GE>"${OUTDIR}"/sub-*/ses-*/dwi/*bvec
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
        --env ENV_NAME=v1.0.20211006 \
        -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" \
        bash -c "
          source /usr/local/bin/_activate_current_env.sh && python index_coilqa.py ${OUTDIR}/sub-umphantom/ses*/anat/*T1w.nii.gz
          "
    ;;
  esac
fi

echo singularity run \
  --cleanenv \
  --env ENV_NAME=v1.0.20211006 \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" \
    bash -c "
      source /usr/local/bin/_activate_current_env.sh && python edit_json.py ${OUTDIR}
      "

singularity run \
  --cleanenv \
  --env ENV_NAME=v1.0.20211006 \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  docker://"${CONTAINER_IMAGE}" \
    bash -c "
      source /usr/local/bin/_activate_current_env.sh && python edit_json.py ${OUTDIR}
      "


# resting state scans do not require events files (there are no events)
# so delete any that are found
find "${OUTDIR}" -type f -name '*task-rest*events.tsv' -delete

set -x
if [[ ${CHECK_JSONS} == 1 ]]; then
  # the check is a bit messy. Previously, $SITE could reliably distinguish acquisition protocol. Now, sites
  # have both a patient protocol and a phantom protocol, which always differ. So, the checks must
  # be divided by whether we're dealing with a phantom scan or not.
  singularity run \
    --cleanenv \
    --env ENV_NAME=v1.0.20211006 \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://"${CONTAINER_IMAGE}" \
      bash -c "
        source /usr/local/bin/_activate_current_env.sh \
          && python check_acq.py ${OUTDIR} ${SITE} ${PHANTOM} ${POST}
        "
else
  echo "Skipping check of jsons"
fi

# end with check of newly created directory. if the output is not valid, the job will fail
singularity run \
  -B "${BIND_DIR}":"${BIND_DIR}" \
  --env ENV_NAME=v1.0.20220720 \
  docker://"${CONTAINER_IMAGE}" bids-validator --ignoreWarnings "${OUTDIR}"
  