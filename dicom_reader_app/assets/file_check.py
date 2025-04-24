import datetime
import json
import os
import pathlib
import re
import sys
import zipfile
import tempfile
from shutil import copyfile, copytree, make_archive, rmtree
from typing import Literal, Tuple

import pydicom
import requests
from tapipy.tapis import Tapis

SITE_CODES = {
    "UI": "UI_uic",
    "NS": "NS_northshore",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "WS": "WS_wayne_state",
    "SH": "SH_spectrum_health",
    "RU": "RU_rush",
}


def get_device_serial_number(dcm_file: str) -> str:
    dcm = pydicom.dcmread(dcm_file, stop_before_pixels=True)
    device_serial_number = dcm.get("DeviceSerialNumber")
    if not isinstance(device_serial_number, str):
        raise ValueError("DeviceSerialNumber missing from dicom")

    return device_serial_number


def extract_phantom_date(dicom_file: str) -> str:
    """
    the label of the file should have the date, but this is unreliable
    here, we get the date from the dicom header in the first file
    of the zip
    """
    header = pydicom.dcmread(dicom_file, stop_before_pixels=True)

    if (day := header.get("SeriesDate")) or (
        day := header.get("AcquisitionDate")
    ):
        tmp = datetime.datetime.strptime(day, "%Y%m%d").date()
        return datetime.date.strftime(tmp, "%y%m%d")

    raise AssertionError(
        "AcquisitionDate not found in dicom. Incorrect file unzipped?"
    )


def yymmdd_to_mmddyy(day: str) -> str:
    tmp = datetime.datetime.strptime(day, "%y%m%d").date()
    return datetime.date.strftime(tmp, "%m%d%y")


def get_client():
    with open("/home1/09910/a2cpsadmin/.tapis3/a2cpsadmin", "r") as openfile:
        data = json.load(openfile)
    t = Tapis(
        base_url=data["base_url"],
        tenant_id=data["tenant_id"],
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        client_id=data["client_id"],
        client_key=data["client_key"],
        verify=True,
    )
    t.get_tokens()
    return t


def post_notification(client, notification):
    secretObj = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName="SLACKBOT_ADDRESS_SECRET_NAME",
        tenant=client.access_token.claims["tapis/tenant_id"],
        user=client.access_token.claims["tapis/username"],
    )
    endpoint = secretObj.get("secretMap").get("SLACKBOT_ADDRESS_SECRET_KEY")
    content = requests.post(url=endpoint, json={"text": notification})
    data = content.json()
    return data


def message_heudiconv(client, message):
    secretObj = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName="HEUDICONV_NONCE",
        tenant=client.access_token.claims["tapis/tenant_id"],
        user=client.access_token.claims["tapis/username"],
    )
    endpoint = secretObj.get("secretMap").get("HEUDICONV_NONCE")
    content = requests.post(url=endpoint, json=message)
    data = content.json()
    return data


def test_zip(filename: str) -> bool:
    try:
        zipfile.ZipFile(filename).testzip()
        return True
    except Exception:
        print("bad zip")
        return False


def is_device_serial_number_in_header(file: str) -> bool:
    header = pydicom.dcmread(file, stop_before_pixels=True)
    return "DeviceSerialNumber" in header


def find_dicom(filename: str, isZip: bool) -> str:
    # Find first zip dicom
    if isZip:
        site_zip = zipfile.ZipFile(filename)
        for listing in site_zip.infolist():
            if (not listing.is_dir()) and (
                "DICOMDIR" not in listing.orig_filename
            ):
                # confirm that device_serial_number is in this dicom
                # (missing from some RU files)
                with tempfile.TemporaryDirectory() as tmpd:
                    dicom_file = site_zip.extract(listing, tmpd)
                    if not (is_device_serial_number_in_header(dicom_file)):
                        continue
                return site_zip.extract(listing)
    # Find first unzipped dicom
    for root, _, files in os.walk(filename):
        if files != []:
            dicom_file = root + "/" + files[0]
            if not (is_device_serial_number_in_header(dicom_file)):
                continue
            print(dicom_file)
            return dicom_file

    raise RuntimeError("Unable to find dicom")


def get_site_from_zipfile(
    zipfile: pathlib.Path,
) -> Literal["UI", "NS", "UC", "UM", "WS", "SH", "RU"]:
    SUBMISSION_SITE = {
        "a2dtn01": "UI",
        "UI_uic": "UI",  # helps to have this when testing on files stored in products
        "UC_uchicago": "UC",
        "UM_umichigan": "UM",
        "NS_northshore": "NS",
        "SH_spectrum_health_grand_rapids": "SH",
        "SH_spectrum_health": "SH",  # helps to have this when testing on files stored in products
        "WS_wayne_state": "WS",
        "RU_rush_imaging": "RU",
    }

    return SUBMISSION_SITE.get(
        [
            key
            for key in SUBMISSION_SITE.keys()
            if key in str(zipfile.absolute())
        ][0]
    )  # type: ignore


