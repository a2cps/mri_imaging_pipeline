#!/bin/bash

set -x
date
python make_dataset.py "${OUTDIR}" --inroot "${INROOT}"
