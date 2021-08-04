import os,json,glob,pydicom,shutil,re
from pathlib import Path
from nilearn.image import load_img,index_img
from collections import OrderedDict
import pandas as pd

def make_copy(path):
    """
    Makes a copy of the original data. The original data is saved with a suffix "_orig"
    """
    #suffix = '-orig'
    #dst = os.path.join(path+suffix)
    #dst = os.path.join(path,'dicom')
    dst = os.path.join('./dicom')
    print("Making a copy of the data...")
    if os.path.isdir(dst):
        flag=True
        print("Destination directory already exists")
    else:
        shutil.copytree(path, dst)
        flag=False
        print("Done!The original copy is %s"%path)
    return dst,flag

def get_subdirectory(path):
    """
    Returns all the subdirectories under 'func' directory of the raw subject data.
    """
    dirs = []
    for dirpath, dirnames, filenames in os.walk(path):
        if not dirnames:
            dirs.append(dirpath)
    return dirs,filenames,dirnames

def delete_tag(fname):
    try:
        ds = pydicom.read_file(fname)
        if ds.__contains__('TriggerTime'):
        # Delete the dicom tag 0018,1060. This tag represents the Trigger value
            del(ds['0018','1060'])
        #else:
            #print("No trigger tag found for %s"%fname)
        ds.save_as(fname)
    except:
        print("Unable to open the file %s"%fname)


def edit_dicom_file_philips(filepath):
    """
    Deletes the trigger tag (0018,1060) from the DICOM file.
    """
    # Copy the data to local "dicom" directory
    new_path,flag  = make_copy(filepath)

    if not flag:
        dirs,files,dirnames = get_subdirectory(new_path)
        for func in dirs:
            #print("Deleting tag for %s"%func)
            for i in sorted(os.listdir(func)):
                fname = os.path.join(func,i)
                #print('Working on file %s'%fname)
                delete_tag(fname)

        print("Searching for any files under %s"%new_path)

        # if files !=[]:
        #     for i in sorted(files):
        #         fname = os.path.join(new_path,i)
        #         #print('Working on file %s'%fname)
        #         delete_tag(fname)
        print("Done! New dicoms are stored in %s"%os.path.join(new_path))
    else:
        print("Skipping!")


def create_dwi_b0(dwi_b0_file,dwi_file):
    """
    Creates fieldmaps for DWI data
    """

    basepath = str(Path(dwi_b0_file).parents[0])

    # load images
    b0_imgs = load_img(dwi_b0_file)
    dwi_imgs = load_img(dwi_file)

    AP = index_img(b0_imgs,[0,1])
    PA = index_img(dwi_imgs,[0,1])

    # Save images as AP and PA.
    # First 2 volumes of b0 are saved as AP
    output_AP_fname = Path(basepath,str(Path(dwi_b0_file).name).replace('dwib0_epi.nii.gz','dwib0_dir-AP_epi.nii.gz'))
    print("Saving AP image as %s"%output_AP_fname)
    AP.to_filename(output_AP_fname)

    # First 2 volumes of DWI are saved as PA
    output_PA_fname = Path(basepath,str(Path(dwi_b0_file).name).replace('dwib0_epi.nii.gz','dwib0_dir-PA_epi.nii.gz'))
    print("Saving PA image as %s"%output_PA_fname)
    PA.to_filename(output_PA_fname)

    return output_AP_fname,output_PA_fname

def create_fmri_b0(b0_file):
    """
    Creates fieldmaps for functional data
    """

    # Get input path and subject name
    basepath = str(Path(b0_file).parents[0])

    # Split the fmri b0 image and merge the 1st and 3rd volumes for PA and 2nd and 4th for AP
    cmd = 'fslsplit %s %s' %(b0_file,os.path.join(basepath,'vol'))
    print(cmd)
    os.system(cmd)

