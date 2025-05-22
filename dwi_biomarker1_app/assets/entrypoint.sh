#!/bin/bash

set -ex

extract_voxels (){

    local i=${1}
    local PREFIX=${2}
    local VOXINDEX=${3}

    echo "${i}"

    # Extract each voxel into a separate nii file (binarized output)
    fslmaths "${VOXINDEX}" \
        -thr "${i}" \
        -uthr "${i}" \
        -bin \
        "${PREFIX}"vox"${i}"_bin.nii.gz

}

do_voxelwise_tractography (){

    local i=${1}
    local BEDPOSTXDIR=${2}
    local PREFIX=${3}
    local DIR_PROBTRACKX_OUTPUT=${4}

    echo "running voxel " "${i}"
    local tractdir="${DIR_PROBTRACKX_OUTPUT}"/voxelwise/vox-"${i}"

    mkdir -p "${tractdir}"

    # Run tractography
    probtrackx2 \
        -x "${PREFIX}"vox"${i}"_bin.nii.gz \
        -l \
        --onewaycondition \
        -c 0.2 \
        -S 2000 \
        --steplength=0.5 \
        -P 5000 \
        --fibthresh=0.01 \
        --distthresh=0.0 \
        --sampvox=0.0 \
        --forcedir \
        --opd \
        --ompl \
        -s "${BEDPOSTXDIR}"/merged \
        -m "${BEDPOSTXDIR}"/nodif_brain_mask.nii.gz \
        --dir="${tractdir}" \
        --modeuler
        ## not including distance correction (would be --pd), doing in matlab instead

}

find_and_merge(){
    local DST=${1}
    local SRC_DIR=${2}
    local PATTERN=${3}

    local to_merge
    mapfile -t to_merge < <(find "${SRC_DIR}" -type f -name "${PATTERN}" | sort -V)
    fslmerge -t "${DST}" "${to_merge[@]}"

}

