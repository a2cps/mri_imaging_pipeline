import os
import re
import glob
import json
import sys
import pandas as pd
from pathlib import Path
#'0.24.2'
import numpy as np
import requests
import xlsxwriter

FAILURE_LOG_DST = Path(os.environ.get("FAILURE_LOG_DST", "/corral-secure/projects/A2CPS/products/development/mris/logs"))

APP_STEPS = [
                "bids", 
                "fslanat",
                "fmriprep_anat", 
                "fmriprep_rest", 
                "fmriprep_cuff",
                "mriqc_anat", 
                "mriqc_rest", 
                "mriqc_cuff", 
                "qsiprep", 
                "cat12",
                "brainager",
                "fcn",
                "signatures"
            ]

# function to filter reponse object for highest record_id+visit repeat instance
def filter_highest_value(data, identification_keys, key_to_compare):
    result = []

    # Create a dictionary to store the highest values for each combination of identification keys
    highest_values = {}

    for item in data:
        # Create a tuple for the combination of identification keys
        identification_values = tuple(item[key] for key in identification_keys)

        # Check if the combination of identification keys already in highest_values
        if identification_values in highest_values:
            # Compare 'b' values and update if higher
            if item[key_to_compare] > highest_values[identification_values][key_to_compare]:
                highest_values[identification_values] = item
        else:
            # If combination not in highest_values, add the item
            highest_values[identification_values] = item

    # Convert the dictionary of highest values back to a list
    result.extend(highest_values.values())

    return result

