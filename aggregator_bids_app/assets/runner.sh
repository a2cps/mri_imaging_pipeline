#!/bin/bash

set -x
OUTDIR='/corral-secure/projects/A2CPS/products/mris/all_sites/bids'
INROOT="/corral-secure/projects/A2CPS/products/mris"

date
source /corral-secure/projects/A2CPS/system/cronjob/virtual_bids/venv/bin/activate
cd /corral-secure/projects/A2CPS/system/cronjob/virtual_bids/
export 
LD_LIBRARY_PATH=/opt/apps/cuda/10.0/lib64:/opt/apps/hwloc/1.11.12/lib:/opt/apps/pmix/3.1.4/lib:/opt/apps/intel19/python3/3.7.0/lib:/opt/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/libfabric/lib:/opt/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/lib/release:/opt/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/lib:/opt/intel/debugger_2020/libipt/intel64/lib:/opt/intel/compilers_and_libraries_2020.1.217/linux/daal/lib/intel64_lin:/opt/intel/compilers_and_libraries_2020.1.217/linux/tbb/lib/intel64_lin/gcc4.8:/opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin:/opt/intel/compilers_and_libraries_2020.1.217/linux/ipp/lib/intel64:/opt/intel/compilers_and_libraries_2020.1.217/linux/compiler/lib/intel64_lin:/opt/apps/gcc/8.3.0/lib64:/opt/apps/gcc/8.3.0/lib
#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/apps/intel19/python3/3.9.2/lib/
/corral-secure/projects/A2CPS/system/cronjob/virtual_bids/venv/bin/python /corral-secure/projects/A2CPS/system/cronjob/virtual_bids/make_dataset.py "${OUTDIR}" --inroot "${INROOT}"