#     PA = index_img(b0_imgs,[0,2])
#     AP = index_img(b0_imgs,[1,3])

    # Extract the 2nd and 4rth volumes of b0 for AP
    output_AP_fname = Path(basepath,str(Path(b0_file).name).replace('fmrib0_epi.nii.gz',
                                                                    'fmrib0_dir-AP_epi.nii.gz'))
    cmd = 'fslmerge -t %s %s %s' %(output_AP_fname,os.path.join(basepath,'vol0001.nii.gz'),
                               os.path.join(basepath,'vol0003.nii.gz'))
    print(cmd)
    os.system(cmd)

    print("Saving AP image as %s"%output_AP_fname)

    # Extract the 1st and 3rd volumes of b0 for PA
    output_PA_fname = Path(basepath,str(Path(b0_file).name).replace('fmrib0_epi.nii.gz',
                                                                    'fmrib0_dir-PA_epi.nii.gz'))

    cmd = 'fslmerge -t %s %s %s' %(output_PA_fname,os.path.join(basepath,'vol0000.nii.gz'),
                               os.path.join(basepath,'vol0002.nii.gz'))
    print(cmd)
    os.system(cmd)

    print("Saving PA image as %s"%output_PA_fname)

    # flip the orientation of AP and save as PA (to make them the same orientation)
    cmd = 'fslswapdim %s x -y z %s' %(output_PA_fname,output_PA_fname)
    print(cmd)
    os.system(cmd)

    # get the sform and qform of swapped image and change the y orientation using fslorient
    PA = load_img(str(output_PA_fname))

    sform = PA.header.get_sform()
    qform = PA.header.get_qform()
    sform[1,:] *= -1
    qform[1,:] *= -1

    sform = ' '.join(str(v) for v in sform.flatten().tolist())
    qform = ' '.join(str(v) for v in qform.flatten().tolist())

    # nipype does not have fslorient command, so have to run it as a shell command!
    cmd = 'fslorient -setsform %s %s' %(sform,output_PA_fname)
    cmd = 'fslorient -setqform %s %s' %(qform,output_PA_fname)
    print(cmd) # for ipython use !echo {cmd}
    os.system(cmd) # for ipython use !{cmd}

    files_to_remove = glob.glob(os.path.join(basepath,"vol*"))
    for i in files_to_remove:
        os.remove(i)

    return output_AP_fname, output_PA_fname


def edit_scansdf(scans_df):
    """
    edits scans.tsv file to accomodate newly created and deleted fieldmaps
    """

    filenames = scans_df[['filename']]
    
    fmaps = filenames[filenames.filename.str.contains('fmap')]
    ap = pd.DataFrame(
        fmaps.apply(lambda x: re.sub('b0_','b0_dir-AP_', x.filename), axis=1),
        columns=['filename'])
    pa = pd.DataFrame(
        fmaps.apply(lambda x: re.sub('b0_','b0_dir-PA_', x.filename), axis=1),
        columns=['filename'])

    out = scans_df[~scans_df.filename.str.contains('fmap')].append([ap, pa]).fillna('n/a')

    return out