def redcap_query():
    #read secrets
    with open('secrets.json') as jsonfile:
        secrets = json.load(jsonfile)

    data = {
        'token': secrets['RCAP_TOKEN_85'],
        'content': 'report',
        'format': 'json',
        'report_id': '85',
        'csvDelimiter': '',
        'rawOrLabel': 'raw',
        'rawOrLabelHeaders': 'raw',
        'exportCheckboxLabel': 'false',
        'returnFormat': 'json'
    }
    mcc2_imaging = requests.post('https://redcap.tacc.utexas.edu/api/',data=data)
    print('HTTP Status: ' + str(mcc2_imaging.status_code))
    #print(mcc2_imaging.json())


    #!/usr/bin/env python
    data = {
        'token': secrets['RCAP_TOKEN_86'],
        'content': 'report',
        'format': 'json',
        'report_id': '86',
        'csvDelimiter': '',
        'rawOrLabel': 'raw',
        'rawOrLabelHeaders': 'raw',
        'exportCheckboxLabel': 'false',
        'returnFormat': 'json'
    }
    mcc1_imaging = requests.post('https://redcap.tacc.utexas.edu/api/',data=data)
    print('HTTP Status: ' + str(mcc1_imaging.status_code))
    #print(mcc1_imaging.json())


    data = {
        'token': secrets['RCAP_TOKEN_454'],
        'content': 'report',
        'format': 'json',
        'report_id': '454',
        'csvDelimiter': '',
        'rawOrLabel': 'raw',
        'rawOrLabelHeaders': 'raw',
        'exportCheckboxLabel': 'false',
        'returnFormat': 'json'
    }
    mcc2_tka = requests.post('https://redcap.tacc.utexas.edu/api/',data=data)
    print('HTTP Status: ' + str(mcc2_tka.status_code))

    data = {
        'token': secrets['RCAP_TOKEN_455'],
        'content': 'report',
        'format': 'json',
        'report_id': '455',
        'csvDelimiter': '',
        'rawOrLabel': 'raw',
        'rawOrLabelHeaders': 'raw',
        'exportCheckboxLabel': 'false',
        'returnFormat': 'json'
    }
    mcc1_thoracic = requests.post('https://redcap.tacc.utexas.edu/api/',data=data)
    print('HTTP Status: ' + str(mcc1_thoracic.status_code))

    relevant_keys = [
    'record_id',
    'redcap_repeat_instance',
    'fmripatientname',
    'fmricufft1yn',
    'fmricuffdwiyn',
    'fmricuffrest1yn',
    'fmricuffipyn',
    'fmricuffcpyn', #MCC1
    'fmricuffspyn', #MCC2
    'fmricuffrest2yn',
    'fmricuffdicuploaded',
    #'fmricuffnotes',
    'imaging_mcc1_v09_complete', #MCC1
    'imaging_mcc2_v01_complete', #MCC2
    'fmricuffcompletescl',
    'fmricufft1techrating',
    'fmricufft1techrating2',
    'fmricuffcalfpressure', #MCC1
    'cuffpfmripressure', #MCC2
    'fmricuffcalfpressurerecal',
    'fmricuffrestpainss',
    'fmricuffrestpainovrall',
    'fmricuffcurrpainaftfirstscanss',
    'fmricuffcurrpainaftfirstscanovrall',
    'fmricuffcurrpainaftfirstscancp', #MCC1
    'fmricuffcurrpainaftfirstscancuff', #MCC2
    'fmricuffpainbegin',
    'fmricuffpainmid',
    'fmricuffpainend',
    'fmricuffpaincpbegin',
    'fmricuffpaincpmid',
    'fmricuffpaincpend',
    'fmricuffpainrestscanbegin',
    'fmricuffpainrestscanmid',
    'fmricuffpainrestscanend',
    'fmricuffpainaftlastscanss',
    'fmricuffpainaftlastscanany',
    'sp_surg_date',
    'fmricuffcontrayn', #MCC1
    'cuffpfmricontraindyn', #MCC2
    'fmri_face_mask',
    'fmri_magnet_name'
    ]
    all_mcc1 = mcc1_imaging.json() + mcc2_tka.json()
    all_mcc2 = mcc2_imaging.json() + mcc1_thoracic.json()
    # get surgery dates
    date_dict = {item['record_id']:item['sp_surg_date'] 
                for item in all_mcc1 
                if item['redcap_event_name'] == 'informed_consent_arm_1'}
    date_dict.update({item['record_id']:item['sp_surg_date'] 
                      for item in all_mcc2
                      if item['redcap_event_name'] == 'informed_consent_arm_1'})
    # date_dict.update({item['record_id']:item['sp_surg_date'] 
    #                   for item in mcc1_thoracic.json() 
    #                   if item['redcap_event_name'] == 'informed_consent_arm_1'})
    # date_dict.update({item['record_id']:item['sp_surg_date'] 
    #                   for item in mcc2_tka.json() 
    #                   if item['redcap_event_name'] == 'informed_consent_arm_1'})

    # remove subjects that explicitly have no uploaded scans
    mcc1_uploaded_list = [item for item in all_mcc1 if item['imaging_mcc1_v09_complete'] == '2']
    mcc1_uploaded_list = [item for item in mcc1_uploaded_list if item['fmricuffcompletescl'] != '0']
    mcc2_uploaded_list = [item for item in all_mcc2 if item['imaging_mcc2_v01_complete'] == '2'] 
    mcc2_uploaded_list = [item for item in mcc2_uploaded_list if item['fmricuffcompletescl'] != '0']

    # filter lists for highest repeat instance
    mcc1_uploaded_list = filter_highest_value(mcc1_uploaded_list, ['record_id', 'redcap_event_name'], 'redcap_repeat_instance')
    mcc2_uploaded_list = filter_highest_value(mcc2_uploaded_list, ['record_id', 'redcap_event_name'], 'redcap_repeat_instance')
    
    #foodict = {k: v for k, v in mydict.items() if k in relevant_keys}
    for index,item in enumerate(mcc1_uploaded_list):
        # resetting all uploads to 1 if the "complete" box is checked
        update_scans = ['fmricufft1yn',
                      'fmricuffdwiyn',
                      'fmricuffrest1yn',
                      'fmricuffipyn',
                      'fmricuffcpyn',
                      'fmricuffspyn',
                      'fmricuffrest2yn']
        updated_item = {k: v for k, v in item.items() if k in relevant_keys}
        updated_item.update({k:'1' for k,v in updated_item.items() 
                            if updated_item['fmricuffcompletescl'] == '1'
                            and k.endswith('yn')
                            and k in update_scans})
        # If it comes from mcc1 and is V1, pull value from fmricuffcalfpressure on the QST form
        # if it comes from mcc1 and is V3, pull value from fmricuffcalfpressure on the imaging form
        # if it is from mcc2 and V1 pull value from cuffpfmripressure on the QST form
        # if it is from mcc2 and V3 pull value from cuffpfmripressure on the imaging form 
        # add correct contraindicated
        try: 
            contra = [i['fmricuffcontrayn'] for i in all_mcc1 if i['record_id'] == item['record_id'] and i['redcap_repeat_instrument'] == 'qst_mcc1_v03'][-1]
        except Exception as e:
            contra = ''
        updated_item['fmricuffcontrayn'] = contra

        if item['redcap_event_name'] == 'baseline_visit_arm_1':
            try: 
                pressure = [i['fmricuffcalfpressure'] for i in all_mcc1 if i['record_id'] == item['record_id'] and i['redcap_repeat_instrument'] == 'qst_mcc1_v03'][-1]
            except Exception as e:
                pressure = ''
            updated_item['fmricuffcalfpressure'] = pressure

        mcc1_uploaded_list[index] = updated_item

    for index,item in enumerate(mcc2_uploaded_list):
        updated_item = {k: v for k, v in item.items() if k in relevant_keys}
        updated_item.update({k:'1' for k,v in updated_item.items() 
                            if updated_item['fmricuffcompletescl'] == '1'
                            and k.endswith('yn')
                            and k in update_scans})

        try: 
            contra = [i['cuffpfmricontraindyn'] for i in all_mcc2 if i['record_id'] == item['record_id'] and i['redcap_repeat_instrument'] == 'qst_mcc1_v03'][-1]
        except Exception as e:
            contra = ''
        updated_item['cuffpfmricontraindyn'] = contra

        if item['redcap_event_name'] == 'baseline_visit_arm_1':
            try: 
                pressure = [i['cuffpfmripressure'] for i in all_mcc2 if i['record_id'] == item['record_id'] and i['redcap_repeat_instrument'] == 'qst_mcc1_v03'][-1]
            except Exception as e:
                pressure = ''
            updated_item['cuffpfmripressure'] = pressure

        mcc2_uploaded_list[index] = updated_item

    uploaded = mcc1_uploaded_list +  mcc2_uploaded_list
    for index,item in enumerate(uploaded):
        #print(item)
        #print(item['fmripatientname'])
        try:
            std_name = item['fmripatientname']
            std_name = std_name.upper()
            #print(std_name)
            patient_id = re.search('(NS|WS|UC|UM|UI|SH|RU)\d{5}[vV](1|3)',std_name)
            #print(patient_id)
            (site_id, subject_id, v, session_number, space) = re.split('(\d+)',patient_id.group(0))
            session_id = v + session_number
            updated_item = item
            updated_item.update({
            "site_id": site_id,
            "subject_id": subject_id,
            "visit": session_id})
            uploaded[index] = updated_item
        except Exception as e:
            print(std_name)
            print(e)
    return uploaded, date_dict

