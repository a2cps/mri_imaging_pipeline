import os, json, glob, shutil, re
import pathlib
from pathlib import Path
from nilearn.image import load_img, index_img
import pandas as pd

# Hardcoded slice timings to be added to fmri json file. Used only for Philips scanner
# From Xiaodong: The fMRI sequence in phantom QA is the same as that for subjects scan (June 7th, 2022):
slice_timing = [
    0,
    0.444,
    0.089,
    0.533,
    0.178,
    0.622,
    0.267,
    0.711,
    0.356,
    0,
    0.444,
    0.089,
    0.533,
    0.178,
    0.622,
    0.267,
    0.711,
    0.356,
    0,
    0.444,
    0.089,
    0.533,
    0.178,
    0.622,
    0.267,
    0.711,
    0.356,
    0,
    0.444,
    0.089,
    0.533,
    0.178,
    0.622,
    0.267,
    0.711,
    0.356,
    0,
    0.444,
    0.089,
    0.533,
    0.178,
    0.622,
    0.267,
    0.711,
    0.356,
    0,
    0.444,
    0.089,
    0.533,
    0.178,
    0.622,
    0.267,
    0.711,
    0.356,
]


def create_dwi_b0(dwi_b0_file, dwi_file):
    """
    Creates fieldmaps for DWI data
    """

    basepath = str(Path(dwi_b0_file).parents[0])

    # load images
    b0_imgs = load_img(dwi_b0_file)
    dwi_imgs = load_img(dwi_file)

    # most GE scanners give b0 images with 8 volumes (4D image)
    # second UM scanner gives just a single volume (only 3D image)
    if len(b0_imgs.shape) == 4:
        AP = index_img(b0_imgs, [0, 1])
        PA = index_img(dwi_imgs, [0, 1])
    else:
        AP = b0_imgs
        PA = index_img(dwi_imgs, 0)

    # Save images as AP and PA.
    output_AP_fname = Path(
        basepath,
        str(Path(dwi_b0_file).name).replace(
            "dwib0_epi.nii.gz", "dwib0_dir-AP_epi.nii.gz"
        ),
    )
    print("Saving AP image as %s" % output_AP_fname)
    AP.to_filename(output_AP_fname)

    output_PA_fname = Path(
        basepath,
        str(Path(dwi_b0_file).name).replace(
            "dwib0_epi.nii.gz", "dwib0_dir-PA_epi.nii.gz"
        ),
    )
    print("Saving PA image as %s" % output_PA_fname)
    PA.to_filename(output_PA_fname)

    return output_AP_fname, output_PA_fname


def rename_fmri_b0(fmri_b0_nifti: list, fmri_b0_json: list) -> None:
    # rename from epi# to dir-ap or dir-pa based on PhaseEncodingDirection in
    # sidecar (the labels epi1 vs epi2 are not reliable)

    # first, comfirm that dcm2niix/heudiconv produced two files
    n_files = len(fmri_b0_json)
    if not n_files == 2:
        raise AssertionError(
            f"Unexpected number of fmrib0_epi files! Wanted 2, found {n_files}"
        )

    name_translations = {}
    for filename in fmri_b0_json:
        with open(filename, "r") as f:
            data = json.load(f)
            phaseencoding = data.get("PhaseEncodingDirection")
        if phaseencoding == "j":
            epi_dir = "dir-PA_epi"
        elif phaseencoding == "j-":
            epi_dir = "dir-AP_epi"
        elif phaseencoding is None:
            raise AssertionError(
                f"PhaseEncodingDirection not present for {filename}! Don't know how to relabel."
            )
        else:
            raise AssertionError(
                f"PhaseEncodingDirection set to {phaseencoding}! Don't know what to do with this."
            )

        name_translations.update({re.findall(r"epi\d", filename)[0]: epi_dir})

    for src in fmri_b0_nifti + fmri_b0_json:
        dst = src.replace("epi1", name_translations["epi1"]).replace(
            "epi2", name_translations["epi2"]
        )
        print(f"renaming {src} as {dst}")
        shutil.move(src, dst)


