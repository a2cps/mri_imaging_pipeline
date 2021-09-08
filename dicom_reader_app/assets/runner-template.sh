# Import Agave runtime extensions
. _lib/extend-runtime.sh


echo Input is ${FILENAME}

# Echo command to std out
echo singularity run \
            -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
            docker://${CONTAINER_IMAGE} \
            python file_check.py ${FILENAME} ${SUBJECT_ID}

singularity run \
            -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
            docker://${CONTAINER_IMAGE} \
            python file_check.py ${FILENAME} ${SUBJECT_ID}