def find_outputs(bids_path: str):
    dicom_path = bids_path.replace('bids','dicoms')
    bids_validation_path = bids_path.replace('bids','bids_validation')
    fmriprep_path = bids_path.replace('bids','fmriprep')
    mriqc_path = bids_path.replace('bids','mriqc')
    qsiprep_path = bids_path.replace('bids','qsiprep')
    cat12_path = bids_path.replace('bids','cat12')
    fslanat_path = bids_path.replace('bids','fslanat')
    fcn_path = bids_path.replace('bids','fcn')
    signatures_path = bids_path.replace('bids','signatures')
    brainager_path = bids_path.replace('bids','brainager')
    print(bids_path)
    # for path in [bids_path, dicom_path, bids_validation_path, fmriprep_path, mriqc_path]
    # outputs = {}
    # for x in [bids_path, dicom_path, bids_validation_path, fmriprep_path, mriqc_path]:
    #     #d["string{0}".format(x)] = "Hello"
    #     d["{0}".format(x)] = "Hello"
    #     outfile = glob.glob("".format(x)+'/*.out')[0]

    try: 
        bids_present = glob.glob(bids_path+'/*.out')[0]
        bids_present = 1
        bids = glob.glob(bids_path)[0]
    except Exception as e:
        print("no bids", bids_path)
        bids = 0
        bids_present = 0

    try:
        scans_file = glob.glob(bids_path+'/sub-*/ses-*/*.tsv')[0]
        #check t1 acquisition time and round to the nearest Friday
        #acq_time = pd.to_datetime(pd.read_csv(scans_file, sep='\t')['acq_time'][0]).round('7d')
        acq_day = pd.to_datetime(pd.read_csv(scans_file, sep='\t')['acq_time'][0])
        acq_time = acq_day - acq_day.weekday() * np.timedelta64(1, 'D')
        acq_time = acq_time.strftime('%Y-%m-%d')
    except Exception as e:
        acq_time = 'na'
    
    try: 
        duplicates = glob.glob(bids_path+'/sub-*/ses-*/*/*dup*')[0]
        duplicates = 1
    except Exception as e:
        duplicates = 0

    try: 
        dicom = glob.glob(dicom_path+'.zip')[0]
        dicom = 1
    except Exception as e:
        print("no dicom", dicom_path)
        dicom = 0
    try: 
        bids_validation = glob.glob(bids_validation_path+'/*.out')[0]
        bids_validation = 1
    except Exception as e:
        print("no bids_validation", bids_validation_path)
        bids_validation = 0
    try: 
        fmriprep_anat = glob.glob(fmriprep_path+'/anat/*.out')[0]
        fmriprep_anat = 1
    except Exception as e:
        print("no fmriprep anat", fmriprep_path)
        fmriprep_anat = 0
    try: 
        fmriprep_cuff = glob.glob(fmriprep_path+'/cuff/*.out')[0]
        fmriprep_cuff = 1
    except Exception as e:
        print("no fmriprep cuff", fmriprep_path)
        fmriprep_cuff = 0
    try: 
        fmriprep_rest = glob.glob(fmriprep_path+'/rest/*.out')[0]
        fmriprep_rest = 1
    except Exception as e:
        print("no fmriprep rest", fmriprep_path)
        fmriprep_rest = 0
    try: 
        mriqc_anat = glob.glob(mriqc_path+'/*nat/*')[0]
        mriqc_anat = 1
    except Exception as e:
        print("no mriqc anat", mriqc_path)
        mriqc_anat = 0
        
    try: 
        mriqc_cuff = glob.glob(mriqc_path+'/*uff/*')[0]
        mriqc_cuff = 1
    except Exception as e:
        print("no mriqc cuff", mriqc_path)
        mriqc_cuff = 0

    try: 
        mriqc_rest = glob.glob(mriqc_path+'/*est/*')[0]
        mriqc_rest = 1
    except Exception as e:
        print("no mriqc rest", mriqc_path)
        mriqc_rest = 0

    try:
        qsiprep = glob.glob(qsiprep_path+'/qsiprep/*.html')[0]
        qsiprep = 1
    except Exception as e:
        print("no qsiprep", qsiprep_path)
        qsiprep = 0

    try:
        cat12 = glob.glob(cat12_path+'/*.out')[0]
        cat12 = 1
    except Exception as e:
        print("no cat12", cat12_path)
        cat12 = 0
    
    fslanat = 1 if len(glob.glob(f"{fslanat_path}/*.out")) else 0
    fcn = 1 if len(glob.glob(f"{fcn_path}/*.out")) else 0
    signatures = 1 if len(glob.glob(f"{signatures_path}/*.out")) else 0
    brainager = 1 if len(glob.glob(f"{brainager_path}/*.out")) else 0
        
    return dicom, bids, bids_present, bids_validation, fmriprep_anat, fmriprep_cuff, fmriprep_rest, mriqc_anat, mriqc_cuff, mriqc_rest, qsiprep, cat12, acq_time, fslanat, fcn, signatures, brainager