def edit_scansdf(scans_df: pd.DataFrame) -> pd.DataFrame:
    """
    edits scans.tsv file to accomodate newly created and deleted fieldmaps
    """

    out0 = scans_df.assign(
        filename=scans_df["filename"]
        .str.replace("epi1", "dir-AP_epi")
        .str.replace("epi2", "dir-PA_epi")
    )

    filenames = out0[["filename"]]

    dwib0 = filenames[filenames.filename.str.contains("dwib0_epi")]
    ap = pd.DataFrame(
        dwib0.apply(
            lambda x: re.sub("dwib0_epi", "dwib0_dir-AP_epi", x.filename), axis=1
        ),
        columns=["filename"],
    )
    pa = pd.DataFrame(
        dwib0.apply(
            lambda x: re.sub("dwib0_epi", "dwib0_dir-PA_epi", x.filename), axis=1
        ),
        columns=["filename"],
    )

    out = (
        out0[~out0.filename.str.contains("dwib0_epi")]
        .append([ap, pa])
        .fillna("n/a")
        .reset_index(drop=True)
    )

    return out


def create_fieldmaps(data_path) -> None:
    """
    Creates DWI fieldmaps for GE data
    data_path: str full path of subject
    e.g. create_fieldmaps('/home/tanmay/hacking/AC2PC/data/uic/development/UI_uic/UI_travhuman')
    """
    dirs = Path(data_path)

    # Accessing subject directory, removing hidden directory and sourcedata
    sub_dir = str(Path(glob.glob(os.path.join(dirs, "sub-*"))[0]))

    # Getting session name
    sess_name = os.listdir(sub_dir)[0]  # Assuming there is only a single session

    # Getting nifti files under fmap directory
    dwi_b0_file = glob.glob(os.path.join(sub_dir, sess_name, "fmap", "*dwib0*.nii.gz"))
    dwi_file = glob.glob(os.path.join(sub_dir, sess_name, "dwi", "*dwi*.nii.gz"))

    # Getting json files under fmap directory
    dwi_json_file = glob.glob(os.path.join(sub_dir, sess_name, "fmap", "*dwib0*.json"))

    print("Creating fieldmaps for dwi data...")
    output_AP_fname_dwi, output_PA_fname_dwi = create_dwi_b0(
        dwi_b0_file[0], dwi_file[0]
    )

    fmri_b0_file = glob.glob(
        os.path.join(sub_dir, sess_name, "fmap", "*fmrib0_epi*.nii.gz")
    )
    fmri_json_file = glob.glob(
        os.path.join(sub_dir, sess_name, "fmap", "*fmrib0_epi*.json")
    )
    if len(fmri_b0_file) > 0:
        print("Renaming fieldmaps for fmri data...")
        rename_fmri_b0(fmri_b0_file, fmri_json_file)
    else:
        print("No fmrib0 found. Nothing to rename")

    # remove original fieldmaps from scans.tsv and append new ones
    print("Updating scans.tsv file")
    scans_tsv = glob.glob(os.path.join(sub_dir, sess_name, "sub-*_scans.tsv"))[0]
    scans_df = edit_scansdf(pd.read_csv(scans_tsv, sep="\t"))
    scans_df.to_csv(scans_tsv, sep="\t", index=False)

    print("Creating json files for DWI data...")
    AP_fname_dwi = str(output_AP_fname_dwi).replace("nii.gz", "json")
    PA_fname_dwi = str(output_PA_fname_dwi).replace("nii.gz", "json")
    shutil.copyfile(dwi_json_file[0], AP_fname_dwi)
    shutil.copyfile(dwi_json_file[0], PA_fname_dwi)

    # Remove the original fieldmap
    os.remove(str(dwi_b0_file[0]))
    os.remove(str(dwi_json_file[0]))


def save_as_json(data: dict, json_filename: str):
    with open(json_filename, "w") as data_file:
        json.dump(obj=data, fp=data_file, indent=1, sort_keys=True)


def get_manufacturer(dirs: pathlib.Path) -> str:
    """
    extract manufacturer field from json_file

    Args:
        dirs: bids root directory

    Returns:
        extracted key

    Raises:
        AssertionError: key not found in any of the jsons
    """
    for i in dirs.glob("sub*/ses*/*/*json"):
        with open(i, "r") as f:
            json_data = json.load(f)
            if json_data.__contains__("Manufacturer"):
                return json_data["Manufacturer"].lower()

    raise AssertionError("Unable to find json with Manufacturer field")


