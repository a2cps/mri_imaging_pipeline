import os, pydicom, shutil
from pathlib import Path
from nilearn.image import load_img,index_img
import json,glob
from collections import OrderedDict

def make_copy(path):
    """
    Makes a copy of the original data. The original data is saved with a suffix "_orig"
    """
    #suffix = '-orig'
    #dst = os.path.join(path+suffix)
    dst = os.path.join('./dicom')
    print("Making a copy of the data...")
    if os.path.isdir(dst):
        flag=True
        print("Destination directory already exists")
    else:
        shutil.copytree(path, dst)
        flag=False
        print("Done!The original copy is %s"%dst)
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
        else:
            print("No trigger tag found for %s"%fname)
        ds.save_as(fname)
    except:
        print("Unable to open the file %s"%fname)
        
        
def edit_dicom_file_philips(filepath):
    """
    Deletes the trigger tag (0018,1060) from the DICOM file.
    """
    # Copy the data, add suffix "_orig" to the original data and return the path of duplicate data
    new_path,flag  = make_copy(filepath)

    if not flag:
        dirs,files,dirnames = get_subdirectory(new_path)
        for func in dirs:
            print("Deleting tag for %s"%func)
            for i in sorted(os.listdir(func)):
                fname = os.path.join(func,i)
                print('Working on file %s'%fname)
                delete_tag(fname)
                
        print("Searching for any files under %s"%filepath)
        
        if files !=[]:
            for i in sorted(files):
                fname = os.path.join(filepath,i)
                print('Working on file %s'%fname)
                delete_tag(fname)
        print("Done! New dicoms are stored in %s"%os.path.join(filepath))
    else:
        print("Skipping!")

def change_dwi_b0(b0_file,dwi_file):
    """
    """
    # Get input path and subject name
    b0_imgs_path = str(Path(b0_file).parents[0])
    dwi_imgs_path = str(Path(dwi_file).parents[0])
    #get subject name
#     subj_name =  str(Path(b0_file).name).split('_')[0] 
    
    # load images
    b0_imgs = load_img(b0_file)
    dwi_imgs = load_img(dwi_file)
    
    # Extract the first 2 volumes of b0 and DWI images

    PA = index_img(b0_imgs,[0,1])
    AP = index_img(dwi_imgs,[0,1])
    
    # Save images as AP and PA. First 2 volumes of b0 are saved as AP 
    output_AP_fname = Path(b0_imgs_path,str(Path(dwi_file).name).replace('_dwi.nii.gz','_acq-dwib0_dir-AP_epi.nii.gz'))
    print("Saving AP image as %s"%output_AP_fname)
    AP.to_filename(output_AP_fname)
    
    # First 2 volumes of DWI are saved as PA
    output_PA_fname = Path(b0_imgs_path,str(Path(dwi_file).name).replace('_dwi.nii.gz','_acq-dwib0_dir-PA_epi.nii.gz'))
    print("Saving PA image as %s"%output_PA_fname)
    PA.to_filename(output_PA_fname)

#     return AP, PA        

def drop_dwi_vols(dwi_file):
    dwi_imgs = load_img(dwi_file)
    dwi_data = index_img(dwi_imgs,range(2,dwi_imgs.shape[-1]))
    print("Saving dwi image...")
    dwi_data.to_filename(dwi_file)
    
    

def change_dwi_b0_ui(b0_file,dwi_file):
    """
    """
    # Get input path and subject name
    b0_imgs_path = str(Path(b0_file).parents[0])
    dwi_imgs_path = str(Path(dwi_file).parents[0])
    #get subject name
#     subj_name =  str(Path(b0_file).name).split('_')[0] 
    
    # load images
    b0_imgs = load_img(b0_file)
    dwi_imgs = load_img(dwi_file)
    
    # Extract the first 2 volumes of b0 and DWI images
#     AP = index_img(b0_imgs,[0,1])
#     PA = index_img(dwi_imgs,[0,1])
    
    PA = index_img(b0_imgs,[0,1])
    AP = index_img(dwi_imgs,[0,1])
    
    # Save images as AP and PA. First 2 volumes of b0 are saved as AP 
    output_AP_fname = Path(b0_imgs_path,str(Path(dwi_file).name).replace('_dwi.nii.gz','_acq-dwib0_dir-AP_epi.nii.gz'))
    print("Saving AP image as %s"%output_AP_fname)
    AP.to_filename(output_AP_fname)
    
    # First 2 volumes of DWI are saved as PA
    output_PA_fname = Path(b0_imgs_path,str(Path(dwi_file).name).replace('_dwi.nii.gz','_acq-dwib0_dir-PA_epi.nii.gz'))
    print("Saving PA image as %s"%output_PA_fname)
    PA.to_filename(output_PA_fname)

    return AP, PA


