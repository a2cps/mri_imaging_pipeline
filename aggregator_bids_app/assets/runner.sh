#!/bin/bash

set -x
OUTDIR='/corral-secure/projects/A2CPS/products/mris/all_sites/bids'
INROOT="/corral-secure/projects/A2CPS/products/mris"

date
python3 make_dataset.py "${OUTDIR}" --inroot "${INROOT}"
