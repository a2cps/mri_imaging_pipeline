#!/bin/bash

set -eu
ml python3
#topdir=$(dirname "$0"| xargs readlink -f | xargs dirname)
topdir=/corral-secure/projects/A2CPS/
indir="$topdir/submissions"
#outdir="$topdir/data"
submitted="/corral-secure/projects/A2CPS/system/cronjob/submitted.txt"

heudiconv_actorid=heudiconv_router.prod
notifications_id=WPYELPWZy48aw
tapis auth tokens refresh

# refresh tokens
# tapis auth tokens refresh

function announce_error() {
	echo TODO: possibly announce that this script failed
}

# TODO: figure out how to do on EXIT with non 0 only
trap announce_error SIGINT SIGHUP SIGABRT 

function skip_file() {
	msg="$1"
	echo "TODO: tapis actors submit announce failed $msg"
}



touch "$submitted"
/bin/ls "$indir"/*/*/*.zip | while read f; do
	if grep -q "^$f\$" "$submitted"; then
		echo "$f was submitted, skipping"
		continue
	fi
	#cd "$(dirname $f)";
	#if ! md5sum -c "$f"; then
	if test 'find "$F" -mmin +10'
	then
		#zipfile="${f%.MD5SUM}"
		zipfile=${f}
		filename=$(basename "$zipfile" | sed -e 's,.zip,,g')
		#subj=${filename%_*}
		#ses=${filename#*_}
		#site="$(dirname $zipfile| xargs basename)"
		#site_path=$(dirname $(dirname "$zipfile"))
		#site="$(basename $site_path)"
		#outdir="$site_path/bids/$subj"
		# requires tapis from tapis-cli (pypi)	
		#echo tapis actors submit -m "{\"site\": \"$site\", \"subject\": \"$subj\", \"session\": \"$ses\", \"zipfile\": \"$zipfile\", \"outdir\": \"$outdir\"}" "$heudiconv_actorid"
		echo tapis actors submit -m "{\"zipfile\": \"$zipfile\"}" "$heudiconv_actorid"
		tapis actors submit -m "{\"zipfile\": \"$zipfile\"}" $heudiconv_actorid
		echo "$f" >> "$submitted"
		abaco submit -m "{\"text\": \"detected and submitted for processing: \"$zipfile\"}" $notifications_id
		
		continue
	else 
		skip_file "modified within 10 minutes"
		fi

done
