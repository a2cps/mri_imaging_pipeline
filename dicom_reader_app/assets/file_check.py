import os
#import zipfile
import zipfile38 as zipfile
from shutil import copyfile,copytree,make_archive,rmtree
import requests
import sys
import pydicom
import re
import datetime

def extract_phantom_date(dicom_file: str) -> str:
    """
    the label of the file should have the date, but this is unreliable
    here, we get the date from the dicom header in the first file 
    of the zip
    """
    #zip = zipfile.ZipFile(dicoms)
    #dicom_file = zip.extract(f)
    header = pydicom.dcmread(dicom_file, stop_before_pixels=True)
    if not header.__contains__("AcquisitionDate"):
        AssertionError ("AcquisitionDate not found in dicom. Incorrect file unzipped?")
        
    day = header.get("AcquisitionDate")
    tmp = datetime.datetime.strptime(day, "%Y%m%d").date()
    return datetime.date.strftime(tmp, "%y%m%d")


def post_notification(notification):
    endpoint = r"https://api.a2cps.org/actors/v2/imaging-slackbot.prod/messages?x-nonce=A2CPS_w1r4M51bYemAQ"
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
            if zipfile.Path.is_file(listing): #and 'DICOMDIR' not in listing.orig_filename
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
    std_name = str(std_name).upper()

    patient_id = re.search('(NS|WS|UC|UM|UI|SH)\d{5}[vV](1|3)',std_name)
    # Check if it's a QA scan
    qa = re.search('[Qq][Aa]',std_name)
    if qa is not None:
        # If it's not a QC scan we don't add the QC prefix
        qa_id = re.search('[A-Z][A-Z]\d+',std_name)
        std_name = qa_id.group(0)
        qc = 'QC_'
        (site_id, subject_id, session_id) = re.split('(\d+)',std_name)
        session_id='QA'
    else:
        std_name = patient_id.group(0)
        # If it's not a QC scan we don't add the QC prefix
        # and just use an empty string
        qc=''
        (site_id, subject_id, v, session_number, space) = re.split('(\d+)',std_name)
        session_id = v + session_number

    return site_id, subject_id, session_id, qc


def determine_output_path(site_id, subject_id, session_id, qc=''):
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
    # if it's not a qc scan, the qc object is an empty string
    output_path = base_path + \
                 site_codes[site_id] + \
                 '/dicoms/' + \
                 qc + \
                 site_id + subject_id + session_id
    return output_path

def write_outputs(filename, output_path, isZip):
    if os.path.exists(output_path) or os.path.exists(output_path + '.zip'):
        print("Output file exists already, will not overwrite")
        data = post_notification("Output file exists already, will not overwrite " + output_path)
        print(data)
        exit(1)

    if isZip:
        #with zipfile.ZipFile(filename, 'r') as zip_ref:
        #    zip_ref.extractall(output_path)
        copyfile(filename, output_path + '.zip')
    else:
        assert isZip is False
        copytree(filename, output_path)
        oldwd = os.getcwd()
        #os.chdir(output_path)
        #zip_files(filename, output_path, arcname=None)
        make_archive(output_path, 'zip', output_path)
        rmtree(output_path)

    json_to_env({"dicom_dir": output_path + '.zip'})
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

def main(filename, predefined_subject_id):
    isZip = test_zip(filename)
    print(filename)
    dicom_file = find_dicom(filename, isZip)
    print(dicom_file)
    if predefined_subject_id is not None:
        (site_id, subject_id, v, session_number, space) = re.split('(\d+)', predefined_subject_id)
        session_id = v + session_number
        qc = ''
    else:
        (site_id, subject_id, session_id, qc) = read_dicom_metadata(dicom_file, filename)
    output_path = determine_output_path(site_id, subject_id, session_id, qc)
    print(output_path)
    write_outputs(filename, output_path, isZip)
    if qc == "":
        message = {
            "site_id": site_id,
            "subject_id": subject_id,
            "session_id": session_id,
            "dicoms": output_path + '.zip'
        }
    else:
        message = {
            "site_id": site_id,
            "subject_id": f"{site_id.lower()}phantom",
            "session_id": extract_phantom_date(dicom_file),
            "dicoms": output_path + '.zip'
        }
    message_heudiconv(message)
    notification = "Input file " + os.path.basename(filename) + " processed for " + \
                    subject_id + " output under " + output_path
    post_notification(notification)
    return

if __name__ == '__main__':
    # adding option to define subject id
    # should switch to using argparse in the future
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1], None)


