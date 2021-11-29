#!/bin/bash

. lib/container_exec.sh

set -x

date

[[ ! -d "${OUTDIR}" ]] && mkdir -p "${OUTDIR}"

# allows running when SUBLONG is specified with job.json, and if not 
# defaulting to updated list of participants for which bids_validation == 1
if [[ -z "${SUBLONG}" ]]; then
  # assumes that bids_validation is column 18 in this file
  readarray -t SUBSLONG < <(awk -F ',' '{ if ($18 == 1)  print $1$2$3 }' "${CSV}")
else
  read -ra SUBSLONG <<< "${SUBLONG}"
fi

for s in "${SUBSLONG[@]}"; do
  site=${s:0:2}
  case ${site} in
    NS)
      sitelong=NS_northshore
      ;;
    UI)
      sitelong=UI_uic
      ;;
    UM)
      sitelong=UM_umichigan
      ;;
    UC)
      sitelong=UC_uchicago
      ;;
    WS)
      sitelong=WS_wayne_state
      ;;
    SH)
      sitelong=SH_spectrum_health
      ;;
  esac

  sub=${s:2:5}  
  in_sub_dir="${INROOT}/${sitelong}/bids/${s}"

  cp -sRu "${in_sub_dir}/sub-${sub}" "${OUTDIR}/"
    
  # singularity exec \
  #   --cleanenv \
  #   -B "${INROOT}":"${INROOT}":ro \
  #   -B "${OUTDIR}":"${OUTDIR}" \
  #   docker://"${CONTAINER_IMAGE}" \
  #   python update_participants.py "${OUTDIR}/participants.tsv" "${in_sub_dir}/participants.tsv" "${site}"

done

# extra files required to make valid BIDS dataset
# these are placeholders only and don't contain relevant information
echo symlinked > "${OUTDIR}/README"
cp dataset_description.json "${OUTDIR}"
cat bids_ignore >> "${OUTDIR}"/.bidsignore