def write_dummy_fields(filename: str):
    with open(filename) as f:
        json_data = json.load(f)
        json_data["TotalReadoutTime"] = json_data["EstimatedTotalReadoutTime"]
        json_data["EffectiveEchoSpacing"] = json_data["EstimatedEffectiveEchoSpacing"]

    save_as_json(json_data, filename)
    print(f"Added dummy TotalReadoutTime,EffectiveEchoSpacing to {filename}")


def add_intendedfor(meta: pathlib.Path, dirs: pathlib.Path, modality: str) -> None:
    # add each fmri or dwi to the fmap intendedfor, but only if the phase encoding axes match
    intendedfor = []
    json_data = json.loads(meta.read_text())
    for nii in dirs.glob(f"sub*/ses*/{modality}/*json"):
        with open(nii) as n:
            phase_axis_nii = json.load(n).get("PhaseEncodingDirection")[0]
        if phase_axis_nii in json_data.get("PhaseEncodingDirection"):
            # assumes that there is always a session
            intendedfor.append(
                str(nii.relative_to(nii.parents[2]).with_suffix(".nii.gz"))
            )
    if len(intendedfor) > 0:
        json_data["IntendedFor"] = intendedfor
        save_as_json(json_data, meta)
        print(f"IntendedField is added to {meta}")


def set_jsonfield(meta: pathlib.Path, key: str, value: str) -> None:
    with open(meta) as f:
        json_data = json.load(f)
        json_data[key] = value

    save_as_json(json_data, meta)
    print(f"{key} for {meta} is set to {value}")


def edit_json(data_path):
    dirs = Path(data_path).absolute()

    # assume that if there was a conversion then there should be at least 1 json
    manufacturer = get_manufacturer(dirs)

    print(
        f"Will try to apply post-conversion fixes specific to images from {manufacturer}"
    )

    for i in dirs.glob("sub*/ses*/dwi/*dwi*json"):
        set_jsonfield(i, key="PhaseEncodingDirection", value="j")

    # Add SliceTiming to the json files of rest/cuff json files
    if manufacturer == "philips":
        for i in dirs.glob("sub*/ses*/func/*json"):
            set_jsonfield(i, key="PhaseEncodingDirection", value="j")
            set_jsonfield(i, key="SliceTiming", value=slice_timing)

        # add parameters missing from philips: TotalReadoutTime, EffectiveEchoSpacing
        # see: https://confluence.a2cps.org/x/kwnz
        # these are just dummy values, which works for distortion correction
        # but the units will not end up scaled correctly
        for filename in dirs.glob("sub*/ses*/*/*json"):
            write_dummy_fields(filename)

    # Adding IntendedFor field in the b0 json files for DWI data
    # NOTE: for Philips, this must happen after the PhaseEncodingDirection has been set
    for i in dirs.glob("sub*/ses*/fmap/*dwib0*json"):
        if manufacturer in ["philips", "ge"]:
            if "AP" in str(Path(i).name):
                value = "j-"
            else:
                value = "j"
            set_jsonfield(i, key="PhaseEncodingDirection", value=value)

        add_intendedfor(i, dirs, "dwi")

    # Adding IntendedFor field in the json files for rest and cuff data, all sites
    # also add PhaseEncodingDirection for Philips
    for i in dirs.glob("sub*/ses*/fmap/*fmrib0*json"):
        if manufacturer in ["philips"]:
            if "AP" in str(Path(i).name):
                value = "j-"
            else:
                value = "j"
            set_jsonfield(i, key="PhaseEncodingDirection", value=value)

        add_intendedfor(i, dirs, "func")

    if manufacturer == "siemens":
        # https://github.com/nipy/heudiconv/issues/303
        for f in dirs.glob("sub*/ses*/*/*json"):
            sanitize_json(f)


def sanitize_json(f) -> None:
    rewrite = False
    with open(f) as j:
        data = json.load(j)
        if (
            data.__contains__("global")
            and data["global"].__contains__("slices")
            and data["global"]["slices"].__contains__("DataSetTrailingPadding")
        ):
            del data["global"]["slices"]["DataSetTrailingPadding"]
            if check_for_null(data):
                raise AssertionError(
                    f"file {f} still has null characters, which will cause issues downstream"
                )
            rewrite = True
    if rewrite:
        save_as_json(data, f)


def check_for_null(data: dict) -> bool:
    return "\\u0000" in json.dumps(data)