def change_fmri(file):
    basedir = str(Path(file).parents[0])

    output_AP_fname = Path(basedir,str(Path(file).name).replace('_acq-GE_epi.nii.gz','_acq-fmrib0_dir-AP_epi.nii.gz'))
    output_PA_fname = Path(basedir,str(Path(file).name).replace('_acq-GE_epi.nii.gz','_acq-fmrib0_dir-PA_epi.nii.gz'))

    split_fname = os.path.join(basedir,'vol')
    print("Splitting the fieldmap")
    cmd = 'fslsplit %s %s'%(file,split_fname)
    os.system(cmd)

    print("Merging 2nd and 4rth volume as AP...")
    cmd = 'fslmerge -a %s %s %s'%(output_AP_fname,str(split_fname+'0001.nii.gz'),str(split_fname+'0003.nii.gz'))
    print(cmd)
    os.system(cmd)
    print("Merging the 1st and 3rd volume for PA")
    cmd = 'fslmerge -a %s %s %s'%(output_PA_fname,str(split_fname+'0000.nii.gz'),str(split_fname+'0002.nii.gz'))
    print(cmd)
    os.system(cmd)

    print("Swapping the dimension PA")
    cmd = 'fslswapdim %s %s %s %s %s'%(output_PA_fname,'x' ,'-y', 'z',output_PA_fname)
    print(cmd)
    os.system(cmd)

    PA = load_img(str(output_PA_fname))

    sform = PA.header.get_sform()
    qform = PA.header.get_qform()
    sform[1,:] *= -1
    qform[1,:] *= -1

    sform = ' '.join(str(v) for v in sform.flatten().tolist())
    qform = ' '.join(str(v) for v in qform.flatten().tolist())

    # nipype does not have fslorient command, so have to run it as a shell command!
    cmd = 'fslorient -setsform %s %s' %(sform,output_PA_fname)
    os.system(cmd)
    cmd = 'fslorient -setqform %s %s' %(qform,output_PA_fname)
    os.system(cmd)
    print(cmd)
    
def impute_intendedFor(json_filename, key, pos_key, value,save=True):
    """
    json_filename: filename of the json file
    key: Name of the key to be added to the json file
    pos_key: Name of the reference key where the new key is added. The new key is added just above this reference key
    value: Value of the key to be added
    save: Saves the json with the same filename as the original
    """
    f=open(json_filename,'r')
    json_data=json.load(f)
    if 'PhaseEncodingDirection' in json_data.keys():
        flag=True
    else:
        flag=False
    new_dict = OrderedDict()
    for k, v in json_data.items():
        if k==pos_key:
            new_dict[key] = value  # insert new key
            if flag==False:
                print("PhaseEncodingDirection added to %s"%json_filename)
                if 'AP' in str(Path(json_filename).name):
                    new_dict['PhaseEncodingDirection'] = "j-"  # insert new key
                else:
                    new_dict['PhaseEncodingDirection'] = "j"  # insert new key
        new_dict[k] = v
    if save:
        with open(json_filename, 'w') as data_file:
            json.dump(new_dict, data_file,indent=1)
    f.close()
    print("IntendedField added to %s"%json_filename)

def edit_json(data_path):
    dirs = Path(data_path)
    ignore='sourcedata' 
    # Accessing subject directory, removing hidden directory and sourcedata
    for d in dirs.iterdir():
        if d.is_dir() and ignore not in str(d) and '.heudiconv' not in str(d):
            sub_dir = str(d)
    # Getting session name
    sess_name = os.listdir(sub_dir)[0] # Assuming there is only a single session
    
    # Getting json and nifti files under dwi and func directories 
    json_files = glob.glob(os.path.join(sub_dir,sess_name,'fmap','*b0*.json'))
    dwi_json = sorted([i for i in json_files if 'dwi' in i])
    dwi_data = Path(glob.glob(os.path.join(sub_dir,sess_name,'dwi','*.nii.gz'))[0]).name # assuming simple case of 1 DWI data
    func_json = sorted([i for i in json_files if 'fmri' in i])
    func_data = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.nii.gz')))
    
    # Adding IntendedFor field in the json files for DWI data
    for i in dwi_json:
        value = [os.path.join(sess_name,'dwi',dwi_data)]
        impute_intendedFor(i, 'IntendedFor', 'InstitutionAddress', value,save=True)

    # Adding IntendedFor field in the json files for rest and cuff data
    for i in func_json:
        value = [os.path.join(sess_name,'func',str(Path(i).name)) for i in func_data]
        impute_intendedFor(i, 'IntendedFor', 'InstitutionAddress', value,save=True)


