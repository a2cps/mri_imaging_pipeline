#!/bin/bash
set -e

date

readonly OUT_MRIQC="${OUTROOT}/mriqc-group/a2cps/"
readonly OUT_BIDS="${OUTROOT}/bids/a2cps/"

[[ ! -d "${OUT_BIDS}" ]] && mkdir -p "${OUT_BIDS}"
[[ ! -d "${OUT_MRIQC}" ]] && mkdir -p "${OUT_MRIQC}"

# create symlinks to all new outputs in the bids and mriqc folders
# -s: symlink
# -R: recursive
# -n: never clobber
for site in ${SITES}; do

  # test if multiple files exist
  # https://stackoverflow.com/a/51062686
  # only copy when passing test
  in_bids=("${INROOT}"/"${site}"/bids/*/sub-*)
  if [[ -d "${in_bids[0]}"  ]]; then
    for f in "${in_bids[@]}"; do
      cp -sRnv "${f}" "${OUT_BIDS}"
    done
  fi

  in_mriqc=("${INROOT}"/"${site}"/mriqc/*/sub-*)
  if [[ -d "${in_mriqc[0]}" ]]; then
    for f in "${in_mriqc[@]}"; do
      cp -sRnv "${f}" "${OUT_MRIQC}"
    done
  fi

done

set -x

# extra files requires to make valid BIDS dataset
# note that these are just placeholders and don't actually contain relevant information
echo symlinked > "${OUT_BIDS}/README"
cp dataset_description.json "${OUT_BIDS}"

# NOTE: since bids and mriqc files are only symlinks, the targets of the 
# symlinks must also be bound (hence -B for INROOT)
singularity run \
  --cleanenv \
  -B "${INROOT}":"${INROOT}":ro \
  -B "${OUT_BIDS}":/bids:ro \
  -B "${OUT_MRIQC}":/mriqc \
  docker://"${CONTAINER_IMAGE}" \
  /bids /mriqc group

set +x

date
