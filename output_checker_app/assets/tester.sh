#!/usr/bin/env bash

return 0

echo singularity exec \
        -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
        -e \
        python output_check.py "{ 
                \"subject_id\": \"10015\",
                \"visit\": \"V3\",
                \"T1 Indicated\": \"1\",
                \"DWI Indicated\": \"1\",
                \"fMRI Individualized Pressure Indicated\": \"1\",
                \"fMRI Standard Pressure Indicated\": \"0\",
                \"1st Resting State Indicated\": \"1\",
                \"2nd Resting State Indicated\": \"1\"
                }" \
                /corral-secure/projects/A2CPS/products/mris/UI_uic/bids/UI10015V3 \
                test.xls

singularity exec \
        -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
        -e \
        python output_check.py "{ 
                \"subject_id\": \"$SUBJECT_ID\",
                \"visit\": \"$VISIT\",
                \"T1 Indicated\": \"$ANAT\",
                \"DWI Indicated\": \"$DWI\",
                \"fMRI Individualized Pressure Indicated\": \"$CUFF1\",
                \"fMRI Standard Pressure Indicated\": \"$CUFF2\",
                \"1st Resting State Indicated\": \"$REST1\",
                \"2nd Resting State Indicated\": \"$REST2\"
                }" \
                /corral-secure/projects/A2CPS/products/mris/UI_uic/bids/UI10015V3 \
                test.xls