def create_fieldmaps(data_path):
    """
    Creates DWI and fMRI fieldmaps for GE data
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
    fmri_b0_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*fmrib0*.nii.gz'))

    # Getting json files under fmap directory
    dwi_json_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*dwib0*.json'))
    fmri_json_file = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*fmrib0*.json'))

    print("Creating fieldmaps for dwi data...")
    output_AP_fname_dwi,output_PA_fname_dwi = create_dwi_b0(dwi_b0_file[0],dwi_file[0])

    print("Creating fieldmaps for fmri data...")
    output_AP_fname_fmri, output_PA_fname_fmri = create_fmri_b0(fmri_b0_file[0])

    print("Creating json files for DWI data...")
    AP_fname_dwi = str(output_AP_fname_dwi).replace('nii.gz','json')
    PA_fname_dwi = str(output_PA_fname_dwi).replace('nii.gz','json')
    shutil.copyfile(dwi_json_file[0], AP_fname_dwi)
    shutil.copyfile(dwi_json_file[0], PA_fname_dwi)

    print("Creating json files for fmri data...")
    AP_fname_fmri = str(output_AP_fname_fmri).replace('nii.gz','json')
    PA_fname_fmri = str(output_PA_fname_fmri).replace('nii.gz','json')
    shutil.copyfile(fmri_json_file[0], AP_fname_fmri)
    shutil.copyfile(fmri_json_file[0], PA_fname_fmri)

    # Remove the original fieldmap
    os.remove(str(dwi_b0_file[0]))
    os.remove(str(fmri_b0_file[0]))
    os.remove(str(fmri_json_file[0]))
    os.remove(str(dwi_json_file[0]))

    # remove original fieldmaps from scans.tsv and append new ones
    print("Updating scans.tsv file")
    scans_tsv = glob.glob(os.path.join(sub_dir, sess_name, 'sub-*_scans.tsv'))[0]
    scans_df = edit_scansdf(pd.read_csv(scans_tsv, sep='\t'))
    scans_df.to_csv(scans_tsv, sep="\t", index = False)


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

def save_as_json(data,json_filename):
    with open(json_filename, 'w') as data_file:
         json.dump(data, data_file,indent=1)


def test_if_philips(json_data: dict):
    if not ('Manufacturer' in  json_data.keys()):
        raise AssertionError("No Manufacturer specified. Post-conversion fixes likely wrong.")
    print("Will try to apply post-conversion fixes specific to images from Philips...")
    return json_data['Manufacturer'] == "Philips"


def edit_json(data_path):
    dirs = Path(data_path)
    
    # Hardcoded slice timings to be added to fmri json file. Used only for Philips scanner
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
    dwi_b0_json = sorted([i for i in json_files if 'dwi' in i])
    dwi_data = Path(glob.glob(os.path.join(sub_dir,sess_name,'dwi','*.nii.gz'))[0]).name # assuming simple case of 1 DWI data
    func_b0_json = sorted([i for i in json_files if 'fmri' in i])
    func_json = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.json')))
    func_data = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.nii.gz')))

    # Adding IntendedFor field in the b0 json files for DWI data
    for i in dwi_b0_json:
        f=open(i,'r')
        json_data=json.load(f)
        if test_if_philips(json_data):
            philips_scanner=False
        else:
            philips_scanner=True
            if 'AP' in str(Path(i).name):
                 value = "j-"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)
            else:
                 value="j"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection',  value)
            print("PhaseEncodingDirection is added to %s"%i)

        value = [os.path.join(sess_name,'dwi',dwi_data)]
        updated_json = add_fields_to_json(json_data, 'IntendedFor',  value)
        save_as_json(updated_json,i)
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
    # Adding IntendedFor field in the json files for rest and cuff data and sliceTiming and PhaseEncodingDirection for Philips
    for i in func_b0_json:
        f=open(i,'r')
        json_data=json.load(f)

        # Adds sliceTiming and PhaseEncodingDirection for Philips scanner
        if test_if_philips(json_data):
            philips_scanner=False
        else:
            philips_scanner=True
        # Adds PhaseEncodingDirection in the json files for Philips scanner
            if 'AP' in str(Path(i).name):
                 value = "j-"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection',  value)
            else:
                 value="j"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)
            print("PhaseEncodingDirection is added to %s"%i)

        # Adds IntendedFor in the json files regardless of any scanner
        value = [os.path.join(sess_name,'func',str(Path(i).name)) for i in func_data]
        updated_json = add_fields_to_json(json_data, 'IntendedFor', value)
        save_as_json(updated_json,i)
        print("IntendedFor is added to %s"%i)
        f.close()
    # Add SliceTiming to the json files of rest/cuff json files
    if philips_scanner:
       for i in func_json:
           f=open(i,'r')
           json_data=json.load(f)
           print(i)
           #if 'AP' in str(Path(i).name):
           value = "j"
           json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)
           #else:
           #      value="j"
           #      json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', value)

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
    if philips_scanner:
        func_ap = [x for x in func_b0_json if 'AP' in str(Path(x).name)]
        func_pa = [x for x in func_b0_json if 'PA' in str(Path(x).name)]

        with open(func_ap, 'r+') as a, open(func_pa, 'r+') as p:
            ap_data = json.load(a)
            pa_data = json.load(p)
            if not (ap_data["EstimatedTotalReadoutTime"] == pa_data["EstimatedTotalReadoutTime"]):
                raise AssertionError(f"Not finishing because EstimatedTotalReadoutTime do not match in {a} and {p}")                
            
            ap_data = add_fields_to_json(ap_data, 'TotalReadoutTime', ap_data["EstimatedTotalReadoutTime"])
            pa_data = add_fields_to_json(pa_data, 'TotalReadoutTime', pa_data["EstimatedTotalReadoutTime"])

            if not (ap_data["EstimatedEffectiveEchoSpacing"] == pa_data["EstimatedEffectiveEchoSpacing"]):
                raise AssertionError(f"Not finishing because EstimatedEffectiveEchoSpacing do not match in {a} and {p}")                
            
            updated_ap_data = add_fields_to_json(ap_data, 'EffectiveEchoSpacing', ap_data["EstimatedEffectiveEchoSpacing"])
            updated_pa_data = add_fields_to_json(pa_data, 'EffectiveEchoSpacing', pa_data["EstimatedEffectiveEchoSpacing"])
            save_as_json(updated_ap_data, a)
            save_as_json(updated_pa_data, p)
            print(f"Added dummy TotalReadoutTime,EffectiveEchoSpacing to {a} and {p}")
        
        with open(dwi_json_file, "r+") as d:
            dwi_json_data = json.load(d)
            dwi_json_data = add_fields_to_json(dwi_json_data, 'TotalReadoutTime', dwi_json_data["EstimatedTotalReadoutTime"])
            updated_dwi_json_data = add_fields_to_json(dwi_json_data, 'EffectiveEchoSpacing', dwi_json_data["EstimatedEffectiveEchoSpacing"])
            save_as_json(updated_dwi_json_data, d)


def get_b0_index(df,bval_value):
    ind = df.index[df['bvals'] == bval_value].tolist()
    return ind

def split_shells(basepath):
    if os.path.exists(os.path.join(basepath,'preprocess-dti')):
        pass
    else:
        os.mkdir(os.path.join(basepath,'preprocess-dti'))
    resultpath=os.path.join(basepath,'preprocess-dti')
    # Find the filepaths of dwi dataset
    bval_filepath = glob.glob(os.path.join(basepath,'*T1w_desc-preproc_dwi.bval'))[0]
    dwi_filepath = glob.glob(os.path.join(basepath,'*T1w_desc-preproc_dwi.nii.gz'))[0]
    bvec_filepath = glob.glob(os.path.join(basepath,'*T1w_desc-preproc_dwi.bvec'))[0]

    # Extract the base filename; useful when saving the results
    base_fname = str(Path(bval_filepath).name).split('.')[0]

    # Read the processed bval and bvec files
    bval_file = pd.read_table(bval_filename,header=None)
    bval_file.columns=['bvals']
    bvec_file = pd.read_csv(bvec_filename,header=None,sep=' ')
    bvec_file = bvec_file.T
    dwi_data = load_img(dwi_filename)

    # Find the index of each shells and adds a b0 shell at the beginning. Assuming there are 5 shells
    shells = bval_file['bvals'].unique()
    ind_3000 = [0]+get_b0_index(bval_file,3000)
    ind_2000 = [0]+get_b0_index(bval_file,2000)
    ind_1000 = [0]+get_b0_index(bval_file,1000)
    ind_500 = [0]+get_b0_index(bval_file,500)

    # Find the corresponding nifti, bvals and bvecs
    dwi_data_3000 = index_img(dwi_data,ind_3000)
    dwi_data_2000 = index_img(dwi_data,ind_2000)
    dwi_data_1000 = index_img(dwi_data,ind_1000)
    dwi_data_500 = index_img(dwi_data,ind_500)

    bval_3000 = bval_file.iloc[ind_3000]
    bval_2000 = bval_file.iloc[ind_2000]
    bval_1000 = bval_file.iloc[ind_1000]
    bval_500 = bval_file.iloc[ind_500]

    bvec_3000 = bvec_file.iloc[ind_3000]
    bvec_2000 = bvec_file.iloc[ind_2000]
    bvec_1000 = bvec_file.iloc[ind_1000]
    bvec_500 = bvec_file.iloc[ind_500]

    # Saving nifti, bvals and bvecs
    print("Saving files...")
    dwi_data_3000.to_filename(os.path.join(resultpath,base_fname+'_2nd_shell.nii.gz'))
    dwi_data_2000.to_filename(os.path.join(resultpath,base_fname+'_3rd_shell.nii.gz'))
    dwi_data_1000.to_filename(os.path.join(resultpath,base_fname+'_4rth_shell.nii.gz'))
    dwi_data_500.to_filename(os.path.join(resultpath,base_fname+'_5th_shell.nii.gz'))

    bval_3000.to_csv(os.path.join(resultpath,base_fname+'_2nd_shell.bval'),header=None, index=None)
    bval_2000.to_csv(os.path.join(resultpath,base_fname+'_3rd_shell.bval'),header=None, index=None)
    bval_1000.to_csv(os.path.join(resultpath,base_fname+'_4rth_shell.bval'),header=None, index=None)
    bval_500.to_csv(os.path.join(resultpath,base_fname+'_5th_shell.bval'),header=None, index=None)

    bvec_3000.to_csv(os.path.join(resultpath,base_fname+'_2nd_shell.bvec'),header=None, index=None,sep=' ')
    bvec_2000.to_csv(os.path.join(resultpath,base_fname+'_3rd_shell.bvec'),header=None, index=None,sep=' ')
    bvec_1000.to_csv(os.path.join(resultpath,base_fname+'_4rth_shell.bvec'),header=None, index=None,sep=' ')
    bvec_500.to_csv(os.path.join(resultpath,base_fname+'_5th_shell.bvec'),header=None, index=None,sep=' ')
