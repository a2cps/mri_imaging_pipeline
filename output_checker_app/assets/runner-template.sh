

# Echo command to std out
echo singularity exec \
        -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
        -e \
        python output_check.py "{ 
                \"subject_id\": \"$SUBJECT_ID\",
                \"visit\": \"$VISIT\",
                \"T1 Indicated\": \"$ANAT\",
                \"DWI Indicated\": \"$DWI\",
                \"fMRI Individualized Pressue Indicated\": \"$CUFF1\",
                \"fMRI Standard Pressure\": \"$CUFF2\",
                \"1st Resting State Indicated\": \"$REST1\",
                \"2nd Resting State Indicated\": \"$REST2\"
                }" \
                $BIDS \
                $REPORT_CSV


singularity exec \
        -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
        -e \
        python output_check.py "{ 
                \"subject_id\": \"$SUBJECT_ID\",
                \"visit\": \"$VISIT\",
                \"T1 Indicated\": \"$ANAT\",
                \"DWI Indicated\": \"$DWI\",
                \"fMRI Individualized Pressue Indicated\": \"$CUFF1\",
                \"fMRI Standard Pressure\": \"$CUFF2\",
                \"1st Resting State Indicated\": \"$REST1\",
                \"2nd Resting State Indicated\": \"$REST2\"
                }" \
                $BIDS \
                $REPORT_CSV

