#!/bin/bash

set -x
date
python3 make_dataset.py "${OUTDIR}" --inroot "${INROOT}"