def read_dicom_metadata(
    dicom_file: str, zipfile: pathlib.Path
) -> Tuple[str, str, str, str]:
    dcm = pydicom.dcmread(dicom_file, stop_before_pixels=True)
    patientname = str(dcm.PatientName)
    # qa ex: A2CPS_QA^UI041621QA
    # A2CPS_QA^NS06292021QA
    # 'UC042121QA A2CPSQA'
    # UC10036V1 A2CPS
    # umich = tst
    print(patientname)

    # phantom scan based on crude heuristic
    if re.search("[q][ac]", patientname, flags=re.IGNORECASE) is not None:
        # there is a standard for setting patient name with phantoms
        #  https://confluence.a2cps.org/pages/viewpage.action?spaceKey=DOC&title=A2CPS+Tech+Manual
        # - First name: <site code><mmddyy>QA; e.g. UI040121QA, UC050221QA, NS051521QA
        # - Last name: A2CPS_QA
        # but this has not been enforced and so patient name is very unreliable.
        # moreover, when building the bids dataset, the subject id is based on the site
        # and the session is based on the acquisition date (and for better sorting the ses is yymmdd

        # for phantom scans, the sites do not reliably encode their id in either the
        # dicom PatientName (see: UM) or the filename (see: UI), and unlike with patient scans there is
        # no external source of truth. So, site code is read based on the submission folder (fortunately,
        # sites can only upload to their own folder).
        #
        # this is not done for patient scans, as the site id *should* be in their PatientName field
        site_id = get_site_from_zipfile(zipfile=zipfile)
        subject_id = f"{site_id.lower()}phantom"
        session_id = extract_phantom_date(dicom_file)
        output_path = determine_output_path(
            site_id,
            subject_id=yymmdd_to_mmddyy(session_id),
            session_id="QA",
            qc="QC_",
        )
    else:
        std_name = re.search(
            "(NS|WS|UC|UM|UI|SH|RU)\d{5}[vV](1|3)", patientname.upper()
        ).group(
            0
        )  # type: ignore
        (site_id, subject_id, v, session_number, _) = re.split(
            "(\d+)", std_name
        )
        session_id = v + session_number
        output_path = determine_output_path(
            site_id, subject_id, session_id, qc=""
        )

    return site_id, subject_id, session_id, output_path


def determine_output_path(
    site_id: str, subject_id: str, session_id: str, qc: str = ""
) -> str:
    base_path = "/corral-secure/projects/A2CPS/products/mris/"
    # if it's not a qc scan, the qc object is an empty string
    output_path = (
        base_path
        + SITE_CODES[site_id]
        + "/dicoms/"
        + qc
        + site_id
        + subject_id
        + session_id
    )
    return output_path


def write_outputs(filename, output_path, isZip, client):
    if os.path.exists(output_path) or os.path.exists(output_path + ".zip"):
        print("Output file exists already, will not overwrite")
        data = post_notification(
            client,
            "Output file exists already, will not overwrite " + output_path,
        )
        print(data)
        exit(1)

    if isZip:
        copyfile(filename, output_path + ".zip")
    else:
        assert isZip is False
        copytree(filename, output_path)
        oldwd = os.getcwd()
        # os.chdir(output_path)
        # zip_files(filename, output_path, arcname=None)
        make_archive(output_path, "zip", output_path)
        rmtree(output_path)

    json_to_env({"dicom_dir": output_path + ".zip"})
    return


def json_to_env(json_dict):
    dot_list = []
    for key, value in json_dict.items():
        dot_list.append("export " + key + "=" + value)

    with open(".listfile.txt", "w") as filehandle:
        for listitem in dot_list:
            filehandle.write("%s\n" % listitem)
    return


def main(filename, predefined_subject_id):
    isZip = test_zip(filename)
    print(filename)
    dicom_file = find_dicom(filename, isZip)
    print(dicom_file)
    if predefined_subject_id is not None:
        (site_id, subject_id, v, session_number, _) = re.split(
            "(\d+)", predefined_subject_id
        )
        session_id = v + session_number
        output_path = determine_output_path(
            site_id, subject_id, session_id, qc=""
        )
    else:
        (site_id, subject_id, session_id, output_path) = read_dicom_metadata(
            dicom_file, pathlib.Path(filename)
        )
    device_serial_number = get_device_serial_number(dicom_file)

    print(output_path)
    print(device_serial_number)
    client = get_client()
    write_outputs(filename, output_path, isZip, client)
    message = {
        "device_serial_number": device_serial_number,
        "subject_id": subject_id,
        "session_id": session_id,
        "dicoms": output_path + ".zip",
    }
    message_heudiconv(client, message)
    notification = (
        "Input file "
        + os.path.basename(filename)
        + " processed for "
        + subject_id
        + " output under "
        + output_path
    )
    post_notification(client, notification)
    return


if __name__ == "__main__":
    # adding option to define subject id
    # should switch to using argparse in the future
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1], None)
