import os,json,glob,shutil,re
from pathlib import Path
from nilearn.image import load_img,index_img
from collections import OrderedDict
import pandas as pd

def create_dwi_b0(dwi_b0_file,dwi_file):
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
        AP = index_img(b0_imgs,[0,1])
        PA = index_img(dwi_imgs,[0,1])
    else:
        AP = b0_imgs
        PA = index_img(dwi_imgs, 0)

    # Save images as AP and PA.
    output_AP_fname = Path(basepath,str(Path(dwi_b0_file).name).replace('dwib0_epi.nii.gz','dwib0_dir-AP_epi.nii.gz'))
    print("Saving AP image as %s"%output_AP_fname)
    AP.to_filename(output_AP_fname)

    output_PA_fname = Path(basepath,str(Path(dwi_b0_file).name).replace('dwib0_epi.nii.gz','dwib0_dir-PA_epi.nii.gz'))
    print("Saving PA image as %s"%output_PA_fname)
    PA.to_filename(output_PA_fname)

    return output_AP_fname,output_PA_fname


def rename_fmri_b0(fmri_b0_nifti: list, fmri_b0_json: list) -> None:
    # rename from epi# to dir-ap or dir-pa based on PhaseEncodingDirection in 
    # sidecar (the labels epi1 vs epi2 are not reliable)

    # first, comfirm that dcm2niix/heudiconv produced two files
    n_files = len(fmri_b0_json)
    if not n_files == 2:
        raise AssertionError(f"Unexpected number of fmrib0_epi files! Wanted 2, found {n_files}")
    
    name_translations = {}
    for filename in fmri_b0_json:
        with open(filename, 'r') as f:
            data = json.load(f)
            phaseencoding = data.get("PhaseEncodingDirection")            
        if phaseencoding == "j":
            epi_dir = "dir-PA_epi"                
        elif phaseencoding == "j-":
            epi_dir = "dir-AP_epi"
        elif phaseencoding is None:
            raise AssertionError(f"PhaseEncodingDirection not present for {filename}! Don't know how to relabel.")
        else:
            raise AssertionError(f"PhaseEncodingDirection set to {phaseencoding}! Don't know what to do with this.")                

        name_translations.update({re.findall(r"epi\d", filename)[0]: epi_dir})    

    for src in fmri_b0_nifti + fmri_b0_json:
        dst = src.replace("epi1", name_translations["epi1"]).replace("epi2", name_translations["epi2"])
        print(f"renaming {src} as {dst}")
        shutil.move(src, dst) 