main (){

    local SUB=${1}
    local SES=${2}
    local QSIPREPDIR=${3}
    local BEDPOSTXDIR=${4}
    local OUTDIR=${5}
    local ROIPREPDIR=${6:-/opt/tapis/rois}
    local N_WORKERS=${7:-1}

    mkdir -p "${OUTDIR}"
    local participant_label=sub-"${SUB}"
    local session_label=ses-"${SES}"

    ###########################################################################################################
    ## STEP 1: Define paths/files (qsiprep and qsirecon-FSL)

    ## Redefine subject paths
    local dir_qsiprep_dwi="${QSIPREPDIR}"/"${participant_label}"/"${session_label}"/dwi
    local dir_qsiprep_anat="${QSIPREPDIR}"/"${participant_label}"/anat

    ## Define qsiprep files
    local qsiprep_xfm_mni2dwi="${dir_qsiprep_anat}"/"${participant_label}"_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5
    local qsiprep_dwi_ref="${dir_qsiprep_dwi}"/"${participant_label}"_"${session_label}"_space-T1w_dwiref.nii.gz

    ###########################################################################################################
    ## STEP 2: Move masks from MNI to native (preproc)

    ## Define mask files
    local mask_index_MNI1mm="${ROIPREPDIR}"/modules_all_in_MNI152NLin2009cAsym_brain.nii.gz

    ## Create output dir
    local dir_move_masks="${OUTDIR}"/move_masks/"${participant_label}"/"${session_label}"/dwi
    mkdir -p "${dir_move_masks}"

    ## Define variables
    local interp="NearestNeighbor" # NOTE, ideal to not use GenericLabel (removes smallest clusters, e.g. amygdala)

    ## Move mask (index) to native dwi (preproc) and reorient to qsirecon-FSL
    local dwi_ind="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwi_desc-modules_dseg.nii.gz
    local dwifslstd_ind="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-modules_dseg.nii.gz

    antsApplyTransforms -d 3 \
        -i "${mask_index_MNI1mm}" \
        --interpolation "${interp}" \
        -t "${qsiprep_xfm_mni2dwi}" \
        -r "${qsiprep_dwi_ref}" \
        -o "${dwi_ind}"

    ## Reorient mask in native (preproc) dwi to match qsirecon-FSL
    fslswapdim "${dwi_ind}" x -y z "${dwifslstd_ind}"
    fslorient -swaporient "${dwifslstd_ind}"

    ###########################################################################################################
    ## STEP 3: Split mask (native DWI fslstd) into separate voxel seed files

    # make image in which all background (0) voxels are set to -1, and the others 0
    local tmpdir
    tmpdir=$(mktemp -d)
    local binvmask="${tmpdir}"/bininv.nii.gz
    fslmaths "${dwifslstd_ind}" -binv -mul -1 "${binvmask}"

    # add voxelwise index to mask, use binvmask to subtract 1 from all background voxels, then increment index by 1
    # this roundabout procedure is done because the -index flag sets the lowest index to 0, which is the same value of s
    # the background (causing a voxel to be lost)
    local dwifslstd_voxind="${dir_move_masks}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-modulesvox_dseg.nii.gz

    fslmaths "${dwifslstd_ind}" \
        -bin \
        -index \
        -add "${binvmask}" \
        -add 1 \
        "${dwifslstd_voxind}"

    ## get number of nonzero voxels
    local num_voxels
    num_voxels=$(fslstats "${dwifslstd_voxind}" -V | cut -f 1 -d " ")

    ## split mask into separate voxels

    local voxels
    mapfile -t voxels < <(seq 1 "${num_voxels}")

    ## create output dir
    local dir_split_masks="${dir_move_masks}"/seed_voxels
    mkdir -p "${dir_split_masks}"

    local modulesvox_prefix="${dir_split_masks}"/"${participant_label}"_"${session_label}"_desc-modulesvox

    parallel --link -j "${N_WORKERS}" extract_voxels \
        ::: "${voxels[@]}" \
        ::: "${modulesvox_prefix}" \
        ::: "${dwifslstd_voxind}" 


    ###########################################################################################################
    ## STEP 4: Probtrackx (tractography, voxelwise seeds)

    ## Define output dir
    local dir_probtrackx_output="${OUTDIR}"/probtrackx/"${participant_label}"/"${session_label}"/dwi
    mkdir -p "${dir_probtrackx_output}"

    ## Run voxelwise tractography

    parallel --link -j "${N_WORKERS}" do_voxelwise_tractography \
        ::: "${voxels[@]}" \
        ::: "${BEDPOSTXDIR}"/"${participant_label}"/"${session_label}"/dwi.bedpostx \
        ::: "${modulesvox_prefix}" \
        ::: "${dir_probtrackx_output}"


    ###########################################################################################################
    ## STEP 5: Postprocessing of probtrackx outputs

        ## NOTE: no need to reorient to space-T1w first (ideal to keep in native tractography space, but have code if needed)

    ## Merge into 4D files

    ## merge all (fdt_paths)
    find_and_merge \
        "${dir_probtrackx_output}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-DWIbiomarker1fdtpaths_dwi.nii.gz \
        "${dir_probtrackx_output}" \
        fdt_paths.nii.gz

    ## merge all (fdt_lengths)
    find_and_merge \
        "${dir_probtrackx_output}"/"${participant_label}"_"${session_label}"_space-dwifslstd_desc-DWIbiomarker1fdtlengths_dwi.nii.gz \
        "${dir_probtrackx_output}" \
        fdt_paths_lengths.nii.gz

    ###########################################################################################################
    ## STEP 6: Cleanup files

    # Remove seed voxels (>10k per subj)
    rm -r "${dir_split_masks}"

    # Remove voxelwise probtrackx outputs (>10k per subj)
    rm -r "${dir_probtrackx_output}"/voxelwise

}

export -f main extract_voxels do_voxelwise_tractography find_and_merge

main "$@"