def find_heudiconv_outputs(bids_dir):
    try:
        scans_file = glob.glob(os.path.normpath(bids_dir) + '/sub-*/*/*.tsv')[0]
    except Exception as e:
        print("no scans file for ", bids_dir)
        return 0
    scans_df = pd.read_csv(scans_file, sep='\t')
    scan_list = scans_df['filename'].tolist()
    # Create a set of regexs to match filenames to scan names
    anat = re.compile('anat/[\w\W]+_T1w.nii.gz')
    dwi = re.compile('dwi/[\w\W]+_dwi.nii.gz')
    cuff1 = re.compile('func/[\w\W]+cuff_run-01_bold.nii.gz')
    cuff2 = re.compile('func/[\w\W]+cuff_run-02_bold.nii.gz')
    rest1 = re.compile('func/[\w\W]+rest_run-01_bold.nii.gz')
    rest2 = re.compile('func/[\w\W]+rest_run-02_bold.nii.gz')
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

def compare_colums(workbook, worksheet, a, b):
    format1 = workbook.add_format({'bg_color': '#FFC7CE',
                                'font_color': '#9C0006'})
    worksheet.conditional_format('${}$2:${}$175'.format(a,b), {'type':     'formula',
                                    'criteria': '=${}2<>${}2'.format(a,b),
                                    'format':   format1})
    return worksheet