def edit_scansdf(scans_df: pd.DataFrame) -> pd.DataFrame:
    """
    edits scans.tsv file to accomodate newly created and deleted fieldmaps
    """

    out0 = (
        scans_df
        .assign(filename=scans_df['filename'].str.replace("epi1","dir-AP_epi").str.replace("epi2","dir-PA_epi"))
    )

    filenames = out0[['filename']]
    
    dwib0 = filenames[filenames.filename.str.contains('dwib0_epi')]
    ap = pd.DataFrame(
        dwib0.apply(lambda x: re.sub('dwib0_epi','dwib0_dir-AP_epi', x.filename), axis=1),
        columns=['filename'])
    pa = pd.DataFrame(
        dwib0.apply(lambda x: re.sub('dwib0_epi','dwib0_dir-PA_epi', x.filename), axis=1),
        columns=['filename'])

    out = (
        out0[~out0.filename.str.contains('dwib0_epi')]
        .append([ap, pa])
        .fillna('n/a')
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
    sub_dir = str(Path(glob.glob(os.path.join(dirs,'sub-*'))[0]))

    # Getting session name
    sess_name = os.listdir(sub_dir)[0] # Assuming there is only a single session

    # Getting nifti files under fmap directory
    dwi_b0_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*dwib0*.nii.gz'))
    dwi_file = glob.glob(os.path.join(sub_dir,sess_name,'dwi','*dwi*.nii.gz'))

    # Getting json files under fmap directory
    dwi_json_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*dwib0*.json'))

    print("Creating fieldmaps for dwi data...")
    output_AP_fname_dwi,output_PA_fname_dwi = create_dwi_b0(dwi_b0_file[0],dwi_file[0])
    
    fmri_b0_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*fmrib0_epi*.nii.gz'))
    fmri_json_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*fmrib0_epi*.json'))
    if len(fmri_b0_file) > 0:
        print("Renaming fieldmaps for fmri data...")
        rename_fmri_b0(fmri_b0_file, fmri_json_file)
    else:
        print('No fmrib0 found. Nothing to rename')

    # remove original fieldmaps from scans.tsv and append new ones
    print("Updating scans.tsv file")
    scans_tsv = glob.glob(os.path.join(sub_dir, sess_name, 'sub-*_scans.tsv'))[0]
    scans_df = edit_scansdf(pd.read_csv(scans_tsv, sep='\t'))
    scans_df.to_csv(scans_tsv, sep="\t", index = False)

    print("Creating json files for DWI data...")
    AP_fname_dwi = str(output_AP_fname_dwi).replace('nii.gz','json')
    PA_fname_dwi = str(output_PA_fname_dwi).replace('nii.gz','json')
    shutil.copyfile(dwi_json_file[0], AP_fname_dwi)
    shutil.copyfile(dwi_json_file[0], PA_fname_dwi)

    # Remove the original fieldmap
    os.remove(str(dwi_b0_file[0]))
    os.remove(str(dwi_json_file[0]))




def add_fields_to_json(json_data, key, value):
    """
    json_data: json data in the form of dictionary
    key: Name of the key to be added to the json file
    value: Value of the key to be added
    """
    new_dict = OrderedDict()
    json_data[key]=value
    # sort the dictionary
    new_dict = OrderedDict(sorted(json_data.items(), key=lambda t: t[0]))

    # for k, v in json_data.items():
    #     if k==pos_key:
    #         new_dict[key] = value  # insert new key
    #     new_dict[k] = v
    return new_dict


def save_as_json(data: dict, json_filename: str):
    with open(json_filename, 'w') as data_file:
         json.dump(data, data_file,indent=1)


def get_manufacturer(json_file: str) -> str:
    '''
    extract manufacturer field from json_file

    Args:
        json_file: path to json data, presumably containing the field "manufacturer"

    Returns:
        extracted key

    Raises:
        AssertionError: file was opened, but key was not found
    '''
    with open(json_file, 'r') as f:
        json_data = json.load(f)    
        if not ('Manufacturer' in  json_data.keys()):
            raise AssertionError("No Manufacturer specified. Post-conversion fixes likely wrong.")
        manufacturer = json_data['Manufacturer'].lower()
    return manufacturer


def write_dummy_fields(filename: str):
    with open(filename, "r+") as f:
        json_data = json.load(f)
        json_data = add_fields_to_json(json_data, 'TotalReadoutTime', json_data["EstimatedTotalReadoutTime"])
        json_data = add_fields_to_json(json_data, 'EffectiveEchoSpacing', json_data["EstimatedEffectiveEchoSpacing"])
        save_as_json(json_data, filename)
        print(f"Added dummy TotalReadoutTime,EffectiveEchoSpacing to {filename}")


def edit_json(data_path):
    dirs = Path(data_path)
    
    # Hardcoded slice timings to be added to fmri json file. Used only for Philips scanner
    # From Xiaodong: The fMRI sequence in phantom QA is the same as that for subjects scan (June 7th, 2022): 
    slice_timing = [0,0.444,0.089,0.533,0.178,0.622,0.267,0.711,0.356,0,0.444,0.089,0.533,
                   0.178,0.622,0.267,0.711,0.356,0,0.444,0.089,0.533,0.178,0.622,0.267,0.711,0.356,0,0.444,
                   0.089,0.533,0.178,0.622,0.267,0.711,0.356,0,0.444,0.089,0.533,0.178,0.622,0.267,0.711,
                   0.356,0,0.444,0.089,0.533,0.178,0.622,0.267,0.711,0.356 ]
    # Accessing subject directory, removing hidden directory and sourcedata
    sub_dir = str(Path(glob.glob(os.path.join(dirs,'sub-*'))[0]))
    # Getting session name
    sess_name = os.listdir(sub_dir)[0] # Assuming there is only a single session
    # Getting json and nifti files under dwi and func directories
    json_files = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*b0*.json'))
    dwi_json_file = glob.glob(os.path.join(sub_dir,sess_name,'dwi','*dwi*.json'))

    # might be empy in cases where no dwi was run
    dwi_b0_json = [i for i in json_files if 'dwi' in i]

    func_b0_json = sorted([i for i in json_files if 'fmri' in i])
    func_json = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.json')))
    func_data = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.nii.gz')))

    # assume that if there was a conversion then there should be at least 1 json
    manufacturer = get_manufacturer(glob.glob(os.path.join(sub_dir, sess_name, '*', '*.json'))[0])

    print(f"Will try to apply post-conversion fixes specific to images from {manufacturer}...")    

    # Adding IntendedFor field in the b0 json files for DWI data
    for i in dwi_b0_json:
        f=open(i,'r')
        json_data=json.load(f)
        if manufacturer in ["philips", "ge"]:
            if 'AP' in str(Path(i).name):
                 value = "j-"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)
            else:
                 value="j"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection',  value)
            print(f"PhaseEncodingDirection for {i} set to {value}")

        # this could be empty, if, e.g., the b0 was run but then the DWI was skipped
        dwi_data_files = glob.glob(os.path.join(sub_dir,sess_name,'dwi','*.nii.gz'))
        value = [os.path.join(sess_name, 'dwi', Path(x).name) for x in dwi_data_files]
        updated_json = add_fields_to_json(json_data, 'IntendedFor',  value)
            
        save_as_json(updated_json, i)
        print("IntendedField is added to %s"%i)
        f.close()

    for i in dwi_json_file:
        print(i)
        f = open(i,'r')
        json_data=json.load(f)
        value = "j"
        updated_json = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)
        print("PhaseEncodingDirection is added to %s"%i)
        save_as_json(updated_json,i)
        f.close()
    # Adding IntendedFor field in the json files for rest and cuff data and PhaseEncodingDirection for Philips/GE
    for i in func_b0_json:
        f=open(i,'r')
        json_data=json.load(f)

        # Add PhaseEncodingDirection for Philips (not previously present)
        # fix PhaseEncodingDirection for GE
        if manufacturer in ["philips"]:
            if 'AP' in str(Path(i).name):
                 value = "j-"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection',  value)
            else:
                 value="j"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)
            print(f"PhaseEncodingDirection for {i} set to {value}")

        # Adds IntendedFor in the json files regardless of any scanner
        value = [os.path.join(sess_name,'func',str(Path(i).name)) for i in func_data]
        updated_json = add_fields_to_json(json_data, 'IntendedFor', value)
        save_as_json(updated_json,i)
        print("IntendedFor is added to %s"%i)
        f.close()
    # Add SliceTiming to the json files of rest/cuff json files
    if manufacturer == "philips":
       for i in func_json:
           f=open(i,'r')
           json_data=json.load(f)
           print(i)
           value = "j"
           json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)

           print("PhaseEncodingDirection is added to %s"%i)
            # Adds sliceTiming for Philips scanner
           updated_json = add_fields_to_json(json_data, 'SliceTiming', slice_timing)
           print("SliceTiming is added to %s"%i)
           save_as_json(updated_json,i)
           f.close()

    # add parameters missing from philips: TotalReadoutTime, EffectiveEchoSpacing
    # see: https://confluence.a2cps.org/x/kwnz
    # these are just dummy values, which works for distortion correction
    # but the units will not end up scaled correctly
    if manufacturer == "philips":
        for filename in dwi_json_file + func_json + func_b0_json + dwi_b0_json:
            write_dummy_fields(filename)

    if manufacturer == "siemens":
        # https://github.com/nipy/heudiconv/issues/303
        for f in dirs.glob("sub*/ses*/*/*json"):
            sanitize_json(f)


def sanitize_json(f) -> None:
    rewrite = False
    with open(f, "r") as j:
        data = json.load(j)
        if (
            data.__contains__("global") and 
            data['global'].__contains__("slices") and 
            data['global']['slices'].__contains__("DataSetTrailingPadding")
        ):
            del data['global']["slices"]["DataSetTrailingPadding"]
            if check_for_null(data):
                raise AssertionError(f"file {f} still has null characters, which will cause issues downstream")
            rewrite = True
    if rewrite:
        save_as_json(data, f)


def check_for_null(data: dict) -> bool:
    return '\\u0000' in json.dumps(data)


def get_b0_index(df,bval_value):
    ind = df.index[df['bvals'] == bval_value].tolist()
    return ind

