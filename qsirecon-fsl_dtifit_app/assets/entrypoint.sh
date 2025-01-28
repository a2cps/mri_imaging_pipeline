#!/usr/bin/env bash

main (){

    local BIDSDIR="${1}"
    local WORKDIR="${2}"
    local QSIPREPDIR="${3}"
    local OUTDIR="${4}"
    local PARTICIPANT_LABEL="${5}"
    local NTHREADS="${6}"
    local MEMMB="${7}"
    local LICENSE="${8}"

        ## note: splitshellsdir should be: 
        ## /corral-secure/projects/A2CPS/shared/maj/qsirecon-fsl_dtifit_app/derivatives/split_shells

        ## note: DTIFITDIR should be: 
        ## /corral-secure/projects/A2CPS/shared/maj/qsirecon-fsl_dtifit_app/derivatives/dtifit

    ## RUN QSIRECON

    ## Note, submit example


    qsiprep \
        --participant_label "${PARTICIPANT_LABEL}" \
        --work-dir "${WORKDIR}" \
        --recon-only \
        --recon_spec reorient_fslstd \
        --recon_input "${QSIPREPDIR}" \
        --nthreads "${NTHREADS}" \
        --mem_mb "${MEMMB}" \
        --fs-license-file "${LICENSE}" \
        "${BIDSDIR}" "${OUTDIR}" participant

    echo "qsiprep recon finished!"


    ######################
    #### Split Shells ####

    ## DEFINE ARGS

    ## inputs from qsirecon FSL
    local qsirecon_dir="${OUTDIR}"/qsirecon/"${PARTICIPANT_LABEL}"/ses-V1/dwi

    ## define base filenames

    local filename_dwi="${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi
    local filename_bvals="${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi
    local filename_bvecs="${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi

    local infile_dwi="${qsirecon_dir}"/"${filename_dwi}".nii.gz
    local infile_bvals="${qsirecon_dir}"/"${filename_bvals}".bval
    local infile_bvecs="${qsirecon_dir}"/"${filename_bvecs}".bvec

    #########
    ## b=0 ##

    bval=0

    local splitshells_dir="${OUTDIR}"/split_shells/"${PARTICIPANT_LABEL}"/ses-V1/b${bval}
    mkdir -p "${splitshells_dir}"


    local outfile_b0_dwi="${splitshells_dir}"/"${filename_dwi}"_b"${bval}".nii.gz
    local outfile_b0_bvals="${splitshells_dir}"/"${filename_bvals}"_b"${bval}".bval
    local outfile_b0_bvecs="${splitshells_dir}"/"${filename_bvals}"_b"${bval}".bvec


    ## Subselect indices
    indices_b0=$(awk -v target="${bval}" '
    {
    # $1 is the b-value on this line (since each line has exactly one field)
    if ($1 == target) {
        # Print 0-based line index
        printf("%d ", NR-1)
    }
    }' "${infile_bvals}")
    echo "Indices for b=${bval}: ${indices_b0}"


    ## Extract from dwi data

    fslselectvols \
    -i "${infile_dwi}" \
    -o "${outfile_b0_dwi}" \
    --vols="${indices_b0}"


    ## Extract from bvals

    awk -v idx="${indices_b0}" '
    BEGIN {
        # Split the space-separated volume indices into an array,
        # and store the number of elements in arrLen
        arrLen = split(idx, arr, " ")
        # Create a lookup table "wantedLines" to mark which lines we need
        for (i = 1; i <= arrLen; i++) {
            wantedLines[arr[i]] = 1
        }
    }

    {
        # NR is the (1-based) line number in the file
        # We want 0-based, hence NR-1
        if (wantedLines[NR-1]) {
            # Print the single b-value on its own line
            print $1
        }
    }
    ' "${infile_bvals}" > "${outfile_b0_bvals}"


    ## Extract from bvecs

    awk -v idx="${indices_b0}" '
    BEGIN {
        # Split the space-separated list of 0-based indices into array "arr"
        n = split(idx, arr, " ")
        
        # Create a lookup table to quickly check if an index is wanted
        for (i=1; i<=n; i++) {
            wanted[ arr[i] ] = 1
        }
    }

    {
        # For each line (row in the bvecs file), parse the space-separated fields
        split($0, fields, /[ \t]+/)
        
        # Build an output line with only the columns whose index is in "wanted"
        out = ""
        for (f=1; f<=NF; f++) {
            # f is 1-based in AWK, so (f-1) is the 0-based column index
            if (wanted[f-1]) {
                if (out == "") {
                    out = fields[f]
                } else {
                    out = out " " fields[f]
                }
            }
        }
        # Print the resulting line (preserves row structure)
        print out
    }
    ' "${infile_bvecs}" > "${outfile_b0_bvecs}"


    ## Copy brain mask
    filename_brainmask="${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_mask
    infile_brainmask="${qsirecon_dir}"/"${filename_brainmask}".nii.gz
    outfile_brainmask="${splitshells_dir}"/"${filename_brainmask}".nii.gz
    cp "${infile_brainmask}" "${outfile_brainmask}"


    #############################################
    ## Loop through bvals (1000, 2000, 3000)

    for bval in 500 1000 2000 3000 ; do

    local splitshells_dir="${OUTDIR}"/split_shells/"${PARTICIPANT_LABEL}"/ses-V1/b${bval}
    mkdir -p "${splitshells_dir}"

    local outfile_dwi="${splitshells_dir}"/"${filename_dwi}"_b"${bval}".nii.gz
    local outfile_bvals="${splitshells_dir}"/"${filename_bvals}"_b"${bval}".bval
    local outfile_bvecs="${splitshells_dir}"/"${filename_bvals}"_b"${bval}".bvec

    ## Subselect indices
    indices=$(awk -v target="${bval}" '
    {
    # $1 is the b-value on this line (since each line has exactly one field)
    if ($1 == target) {
        # Print 0-based line index
        printf("%d ", NR-1)
    }
    }' "${infile_bvals}")
    echo "Indices for b=${bval}: ${indices}"

    indices_combined="$(echo "${indices_b0} ${indices}" | xargs)"
    echo "Indices for b=0 + b=${bval}: $indices_combined"

    ## Extract from dwi data

    fslselectvols \
    -i "${infile_dwi}" \
    -o "${outfile_dwi}" \
    --vols="${indices_combined}"


    ## Extract from bvals

    awk -v idx="${indices_combined}" '
    BEGIN {
        # Parse space-separated list of desired 0-based volume indices
        n = split(idx, volList, " ")
    }

    # Store each line in an array, keyed by 0-based line number (NR-1)
    {
        allLines[NR-1] = $1
    }

    END {
        # Now print lines in the exact order given by volList[]
        for (i=1; i<=n; i++) {
            volIndex = volList[i]    # this is a 0-based index
            print allLines[volIndex]
        }
    }
    ' "${infile_bvals}" > "${outfile_bvals}"


    ## Extract from bvecs

    awk -v idx="${indices_combined}" '
    BEGIN {
        # Split the space-separated indices into volList
        n = split(idx, volList, " ")
    }

    # Read each line (row) into 2D array allRows[rowNum, colIndex]
    {
        rowNum = NR
        # split() returns the number of fields
        lenRowFields = split($0, rowFields, /[ \t]+/)
        
        # Store the fields in allRows[ rowNum, c-1 ]
        for (c=1; c<=lenRowFields; c++) {
            allRows[rowNum, c-1] = rowFields[c]
        }
        # Keep track of how many columns in this row
        numCols[rowNum] = lenRowFields
    }

    END {
        # We have 3 lines total in a standard FSL bvecs file
        for (r=1; r<=3; r++) {
            out = ""
            for (i=1; i<=n; i++) {
                colIndex = volList[i]
                # colIndex is 0-based; we stored columns also in 0-based indexing
                if (out == "") {
                    out = allRows[r, colIndex]
                } else {
                    out = out " " allRows[r, colIndex]
                }
            }
            print out
        }
    }
    ' "${infile_bvecs}" > "${outfile_bvecs}"


    ## Copy brain mask
    filename_brainmask="${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_mask
    infile_brainmask="${qsirecon_dir}"/"${filename_brainmask}".nii.gz
    outfile_brainmask="${splitshells_dir}"/"${filename_brainmask}".nii.gz
    cp "${infile_brainmask}" "${outfile_brainmask}"

    done




    ######################
    #### DTIFIT ####

    ## Run on multishell data

    ## define inputs ##

    local data="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi.nii.gz

    local bvals="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi.bval

    local bvecs="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi.bvec

    local mask="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_mask.nii.gz

    ## define outputs ##

    local dtifit_dir="${OUTDIR}"/dtifit/"${PARTICIPANT_LABEL}"/ses-V1/multishell
    mkdir -p ${dtifit_dir}

    ## run dtifit ##
    dtifit -k "${data}" -o ${dtifit_dir}/"${PARTICIPANT_LABEL}"_ses-V1_dtifit -m "${mask}" -r "${bvecs}" -b "${bvals}" --wls --sse --save_tensor



    ## Loop through bvals (1000, 2000, 3000)

    for bval in 1000 2000 3000 ; do

    ## define inputs ##

    local splitshells_dir="${OUTDIR}"/split_shells/"${PARTICIPANT_LABEL}"/ses-V1

    local data="${splitshells_dir}"/b"${bval}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi_b"${bval}".nii.gz

    local bvals="${splitshells_dir}"/b"${bval}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi_b"${bval}".bval

    local bvecs="${splitshells_dir}"/b"${bval}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_dwi_b"${bval}".bvec

    local mask="${splitshells_dir}"/"${PARTICIPANT_LABEL}"_ses-V1_space-T1w_desc-preproc_fslstd_mask.nii.gz

    ## define outputs ##

    local dtifit_dir="${OUTDIR}"/dtifit/"${PARTICIPANT_LABEL}"/ses-V1/b${bval}
    mkdir -p ${dtifit_dir}

    ## run dtifit ##
    dtifit -k "${data}" -o ${dtifit_dir}/"${PARTICIPANT_LABEL}"_ses-V1_dtifit_b"${bval}" -m "${mask}" -r "${bvecs}" -b "${bvals}" --wls --sse --save_tensor

    done

}

export -f main

main "$@"