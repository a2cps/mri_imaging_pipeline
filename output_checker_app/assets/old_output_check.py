import os
import re
import glob
import json
import sys
import pandas as pd
#'0.24.2'
import numpy as np


def color_differences(x):
    df1 = pd.DataFrame('background-color: ', index=x.index, columns=x.columns)
    df1 = select_columns(x,df1,"T1 Received","T1 Indicated")
    df1 = select_columns(x,df1,"DWI Received","DWI Indicated")
    df1 = select_columns(x,df1,"fMRI Individualized Pressure Received","fMRI Individualized Pressure Indicated")
    df1 = select_columns(x,df1,"fMRI Standard Pressure Received","fMRI Standard Pressure Indicated")
    df1 = select_columns(x,df1,"1st Resting State Received","1st Resting State Indicated")
    df1 = select_columns(x,df1,"2nd Resting State Received","2nd Resting State Indicated")
    return df1

def select_columns(x, df1,column1, column2):
    m1 = int(x[column1].iloc[0]) != int(x[column2].iloc[0])
    #print(x[column1].iloc[0], x[column2].iloc[0])
    #print(m1)
    df1[column1] = np.where(m1, 'background-color: {}'.format('red'), df1[column1])
    df1[column2] = np.where(m1, 'background-color: {}'.format('red'), df1[column2])
    return df1

def find_processed(bids_dir):
    scans_file = glob.glob(os.path.normpath(bids_dir) + '/sub-*/*/*.tsv')[0]
    scans_df = pd.read_csv(scans_file, sep='\t')
    scan_list = scans_df['filename'].tolist()
    # Create a set of regexs to match filenames to scan names
    anat = re.compile('anat/[\w\W]+_T1w.nii.gz')
    dwi = re.compile('dwi/[\w\W]+_dwi.nii.gz')
    cuff1 = re.compile('func/[\w\W]+cuff_run-01_bold.nii.gz')
    cuff2 = re.compile('func/[\w]+cuff_run-02_bold.nii.gz')
    rest1 = re.compile('func/[\w]+run-01_bold.nii.gz')
    rest2 = re.compile('func/[\w]+run-02_bold.nii.gz')
    # Create a dictonary of scan names and regex lookups

    search_scans = {
        "T1 Received": anat,
        "DWI Received": dwi,
        "fMRI Individualized Pressure Received": cuff1,
        "fMRI Standard Pressure Received": cuff2,
        "1st Resting State Received": rest1,
        "2nd Resting State Received": rest2,
    }
    for scan_name,scan_file in search_scans.items():
        # If the scan is in our file list set to 1
        if any(scan_file.match(ascan) for ascan in scan_list):
            search_scans[scan_name] = 1
        # If the scan is missing set to 0
        else:
            search_scans[scan_name] = 0
    # Convert our dictionary of scan presence/absence to a dataframe
    scans_actual = pd.DataFrame(search_scans.items())
    return search_scans



def main():
    scans_indicated = json.loads(sys.argv[1])
    bids = sys.argv[2]
    report_csv = sys.argv[3]
    processed_scans = find_processed(bids)
    scan_report = {**scans_indicated, **processed_scans}
    df = pd.DataFrame(scan_report.items()).T
    new_header = df.iloc[0] #grab the first row for the header
    df = df[1:] #take the data less the header row
    df.columns = new_header #set the header row as the df header

    #df.style.apply(color_differences, axis=None)
    df = df.style.apply(color_differences(df), axis=None)
    df.to_excel(report_csv, engine="openpyxl", index = False)
    return


if __name__ == '__main__':
    main()