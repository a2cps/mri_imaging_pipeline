import os
import re
import glob
import json
import sys
import pandas as pd
#'0.24.2'
import numpy as np
import requests
import xlsxwriter

def redcap_query():
    data = {
        'token': '579B9A54777F12A0BE7F2E38C24F06C0',
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
        'token': '8DE47C01CF66D322EF50B6390ADEDDC1',
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

    relevant_keys = [
    'record_id',
    'fmripatientname',
    'fmricufft1yn',
    'fmricuffdwiyn',
    'fmricuffrest1yn',
    'fmricuffipyn',
    'fmricuffcpyn',
    'fmricuffspyn',
    'fmricuffrest2yn',
    'fmricuffdicuploaded',
    #'fmricuffnotes',
    'fmricuffcompletescl'
    ]

    mcc1_uploaded_list = [item for item in mcc1_imaging.json() if item['fmricuffdicuploaded'] == '1']
    mcc2_uploaded_list = [item for item in mcc2_imaging.json() if item['fmricuffdicuploaded'] == '1']

    #foodict = {k: v for k, v in mydict.items() if k in relevant_keys}
    for index,item in enumerate(mcc1_uploaded_list):
        updated_item = {k: v for k, v in item.items() if k in relevant_keys}
        # resetting all uploads to 1 if the "complete" box is checked
        updated_item.update({k:'1' for k,v in updated_item.items() 
                            if updated_item['fmricuffcompletescl'] == '1'
                            and k.endswith('yn')})
        mcc1_uploaded_list[index] = updated_item

    for index,item in enumerate(mcc2_uploaded_list):
        updated_item = {k: v for k, v in item.items() if k in relevant_keys}
        updated_item.update({k:'1' for k,v in updated_item.items() 
                            if updated_item['fmricuffcompletescl'] == '1'
                            and k.endswith('yn')})
        mcc2_uploaded_list[index] = updated_item

    uploaded = mcc1_uploaded_list +  mcc2_uploaded_list
    for index,item in enumerate(uploaded):
        #print(item)
        #print(item['fmripatientname'])
        try:
            std_name = item['fmripatientname']
            #print(std_name)
            patient_id = re.search('(NS|WS|UC|UM|UI)\d{5}[vV](1|3)',std_name)
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
    return uploaded

def find_outputs(bids_path):
    dicom_path = bids_path.replace('bids','dicoms')
    bids_validation_path = bids_path.replace('bids','bids_validation')
    fmriprep_path = bids_path.replace('bids','fmriprep')
    mriqc_path = bids_path.replace('bids','mriqc')
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
        duplicates = glob.glob(bids_path+'/sub-*/ses-*/*/*dup*')[0]
        duplicates = 1
    except Exception as e:
        duplicates = 0

    try: 
        dicom = glob.glob(dicom_path+'/*')[0]
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
        mriqc = glob.glob(mriqc_path+'/*.out')[0]
        mriqc = 1
    except Exception as e:
        print("no mriqc", mriqc_path)
        mriqc = 0
        
    return dicom, bids, bids_present, bids_validation, fmriprep_anat, fmriprep_cuff, fmriprep_rest, mriqc


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
    rest1 = re.compile('func/[\w\W]+run-01_bold.nii.gz')
    rest2 = re.compile('func/[\w\W]+run-02_bold.nii.gz')
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
    uploaded = redcap_query()
    list_of_dict = []

    #for index, row in recieved_csv.iterrows():
    for index, row in enumerate(uploaded):
        #print(row['site'], row['subject_id'])
        site_id = row['site_id']
        bids_path = "/corral-secure/projects/A2CPS/products/mris/*/bids/" + site_id + str(row['subject_id']) + row['visit']
        (dicom, bids, bids_present, bids_validation, fmriprep_anat, fmriprep_cuff, fmriprep_rest, mriqc) = find_outputs(bids_path)

        # patch for typo in redcap
        if "fmricuffcpyn" in row:
            cuff2 = row["fmricuffcpyn"]
        else:
            cuff2 = row["fmricuffspyn"]


        scans_indicated = {
                    "site": site_id, 
                    "subject_id": row['subject_id'],
                    "visit": row['visit'],
                    "T1 Indicated": row['fmricufft1yn'],
                    "DWI Indicated": row["fmricuffdwiyn"],
                    "fMRI Individualized Pressure Indicated": row["fmricuffipyn"],
                    "fMRI Standard Pressure Indicated": cuff2,
                    "1st Resting State Indicated": row["fmricuffrest1yn"],
                    "2nd Resting State Indicated": row["fmricuffrest2yn"]#,
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
        scan_report['bids_validation'] = bids_validation
        scan_report['fmriprep_anat'] = fmriprep_anat
        scan_report['fmriprep_cuff'] = fmriprep_cuff
        scan_report['fmriprep_rest'] = fmriprep_rest
        scan_report['mriqc'] = mriqc


        list_of_dict.append(scan_report)
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
    'dicom',
    'bids',
    'bids_validation',
    'fmriprep_anat',
    'fmriprep_cuff',
    'fmriprep_rest',
    'mriqc'#,
    #'comments'
    ]]
    df.to_csv('report.csv', index = False)
    write_excel(df)

    return


if __name__ == '__main__':
    main()