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


# Usage: container_exec IMAGE COMMAND OPTIONS
#   Example: docker run centos:7 uname -a
#            container_exec centos:7 uname -a

# Echo command to std out
echo singularity run  \
    -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
    docker://${CONTAINER_IMAGE} ${CONFIG_IGNORE} ${BIDS_DIRECTORY}


singularity run \
     -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ \
     docker://${CONTAINER_IMAGE} ${CONFIG_IGNORE} ${BIDS_DIRECTORY}