def write_excel(df):
    df[["T1 Indicated",
    "DWI Indicated",
    "fMRI Individualized Pressure Indicated",
    "fMRI Standard Pressure Indicated",
    "1st Resting State Indicated",
    "2nd Resting State Indicated"
     ]] = df[["T1 Indicated",
            "DWI Indicated",
            "fMRI Individualized Pressure Indicated",
            "fMRI Standard Pressure Indicated",
            "1st Resting State Indicated",
            "2nd Resting State Indicated"
            ]].apply(pd.to_numeric)

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter('report.xlsx', engine='xlsxwriter')

    # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name='Sheet1', index=False)

    # Get the xlsxwriter objects from the dataframe writer object.
    workbook  = writer.book
    worksheet = writer.sheets['Sheet1']

    #workbook = xlsxwriter.Workbook('conditional_format.xlsx')
    cell_format = workbook.add_format({'num_format': '0'})
    worksheet.set_column('D:V', 10, cell_format)

    worksheet = compare_colums(workbook, worksheet, 'D', 'E')
    worksheet = compare_colums(workbook, worksheet, 'F', 'G')
    worksheet = compare_colums(workbook, worksheet, 'H', 'I')
    worksheet = compare_colums(workbook, worksheet, 'J', 'K')
    worksheet = compare_colums(workbook, worksheet, 'L', 'M')
    worksheet = compare_colums(workbook, worksheet, 'N', 'O')

    #workbook.close()
    writer.save()


def update_to_fail(d: dict[str, int | str], col: str) -> None:
    sublong = f"{d.get('site')}{d.get('subject_id')}{d.get('visit')}"
    # the check for in [0,1,etc] is to avoid overwritting 'na' values
    if len(list((FAILURE_LOG_DST / col / sublong).glob("*.out"))) and (d.get(col) in ["0", "1", 0, 1]):
        d[col] = '2'


