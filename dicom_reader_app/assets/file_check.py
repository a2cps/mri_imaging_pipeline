import os
#import zipfile
import zipfile38 as zipfile
from shutil import copyfile,copytree
import requests
import sys
import pydicom
import re

def post_notification(notification):
    endpoint = r"https://api.a2cps.org/actors/v2/slackbot.prod/messages?x-nonce=A2CPS_NPzA41LpZw6x5"
    content = requests.post(url = endpoint, json = {"text": notification})
    data = content.json()
    return data

def message_heudiconv(message):
    endpoint = r"https://api.a2cps.org/actors/v2/heudiconv_router.prod/messages?x-nonce=A2CPS_WJBXjrPyBJpM"
    content = requests.post(url = endpoint, json = message)
    data = content.json()
    return data

def test_zip(filename):
    try:
        zipfile.ZipFile(filename).testzip()
        return True
    except Exception as e:
        print("bad zip")
        #data = post_notification("bad zip file at path " + filename)
        #print(data)
        return False
    # except zipfile.BadZipfile:
    #     print('bad')
    # except OSError:
    #     print('os')
    # except zipfile.BadZipfile:
    #     print(lilzip)

def find_dicom(filename, isZip):
    # Find first zip dicom
    if isZip is True:
        site_zip = zipfile.ZipFile(filename)
        for listing in site_zip.filelist:
            if zipfile.Path.is_file(listing):
                break
        dicom_file = site_zip.extract(listing)
        return dicom_file
    # Find first unzipped dicom
    for root, dirs, files in os.walk(filename):
        if files != []:
            dicom_file = root + '/' + files[0]
            print(dicom_file)
            return dicom_file


    #os.path.isfile(filename)
    #os.path.isdir(filename)
    #os.listdir(filename)

def read_dicom_metadata(dicom_file, filename):
    dcm = pydicom.filereader.dcmread(dicom_file)
    std_name = dcm.PatientName
    # qa ex: A2CPS_QA^UI041621QA
    # A2CPS_QA^NS06292021QA
    # 'UC042121QA A2CPSQA'
    # UC10036V1 A2CPS
    # umich = tst
    print(std_name)
    # Stringify and remove A2CPS^ prefix
    if 'A2CPS^' in str(std_name):
        std_name = str(std_name).split('A2CPS^')[1]
    elif 'A2CPS_QA^' in str(std_name):
        std_name = str(std_name).split('A2CPS_QA^')[1]
        (site_id, subject_id, session_id) = re.split('(\d+)',std_name)
        return site_id, 'QC_' + subject_id, session_id
    elif ' A2CPSQA' in str(std_name):
        std_name = str(std_name).split(' A2CPSQA')[0]
        (site_id, subject_id, session_id) = re.split('(\d+)',std_name)
        return site_id, 'QC_' + subject_id, session_id
    elif ' A2CPS' in str(std_name):
        std_name = str(std_name).split(' A2CPS')[0]
    else:
        std_name = str(std_name)
    post_notification("Input file " + os.path.basename(filename) + \
                        " corresponds to " + std_name)
    (site_id, subject_id, v, session_number, space) = re.split('(\d+)',std_name)
    session_id = v + session_number
    return site_id, subject_id, session_id

def determine_output_path(site_id, subject_id, session_id):
    base_path = '/corral-secure/projects/A2CPS/products/mris/'
    site_codes = \
                {
                    "UI": "UI_uic",
                    "NS": "NS_northshore",
                    "UC": "UC_uchicago",
                    "UM": "UM_umichigan",
                    "WS": "WS_wayne_state",
                    "SH": "SH_spectrum_health"
                }
            
    output_path = base_path + \
                 site_codes[site_id] + \
                 '/dicoms/' + \
                 site_id + subject_id + session_id
    return output_path

def write_outputs(filename, output_path, isZip):
    if os.path.exists(output_path):
        print("Output file exists already, will not overwrite")
        data = post_notification("Output file exists already, will not overwrite " + output_zip)
        print(data)
        exit(1)

    if isZip:
        with zipfile.ZipFile(filename, 'r') as zip_ref:
            zip_ref.extractall(output_path)
    else:
        assert isZip is False
        copytree(filename, output_path)

    json_to_env({"dicom_dir": output_path})
    return

        # copyfile(filename, output_zip)
        # dicom_dir = output_zip.split('.zip')[0]
        # if os.path.exists(dicom_dir):
        #     print("Dicom dir exists already, will not overwrite")
        #     data = post_notification("Dicom dir exists already, will not overwrite " + dicom_dir)
        #     print(data)
        #     exit(1)
        # else:
        #     zipfile.ZipFile(output_zip, 'r') as zip_ref:
        #     zip_ref.extractall(dicom_dir)
        #     json_to_env({"dicom_dir": dicom_dir})


def json_to_env(json_dict):
    dot_list = []
    for key,value in json_dict.items():
        dot_list.append("export " + key + '=' + value)

    with open('.listfile.txt', 'w') as filehandle:
        for listitem in dot_list:
            filehandle.write('%s\n' % listitem)
    return

def main(filename):
    isZip = test_zip(filename)
    print(filename)
    dicom_file = find_dicom(filename, isZip)
    print(dicom_file)
    (site_id, subject_id, session_id) = read_dicom_metadata(dicom_file, filename)
    output_path = determine_output_path(site_id, subject_id, session_id)
    print(output_path)
    write_outputs(filename, output_path, isZip)
    message = {
        "site_id": site_id,
        "subject_id": subject_id,
        "session_id": session_id,
        "dicoms": output_path
    }
    message_heudiconv(message)
    notification = "Input file " + os.path.basename(filename) + " processed for " + \
                    subject_id + " output under " + output_path
    post_notification(notification)
    return

if __name__ == '__main__':
    main(sys.argv[1])


#ls /corral-secure/projects/A2CPS/submissions/a2dtn01/EXAM8186/
#ls /corral-secure/projects/A2CPS/submissions/UC_uchicago/UC0001V1_A2CPS.zip
# ls /corral-secure/projects/A2CPS/submissions/NS_northshore/Travelling volunteer 1 NS/1.3.12.2.1107.5.2.42.70032.30000020100520532859700000004.zip
#  /corral-secure/projects/A2CPS/system/jobs/1.3.12.2.1107.5.2.42.70032.30000020100520532859700000004/
#  /corral-secure/projects/A2CPS/system/jobs/UC0001V1_A2CPS/DICOM/00000001/
