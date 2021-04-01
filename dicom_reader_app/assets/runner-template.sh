# Import Agave runtime extensions
. _lib/extend-runtime.sh

# BUG Input Directory ${BIDS_DIRECTORY} not defined
# using some bash tricks to get if from the participant label
#DIR=*/${PARTICIPANT_LABEL}
#DIR=$(echo ${DIR} | cut -d "/" -f1)
echo Input is ${FILENAME}

# Usage: container_exec IMAGE COMMAND OPTIONS
#   Example: docker run centos:7 uname -a
#            container_exec centos:7 uname -a

# module load python3
# python3 file_check.py ${FILES} ${OUTDIR} 
# # Defines dicom_dir
# source .listfile.txt

mkdir -p  ${OUTPUT_DIR}/work
PYTHONPATH=""
# Echo command to std out
echo singularity run \
            -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
            docker://${CONTAINER_IMAGE} \
            python file_check.py ${FILENAME} 

singularity run \
            -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
            docker://${CONTAINER_IMAGE} \
            python file_check.py ${FILENAME} 
