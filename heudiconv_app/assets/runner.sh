#!/bin/bash
set -x
declare -xr LAUNCHER_WORKDIR="${PWD}"
declare -xr LAUNCHER_JOB_FILE="${PWD}/launchfile" 

#######################################
# single job to process individual participant
# Arguments:
#   zipped dicom folder, absolute or relative. ideally of the form <site><sub><ses>
#   output folder where bids directory will be placed
# Outputs:
#   creates bids folder at location of second argument
# Returns:
#   nothing
#######################################
job() {
  local zip="${1}"
  local out="${2}"

  # Unzip dicoms locally 
  local local_dicom
  local_dicom=$(basename "${zip}")
  # remove zip suffix
  local_dicom=${local_dicom%.*}
  unzip "${zip}" -d "${local_dicom}"

  if [[ -z "${SITE}" ]]; then
    local sitecode
    sitecode=$( grep -Po "(NS|SH|UC|UM|UI|WS)" <<< "${local_dicom}" )
  else
    sitecode=${SITE}
  fi

  if [[ -z "${SESSION_FOR_LONGITUDINAL}" ]]; then
    local session
    session=$( grep -Po "(V|v)[13]" <<< "${local_dicom}" )
  else
    session=${SESSION_FOR_LONGITUDINAL}
  fi

  if [[ -z "${LIST_OF_SUBJECTS}" ]]; then
    local subjects
    subjects=$( grep -Po "([0-9]{5})" <<< "${local_dicom}" )
  else
    subjects=${LIST_OF_SUBJECTS}
  fi

  if [[ "${sitecode}" == UC ]]; then
    # UC needs custom version of dcm2niix
    # see https://confluence.a2cps.org/display/WG/2021-12-21+DIRC+Meeting+notes
    # if/else can be removed when dcm2niix updated for Spring 2022 release
    singularity exec \
      --cleanenv \
      --env PREPEND_PATH=/opt/dcm2niix-UC/bin \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      heudiconv \
      ${DICOM_DIR_TEMPLATE} --files "${local_dicom}" \
      --subjects "${subjects}" \
      ${CONVERTER} \
      --outdir "${out}" \
      ${LOCATOR} ${ANON_CMD} \
      ${HEURISTIC} \
      --ses "${session}" ${BIDS} ${OVERWRITE} \
      ${DATALAD} ${DCMCONFIG}
  else
    singularity exec \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
      docker://"${CONTAINER_IMAGE}" \
      heudiconv \
      ${DICOM_DIR_TEMPLATE} --files "${local_dicom}" \
      --subjects "${subjects}" \
      ${CONVERTER} \
      --outdir "${out}" \
      ${LOCATOR} ${ANON_CMD} \
      ${HEURISTIC} \
      --ses "${session}" ${BIDS} ${OVERWRITE} \
      ${DATALAD} ${DCMCONFIG}
  fi 

  # Remove local dicom directory
  rm -rf "${local_dicom}"

  # add bval, bvec, betc to .bidsignore
  cat bids_ignore >> "${out}"/.bidsignore

  # Need to inject IntendedFor field into some jsons, and in the case of GE images
  # generate the AP/PA fieldmaps. Heudiconv outputs them as readonly, so temporarily
  # give write access to user, read to group
  chmod +640 "${out}"/sub-*/ses-*/*/*

  # Delete duplicate scans if flag is set
  echo "delete duplicates flag set to: ${DELETE_DUPLICATES}"
  if [[ "${DELETE_DUPLICATES}" == 1 ]]; then
    # delete duplicte scans
    echo "removing duplicate scans"
    rm -rf "${out}"/sub-*/ses-*/*/*_dup*
    # remove duplicate scans from scans.tsv
    sed -i '/_dup/d' "${out}"/sub-*/ses-*/*scans.tsv
  else
    echo "adding duplicate scans to bids ignore"
    # otherwise add to bids ignore
    echo "${out}/sub-*/ses-*/*/*_dup*" >> .bidsignore
    # remove duplicate scans from scans.tsv
    sed -i '/_dup/d' "${out}"/sub-*/ses-*/*scans.tsv
  fi

  case "${sitecode}" in
    UI | UM)
      singularity exec \
      --cleanenv \
      -B "${BIND_DIR}":"${BIND_DIR}" \
        docker://"${CONTAINER_IMAGE}" python3 create_fieldmaps_GE.py "${out}"

      # Adding the correct GE bvals and bvec file. Added on Sept 28,2021.
      echo "Replacing correct bval and bvec files..."
      cat correct_bval_GE>"${out}"/sub-*/ses-*/dwi/*bval
      cat correct_bvec_GE>"${out}"/sub-*/ses-*/dwi/*bvec
      ;;
  esac

  singularity exec \
    --cleanenv \
    -B "${BIND_DIR}":"${BIND_DIR}" \
    docker://"${CONTAINER_IMAGE}" python3 edit_json.py "${out}"

}

main() {
  
  read -ra zips <<< "${FILES}"
  read -ra outs <<< "${OUTDIR}"

  if [[ ! "${#zips[@]}" == "${#outs[@]}" ]]; then
    echo "lengh of FILES must equal length of OUTDIR"
    exit 1
  fi

  # build up launcher file
  # the jobs will need access to the function "job". writing it here
  local jobfunfile
  jobfunfile=$(mktemp)
  declare -f job > "${jobfunfile}"
  
  # start with empty file. each iteration of loop will add new launcher line
  : > "${LAUNCHER_JOB_FILE}"
  for f in "${!zips[@]}"; do
    printf "set -ex; source %s; job %s %s > %s 2> %s \n" \
    "${jobfunfile}" "${zips[f]}" "${outs[f]}" "${f}".out "${f}".err \
    >> "${LAUNCHER_JOB_FILE}"
  done

  "${LAUNCHER_DIR}"/paramrun
  rm "${jobfunfile}"  
}

main
