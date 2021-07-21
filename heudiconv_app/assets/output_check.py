import os
import re
import glob
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

os.listdir('/corral-secure/projects/A2CPS/system/jobs/urrutia/frontera_secure/heudiconv/exam9042/')

#/corral-secure/projects/A2CPS/products/development/mris/UI_uic/UI_travhuman/sub-UItravhuman/ses-phantom/sub-UItravhuman_ses-phantom_scans.tsv
#scans_file = glob.glob('/corral-secure/projects/A2CPS/system/jobs/urrutia/frontera_secure/heudiconv/exam9042/sub-*/*/*.tsv')[0]
#scans_file = glob.glob(bids_dir + '/sub-*/*/*.tsv')[0]
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
        "anat": anat, 
        "dwi": dwi,
        "cuff1": cuff1,
        "cuff2": cuff2,
        "rest1": rest1,
        "rest2": rest2
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
    #return(scans_actual)
    return search_scans

    #subject ID, visit, t1-cuff2 (indicated/actual)
    # subject ID, visit, site, event, t1-cuff2

    # T1
    # anat/sub-10011_ses-V1_T1w.nii.gz

    # DWI
    # dwi/sub-10011_ses-V1_dwi.nii.gz

    # Resting state
    # func/sub-10011_ses-V1_task-rest_run-01_bold.nii.gz

    # MRI individualized pressure
    # func/sub-10011_ses-V1_task-cuff_run-01_bold.nii.gz

    # MRI standard pressure
    # func/sub-10011_ses-V1_task-cuff_run-02_bold.nii.gz

    # 2nd Resting State
    # func/sub-10011_ses-V1_task-rest_run-02_bold.nii.gz

    # {
    # "record":"90005",
    # "event_ID":"171",
    # "T1":"0", 
    # "DWI":"0",
    # "1st_resting_state":"1",
    # "fMRI_individualized_pressure":"1",
    # "fMRI_standard_pressure":"1",
    # "2nd_resting_state":"1",
    # "dicom_uploaded":"1",
    # "upload_timestamp":"2021-04-02 12:32"
    # }
def parse_message(message):
    # subject_id = message['record']
    # visit = message['event_ID']
    # anat = message['T1']
    # dwi = message['DWI']
    # cuff1 = message['fMRI_individualized_pressure']
    # cuff2 = message['fMRI_standard_pressure']
    # rest1 =message['1st_resting_state']
    # rest2 = message['2nd_resting_state']
    # bids = message['bids']
    submitted_scans = {
        "subject_id": message['record'],
        "visit": message['event_ID'],
        "anat": message['T1'],
        "dwi": message['DWI'],
        "cuff1": message['fMRI_individualized_pressure'],
        "cuff2": message['fMRI_standard_pressure'],
        "rest1":message['1st_resting_state'],
        "rest2": message['2nd_resting_state'],
        "bids": message['bids']
        }

    processed_scans = find_processed(message['bids'])
    
scan_report = {
    "subject_id": message['record'],
    "visit": message['event_ID'],
    "T1 Indicated": message['T1'],
    "T1 Received": processed_scans['anat'],
    "DWI Indicated": message['DWI'],
    "DWI Received": processed_scans['dwi'],
    "fMRI Individualized Pressue Indicated": message['fMRI_individualized_pressure'],
    "fMRI Individualized Pressue Received": processed_scans['cuff1'],
    "fMRI Standard Pressure": message['fMRI_standard_pressure'],
    "fMRI Standard Pressure": processed_scans['cuff2'],
    "1st Resting State Indicated":message['1st_resting_state'],
    "1st Resting State Received": processed_scans['rest1'],
    "2nd Resting State Indicated":message['2nd_resting_state'],
    "2nd Resting State Indicated":processed_scans['rest2'],
}

df = pd.DataFrame(scan_report.items()).T
new_header = df.iloc[0] #grab the first row for the header
df = df[1:] #take the data less the header row
df.columns = new_header #set the header row as the df header

#df.style.apply(color_differences, axis=None)
df2 = df.style.apply(color_differences, axis=None)
df2.to_excel("styled.xlsx", engine="openpyxl", index = False)