def main():
    # scans_indicated = json.loads(sys.argv[1])
    # bids = sys.argv[2]
    # report_csv = sys.argv[3]
    # processed_scans = find_heudiconv_outputs(bids)
    # scan_report = {**scans_indicated, **processed_scans}
    # df = pd.DataFrame(scan_report.items()).T
    # new_header = df.iloc[0] #grab the first row for the header
    # df = df[1:] #take the data less the header row
    # df.columns = new_header #set the header row as the df header

    # writer = pd.ExcelWriter('pandas_conditional.xlsx', engine='xlsxwriter')
    # df1.to_excel(writer, sheet_name='Sheet1')
    # writer.save()
    (uploaded, date_dict) = redcap_query()
    list_of_dict = []

    #for index, row in recieved_csv.iterrows():
    for index, row in enumerate(uploaded):
        #print(row['site'], row['subject_id'])
        try:
            site_id = row['site_id']
            bids_path = "/corral-secure/projects/A2CPS/products/mris/*/bids/" + site_id + str(row['subject_id']) + row['visit']
            (dicom, bids, bids_present, bids_validation, fmriprep_anat, fmriprep_cuff, fmriprep_rest, mriqc_anat, mriqc_cuff, mriqc_rest, qsiprep, cat12, acq_time, fslanat, fcn, signatures, brainager) = find_outputs(bids_path)

            # patch for typo in redcap
            if "fmricuffcpyn" in row:
                cuff2 = row["fmricuffcpyn"]
            else:
                cuff2 = row["fmricuffspyn"]

            # patch for differeing naming conventions in RedCap
            if "fmricuffcalfpressure" in row:
                cuff1_pressure = row["fmricuffcalfpressure"]
            else:
                cuff1_pressure = row["cuffpfmripressure"]

            # replace t1 rating with updated rating, if it exists
            if row["fmricufft1techrating2"] == '':
                t1_rating = row["fmricufft1techrating"]
            else:
                t1_rating = row["fmricufft1techrating2"]

            # patch for differeing naming conventions in RedCap
            if "fmricuffcurrpainaftfirstscancp" in row:
                cuffcurrpainaftfirstscan = row["fmricuffcurrpainaftfirstscancp"]
            else:
                cuffcurrpainaftfirstscan = row["fmricuffcurrpainaftfirstscancuff"]
            
            # patch for differeing naming conventions in RedCap
            if "fmricuffcontrayn" in row:
                contraindicated = row["fmricuffcontrayn"]
            else:
                contraindicated = row["cuffpfmricontraindyn"]

            try:
                surg_date = pd.to_datetime(date_dict[row['record_id']])
                surg_day = surg_date - surg_date.weekday() * np.timedelta64(1, 'D')
                surg_day = surg_day.strftime('%Y-%m-%d')
            except Exception as e:
                print(e)
                surg_day = ''

            # add column for applied pressure
            if row["fmricuffipyn"] == '0':
                applied_pressure = 'na'
            elif row['fmricuffcalfpressurerecal'] != '':
                applied_pressure = row['fmricuffcalfpressurerecal']
            else:
                applied_pressure = cuff1_pressure

            if row.get('fmri_magnet_name') is None:
                row['fmri_magnet_name'] = 'na'
            if row.get('fmri_face_mask') is None:
                row['fmri_face_mask'] = 'na'


            scans_indicated = {
                        "site": site_id, 
                        "subject_id": row['subject_id'],
                        "visit": row['visit'],
                        "T1 Indicated": row['fmricufft1yn'],
                        "DWI Indicated": row["fmricuffdwiyn"],
                        "fMRI Individualized Pressure Indicated": row["fmricuffipyn"],
                        "fMRI Standard Pressure Indicated": cuff2,
                        "1st Resting State Indicated": row["fmricuffrest1yn"],
                        "2nd Resting State Indicated": row["fmricuffrest2yn"],
                        "fMRI T1 Tech Rating": t1_rating,
                        "Cuff1 QST Pressure": cuff1_pressure,
                        "Cuff1 Recalibrated Pressure": row['fmricuffcalfpressurerecal'],
                        "Cuff1 Applied Pressure": applied_pressure,
                        "Surgical site pain rest": row['fmricuffrestpainss'],
                        "Body pain rest": row['fmricuffrestpainovrall'],
                        "Surgical site pain after first scan": row['fmricuffcurrpainaftfirstscanss'],
                        "Body pain after first scan": row['fmricuffcurrpainaftfirstscanovrall'],
                        "Cuff pain after first scan": cuffcurrpainaftfirstscan,
                        "Cuff pain cuff1 beginning": row['fmricuffpainbegin'],
                        "Cuff pain cuff1 middle": row['fmricuffpainmid'],
                        "Cuff pain cuff1 end": row['fmricuffpainend'],
                        "Cuff pain cuff2 beginning": row['fmricuffpaincpbegin'],
                        "Cuff pain cuff2 middle": row['fmricuffpaincpmid'],
                        "Cuff pain cuff2 end": row['fmricuffpaincpend'],
                        "Cuff pain rest beginning": row['fmricuffpainrestscanbegin'],
                        "Cuff pain rest middle": row['fmricuffpainrestscanmid'],
                        "Cuff pain rest end": row['fmricuffpainrestscanend'],
                        "Surgical site pain after last scan": row['fmricuffpainaftlastscanss'],
                        "Body pain after last scan": row['fmricuffpainaftlastscanany'],
                        "Cuff contraindicated": contraindicated,
                        "Surgery Week": surg_day,
                        "Face Mask": row['fmri_face_mask'],
                        "Magnet Name": row['fmri_magnet_name'],
                        "Repeat instance": row['redcap_repeat_instance']
                        #"comments": row['fmricuffnotes']
                        }

            #scans_indicated.update({k:1 for k,v in scans_indicated.items() if v == 'Y'})
            #scans_indicated.update({k:0 for k,v in scans_indicated.items() if v == 'N'})
            #pprint.pprint(scans_indicated)
            if bids != 0:
                processed_scans = find_heudiconv_outputs(bids)
            else:
                processed_scans = {
                "T1 Received": 0,
                "DWI Received": 0,
                "fMRI Individualized Pressure Received": 0,
                "fMRI Standard Pressure Received": 0,
                "1st Resting State Received": 0,
                "2nd Resting State Received": 0,
            }
            # if processed_scans == 0:
            #     continue
            scan_report = {**scans_indicated, **processed_scans}
            scan_report['dicom'] = dicom
            scan_report['bids'] = bids_present
            scan_report['bids_validation'] = bids_present
            scan_report['fslanat'] = fslanat
            scan_report['fcn'] = fcn
            scan_report['signatures'] = signatures
            scan_report['fmriprep_anat'] = fmriprep_anat
            scan_report['fmriprep_cuff'] = fmriprep_cuff
            scan_report['fmriprep_rest'] = fmriprep_rest
            scan_report['mriqc_anat'] = mriqc_anat
            scan_report['mriqc_cuff'] = mriqc_cuff
            scan_report['mriqc_rest'] = mriqc_rest
            scan_report['qsiprep'] = qsiprep
            scan_report['cat12'] = cat12
            scan_report['brainager'] = brainager
            scan_report['acquisition_week'] = acq_time

            # remove preprocessing if scans not indicated
            if scan_report["T1 Indicated"] == "0":
                scan_report["mriqc_anat"] = "na"
                scan_report["mriqc_cuff"] = "na"
                scan_report["mriqc_rest"] = "na"
                scan_report["cat12"] = "na"
                scan_report["brainager"] = "na"
                scan_report["fslanat"] = "na"
                scan_report["fmriprep_anat"] = "na"
                scan_report["fmriprep_rest"] = "na"
                scan_report["fmriprep_cuff"] = "na"
                scan_report["qsiprep"] = "na"
                scan_report["fcn"] = "na"
                scan_report["signatures"] = "na"
            if scan_report['1st Resting State Indicated'] == '0' and scan_report['2nd Resting State Indicated'] == '0':
                scan_report['fmriprep_rest'] = 'na'
                scan_report['mriqc_rest'] = 'na'
            if scan_report['fMRI Individualized Pressure Indicated'] == '0' and scan_report['fMRI Standard Pressure Indicated'] == '0':
                scan_report['fmriprep_cuff'] = 'na'
                scan_report['mriqc_cuff'] = 'na'
            if scan_report["fmriprep_rest"] == "na" and scan_report["fmriprep_cuff"] == "na":
                scan_report['fcn'] = 'na'
                scan_report['signatures'] = 'na'
            if scan_report['DWI Indicated'] == '0':
                scan_report['qsiprep'] = 'na'

            for col in APP_STEPS:
                update_to_fail(scan_report, col)

            list_of_dict.append(scan_report)
        except Exception as e:
            print(e)
            print(row)
    with open('list.json', 'w') as fout:
        json.dump(list_of_dict, fout)
    df = pd.DataFrame(list_of_dict)
    #cols = df.columns.tolist()
    #cols = cols[1:] + cols[:-1]
    df = df[['site',
    'subject_id',
    'visit',
    'T1 Indicated', 'T1 Received',
    'DWI Indicated', 'DWI Received',
    'fMRI Individualized Pressure Indicated', 'fMRI Individualized Pressure Received',
    'fMRI Standard Pressure Indicated', 'fMRI Standard Pressure Received',
    '1st Resting State Indicated', '1st Resting State Received',
    '2nd Resting State Indicated',
    '2nd Resting State Received',
    'fMRI T1 Tech Rating',
    'Cuff1 QST Pressure',
    'Cuff1 Recalibrated Pressure',
    'Cuff1 Applied Pressure',
    'dicom',
    'bids',
    'bids_validation',
    'fslanat',
    'fmriprep_anat',
    'fmriprep_cuff',
    'fmriprep_rest',
    'mriqc_anat',
    'mriqc_cuff',
    'mriqc_rest',
    'qsiprep',
    'cat12',
    'brainager',
    'fcn',
    'signatures',
    'acquisition_week',
    "Surgical site pain rest",
    "Body pain rest",
    "Surgical site pain after first scan",
    "Body pain after first scan",
    "Cuff pain after first scan",
    "Cuff pain cuff1 beginning",
    "Cuff pain cuff1 middle",
    "Cuff pain cuff1 end",
    "Cuff pain cuff2 beginning",
    "Cuff pain cuff2 middle",
    "Cuff pain cuff2 end",
    "Cuff pain rest beginning",
    "Cuff pain rest middle",
    "Cuff pain rest end",
    "Surgical site pain after last scan",
    "Body pain after last scan",
    "Cuff contraindicated",
    "Surgery Week",
    "Face Mask",
    "Magnet Name",
    "Repeat instance"
    #'comments'
    ]]
    df.drop_duplicates(inplace=True)
    df.to_csv('report.csv', index = False)
    write_excel(df)

    return


if __name__ == '__main__':
    main() 




