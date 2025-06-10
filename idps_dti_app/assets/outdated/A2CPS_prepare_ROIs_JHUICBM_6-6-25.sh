#!/bin/bash

## setup

module unload xalt
module load tacc-apptainer

# load my docker to allow FSL

singularity shell -B /corral-secure/projects/A2CPS/:/corral-secure/projects/A2CPS/ docker://jurrutia/fmriprep:20.2.3.1

##############################
## Resample/register the original masks from old MNI to new 1mm MNI

templatedir=/corral-secure/projects/A2CPS/shared/maj/template
prepROIdir=/corral-secure/projects/A2CPS/shared/maj/IDPs_UKB_A2CPS/DTI_IDPs/prepare_ROIs/JHU_ICBM


# move JHUICBM from older MNI (1mm) to newer MNI (1mm)
input=${prepROIdir}/JHU-ICBM-labels-1mm
refname=MNI152NLin2009cAsym_brain
ref=${templatedir}/tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w
transform=${templatedir}/tpl-MNI152NLin2009cAsym_from-MNI152NLin6Asym_mode-image_xfm.h5
output=${input}_in_${refname}

# Note, don't use --interpolation Genericlabel (diff result from NN, fewer voxels)
antsApplyTransforms -d 3 \
-i ${input}.nii.gz \
--interpolation GenericLabel \
-t ${transform} \
-r ${ref}.nii.gz \
-o ${output}.nii.gz



