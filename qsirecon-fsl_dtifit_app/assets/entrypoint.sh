#!/bin/bash

set -euo pipefail

# used to determine whether bvals are equivalent
declare -rxi THRESHOLD=100

main (){

    local QSIPREPDIR="${1}"
    local OUTDIR="${2}"
    local LICENSE="${3}"
    local PARTICIPANT_LABEL="sub-${4}"
    local SES_LABEL="ses-${5}"


        ## note: splitshellsdir should be: 
        ## /corral-secure/projects/A2CPS/shared/maj/qsirecon-fsl_dtifit_app/derivatives/split_shells

        ## note: DTIFITDIR should be: 
        ## /corral-secure/projects/A2CPS/shared/maj/qsirecon-fsl_dtifit_app/derivatives/dtifit
    
    local -r out_qsirecon="${OUTDIR}"/qsirecon

    ## RUN QSIRECON
    local work
    work=$(mktemp -d)
    qsirecon \
        --recon-spec reorient_fslstd \
        --fs-license-file "${LICENSE}" \
        -w "${work}" \
        "${QSIPREPDIR}" "${out_qsirecon}" participant 
    
    rm -r "${work}" 
    echo "qsiprep recon finished!"

    ######################
    #### Split Shells ####

    ## DEFINE ARGS

    ## inputs from qsirecon FSL
    local -r qsirecon_dir="${out_qsirecon}"/derivatives/qsirecon-FSL/"${PARTICIPANT_LABEL}"/"${SES_LABEL}"/dwi

    ## define base filenames
    local -r in_filename_dwi="${PARTICIPANT_LABEL}"_"${SES_LABEL}"_space-T1w_dwi

    local -r infile_dwi="${qsirecon_dir}"/"${in_filename_dwi}".nii.gz
    local -r infile_bvals="${qsirecon_dir}"/"${in_filename_dwi}".bval
    local -r infile_bvecs="${qsirecon_dir}"/"${in_filename_dwi}".bvec

    #########
    ## b=0 ##

    local -i bval=0

    local -r splitshells_dir="${OUTDIR}"/split_shells/"${PARTICIPANT_LABEL}"/"${SES_LABEL}"/dwi
    mkdir -p "${splitshells_dir}"

    local out_filename_dwi="${PARTICIPANT_LABEL}"_"${SES_LABEL}"_acq-b"${bval}"_space-T1w_dwi
    local outfile_b0_dwi="${splitshells_dir}"/"${out_filename_dwi}".nii.gz
    local outfile_b0_bvals="${splitshells_dir}"/"${out_filename_dwi}".bval
    local outfile_b0_bvecs="${splitshells_dir}"/"${out_filename_dwi}".bvec

    ## Subselect indices
    local indices_b0
    indices_b0=$(awk -v thresh="${THRESHOLD}" '
    {
    # $1 is the b-value on this line
    if ($1 < thresh) {
        # Print 0-based line index
        printf("%d ", NR-1)
    }
    }' "${infile_bvals}")

    echo "Indices for b < ${THRESHOLD}: ${indices_b0}"

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


    #############################################
    ## Loop through bvals with +/- THRESHOLD range
    local -i low
    local -i high
    local outfile_dwi
    local outfile_bvals
    local outfile_bvecs
    local indices
    local indices_combined
    for bval in 500 1000 2000 3000 ; do

        # Define the lower and upper bounds for this shell
        low=$((bval - THRESHOLD))
        high=$((bval + THRESHOLD))

        out_filename_dwi="${PARTICIPANT_LABEL}"_"${SES_LABEL}"_acq-b"${bval}"_space-T1w_dwi

        outfile_dwi="${splitshells_dir}"/"${out_filename_dwi}".nii.gz
        outfile_bvals="${splitshells_dir}"/"${out_filename_dwi}".bval
        outfile_bvecs="${splitshells_dir}"/"${out_filename_dwi}".bvec

        ## Subselect indices for the current range        
        indices=$(awk -v L="${low}" -v H="${high}" '
        {
            # $1 is the b-value on this line
            # if it falls within [L, H], we keep that volume
            if ($1 >= L && $1 <= H) {
            # Print 0-based line index
            printf("%d ", NR-1)
            }
        }
        ' "${infile_bvals}")

        echo "Indices for b ~ ${bval} (range ${low}-${high}): ${indices}"

        # Combine with b=0 volumes, stored in indices_b0
        indices_combined="$(echo "${indices_b0} ${indices}" | xargs)"
        echo "Indices for b=0 + b ~ ${bval}: ${indices_combined}"

        ## Extract from DWI data
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

            # Store the fields in allRows[rowNum, c-1]
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
                    colIndex = volList[i]  # 0-based index
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

    done

    ######################
    #### DTIFIT ####

    ## Run on multishell data

    ## define inputs ##

    # reoriented mask used for all dtifit
    local -r mask="${qsirecon_dir}"/"${PARTICIPANT_LABEL}"_"${SES_LABEL}"_space-T1w_mask.nii.gz

    ## define outputs ##
    local dtifit_dir="${OUTDIR}"/dtifit-multishell/"${PARTICIPANT_LABEL}"/"${SES_LABEL}"/dwi
    mkdir -p "${dtifit_dir}"

    ## run dtifit ##
    dtifit \
        -k "${infile_dwi}" \
        -o "${dtifit_dir}"/"${in_filename_dwi}" \
        -m "${mask}" \
        -r "${infile_bvecs}" \
        -b "${infile_bvals}" \
        --wls --sse --save_tensor

    ## Loop through bvals (1000, 2000, 3000)
    local filename_dwi
    for bval in 1000 2000 3000 ; do

        ## define inputs ##
        filename_dwi="${PARTICIPANT_LABEL}"_"${SES_LABEL}"_acq-b"${bval}"_space-T1w_dwi

        ## define outputs ##
        dtifit_dir="${OUTDIR}"/dtifit-b${bval}/"${PARTICIPANT_LABEL}"/"${SES_LABEL}"/dwi
        mkdir -p "${dtifit_dir}"

        ## run dtifit ##
        dtifit \
            -k "${splitshells_dir}"/"${filename_dwi}".nii.gz \
            -o "${dtifit_dir}"/"${filename_dwi}" \
            -m "${mask}" \
            -r "${splitshells_dir}"/"${filename_dwi}".bvec \
            -b "${splitshells_dir}"/"${filename_dwi}".bval \
            --wls --sse --save_tensor

    done

}
export -f main

main "$@"
