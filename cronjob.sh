#!/bin/bash

set -eu
python3=/opt/apps/intel18/python3/3.7.0/bin/python3
export LD_LIBRARY_PATH=/opt/apps/cuda/10.0/lib64:/opt/apps/hwloc/1.11.12/lib:/opt/apps/pmix/3.1.4/lib:/opt/apps/intel19/python3/3.7.0/lib:/opt/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/libfabric/lib:/opt/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/lib/release:/opt/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/lib:/opt/intel/debugger_2020/libipt/intel64/lib:/opt/intel/compilers_and_libraries_2020.1.217/linux/daal/lib/intel64_lin:/opt/intel/compilers_and_libraries_2020.1.217/linux/tbb/lib/intel64_lin/gcc4.8:/opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin:/opt/intel/compilers_and_libraries_2020.1.217/linux/ipp/lib/intel64:/opt/intel/compilers_and_libraries_2020.1.217/linux/compiler/lib/intel64_lin:/opt/apps/gcc/8.3.0/lib64:/opt/apps/gcc/8.3.0/lib

tapis=/home1/05369/urrutia/.local/bin/tapis
topdir=/corral-secure/projects/A2CPS
indir="$topdir/submissions"
#outdir="$topdir/data"
submitted="/corral-secure/projects/A2CPS/system/cronjob/submitted.txt"

dicom_actor=dicom_router.prod
notifications_id=imaging-slackbot.prod
#$tapis auth tokens refresh 1> /dev/null
$tapis actors list 1> /dev/null


function announce_error() {
	echo TODO: possibly announce that this script failed
}

# TODO: figure out how to do on EXIT with non 0 only
trap announce_error SIGINT SIGHUP SIGABRT 

function skip_file() {
	msg="$1"
	echo "TODO: tapis actors submit announce failed $msg"
}

# most received DICOMs follow this pattern
#zips=("$indir"/*/*.zip)
zips=()
for site in NS_northshore UC_uchicago UM_umichigan SH_spectrum_health_grand_rapids WS_wayne_state; do
  zips+=("${indir}"/${site}/*zip)
done
# but WS sends two sets of phantom dicoms:
#   $indir/Wayne_state/QA/DSV
#   $indir/Wayne_state/QA/BIRD
# we only want to process the DSV files. 
zips+=("$indir"/WS_wayne_state/QA/DSV/*zip)
zips+=("$indir"/a2dtn01/*)


touch "$submitted"
for uploaded_file in "${zips[@]}"; do
	if grep -q "^$uploaded_file\$" "$submitted"; then
		#echo "$uploaded_file was submitted, skipping"
		continue
	fi
        #check if file was modified in the last hour
        modfilter=$(find "$uploaded_file" -mmin +60)
        file_string=$(echo $modfilter | sed 's/\s.*$//')
        if [ "$file_string" = "$uploaded_file" ]; then
		# requires tapis from tapis-cli (pypi)	
		echo tapis actors submit -m "{\"uploaded_file\": \"$uploaded_file\"}" "$dicom_actor"
		$tapis actors submit -m "{\"uploaded_file\": \"$uploaded_file\"}" $dicom_actor
		echo "$uploaded_file" >> "$submitted"
		echo abaco submit -m "{\"text\": \"detected and submitted for processing: $uploaded_file\"}" $notifications_id
		$tapis actors submit -m "{\"text\": \"detected and submitted for processing: $uploaded_file\"}" $notifications_id
		continue
	else 
		skip_file "$uploaded_file modified within 1 hour"
	fi

done
