# Import Agave runtime extensions
. _lib/extend-runtime.sh

# Allow CONTAINER_IMAGE over-ride via local file
if [ -z "${CONTAINER_IMAGE}" ]
then
    if [ -f "./_lib/CONTAINER_IMAGE" ]; then
        CONTAINER_IMAGE=$(cat ./_lib/CONTAINER_IMAGE)
    fi
    if [ -z "${CONTAINER_IMAGE}" ]; then
        echo "CONTAINER_IMAGE was not set via the app or CONTAINER_IMAGE file"
        CONTAINER_IMAGE="jurrutia/ubuntu17"
    fi
fi



#IF UCHICAGO 
#python3 run_delete_trigger_tag_philips.py ${FILES}
#echo singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 run_delete_trigger_tag_philips.py /scratch1/05369/urrutia/uchicago_test/dicom/UC042121QA/DICOM
#singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 run_delete_trigger_tag_philips.py /scratch1/05369/urrutia/uchicago_test/dicom/UC042121QA/DICOM

if [[ $SITE == "UC" ]]
then
    echo singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 run_delete_trigger_tag_philips.py ${FILES}
    singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 run_delete_trigger_tag_philips.py ${FILES}
    export DICOM=dicom
fi

echo singularity exec \
    -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
    docker://${CONTAINER_IMAGE} \
    heudiconv \
    ${DICOM_DIR_TEMPLATE} ${FILES} ${DICOM} \
    ${LIST_OF_SUBJECTS} \
    ${CONVERTER} \
    --outdir ${OUTDIR} \
    ${LOCATOR} ${CONV_OUTDIR} ${ANON_CMD} \
    ${HEURISTIC} \
    ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
    ${DATALAD} ${DCMCONFIG}

singularity exec \
    -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
    docker://${CONTAINER_IMAGE} \
    heudiconv \
    ${DICOM_DIR_TEMPLATE} ${FILES} ${DICOM} \
    ${LIST_OF_SUBJECTS} \
    ${CONVERTER} \
    --outdir ${OUTDIR} \
    ${LOCATOR} ${CONV_OUTDIR} ${ANON_CMD} \
    ${HEURISTIC} \
    ${SESSION_FOR_LONGITUDINAL} ${BIDS} ${OVERWRITE} \
    ${DATALAD} ${DCMCONFIG}

# add bval, bvec, betc to .bidsignore
cat bids_ignore >> .bidsignore

if [[ $SITE == "UI" ]]
then
    echo singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 create_fieldmaps_GE .
    singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 create_fieldmaps_GE .
fi

echo singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 edit_json.py .
singularity exec docker://jurrutia/pydicom:3.6.5.1 python3 edit_json.py .



# quick python to remove null values from participants.tsv
python3 participants.py

# When you use spin echo scans for B0 mapping in order to use the PEPOLAR method, 
# your acquisition is effectively a DWI with b=0. Because of this, the dcm2niix 
# converter creates bval/bvec files, though we don't actually need them. 
# decided that it's cleaner to remove
# (https://a2cps-pain.slack.com/archives/C027U8CBFL3/p1627388270028600)
BV_FILES=$( ls "${OUTDIR}/sub-${LIST_OF_SUBJECTS}/ses-${SESSION_FOR_LONGITUDINAL}/fmap/"*{bval,bvec} )
if [[ -n "${BV_FILES}" ]]; then
  echo "deleting extra bval/bvec files: ${BV_FILES}"
  rm BV_FILES
fi

