import os,json,glob
from pathlib import Path
from nilearn.image import load_img,index_img
from collections import OrderedDict

def drop_dwi_vols(dwi_file):
    dwi_imgs = load_img(dwi_file)
    dwi_data = index_img(dwi_imgs,range(2,dwi_imgs.shape[-1]))
    print("Saving dwi image...")
    dwi_data.to_filename(dwi_file)

def create_fieldmaps_dwi(b0_file,dwi_file):
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
    AP = index_img(dwi_imgs,[0,-1])

    # Save images as AP and PA. First 2 volumes of b0 are saved as AP 
    output_AP_fname = Path(b0_imgs_path,str(Path(dwi_file).name).replace('_dwi.nii.gz','_B0_dir_AP_dwi.nii.gz'))
    print("Saving AP image as %s"%output_AP_fname)
    AP.to_filename(output_AP_fname)

    # First  and last volumes of DWI are saved as PA
    output_PA_fname = Path(b0_imgs_path,str(Path(dwi_file).name).replace('_dwi.nii.gz','_B0_dir_PA_dwi.nii.gz'))
    print("Saving PA image as %s"%output_PA_fname)
    PA.to_filename(output_PA_fname)

    return AP, PA

def add_fields_to_json(json_data, key, pos_key, value):
    """
    json_data: json data in the form of dictionary
    key: Name of the key to be added to the json file
    pos_key: Name of the reference key where the new key is added. The new key is added just above this reference key
    value: Value of the key to be added
    """

    new_dict = OrderedDict()
    for k, v in json_data.items():
        if k==pos_key:
            new_dict[key] = value  # insert new key
        new_dict[k] = v
    return new_dict

def save_as_json(data,json_filename):
    with open(json_filename, 'w') as data_file:
         json.dump(data, data_file,indent=1)
  
def edit_json(data_path):
    dirs = Path(data_path)
    ignore='sourcedata' 
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
    print(dwi_json_file)
    dwi_b0_json = sorted([i for i in json_files if 'dwi' in i])
    dwi_data = Path(glob.glob(os.path.join(sub_dir,sess_name,'dwi','*.nii.gz'))[0]).name # assuming simple case of 1 DWI data
    func_b0_json = sorted([i for i in json_files if 'fmri' in i])
    func_json = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.json')))
    func_data = sorted(glob.glob(os.path.join(sub_dir,sess_name,'func','*.nii.gz')))
    
    # Adding IntendedFor field in the b0 json files for DWI data
    for i in dwi_b0_json:
        f=open(i,'r')
        json_data=json.load(f)
        if 'PhaseEncodingDirection' in json_data.keys():
            philips_scanner=False
        else:
            philips_scanner=True
            if 'AP' in str(Path(i).name):
                 value = "j-"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)
            else:
                 value="j"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)
            print("PhaseEncodingDirection is added to %s"%i)

        value = [os.path.join(sess_name,'dwi',dwi_data)]
        updated_json = add_fields_to_json(json_data, 'IntendedFor', 'InstitutionAddress', value)
        save_as_json(updated_json,i)
        print("IntendedField is added to %s"%i)
        f.close()
    
    for i in dwi_json_file:
        print(i)
        f = open(i,'r')
        json_data=json.load(f)
        value = "j"
        json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)
        print("PhaseEncodingDirection is added to %s"%i)
        save_as_json(updated_json,i)
        f.close()
    # Adding IntendedFor field in the json files for rest and cuff data and sliceTiming and PhaseEncodingDirection for Philips
    for i in func_b0_json:
        f=open(i,'r')
        json_data=json.load(f)
        
        # Adds sliceTiming and PhaseEncodingDirection for Philips scanner
        if 'PhaseEncodingDirection' in json_data.keys(): 
            philips_scanner=False
        else:
            philips_scanner=True
        # Adds PhaseEncodingDirection in the json files for Philips scanner
            if 'AP' in str(Path(i).name):
                 value = "j-"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)
            else:
                 value="j"
                 json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)
            print("PhaseEncodingDirection is added to %s"%i)
            
        # Adds IntendedFor in the json files regardless of any scanner
        value = [os.path.join(sess_name,'func',str(Path(i).name)) for i in func_data]
        updated_json = add_fields_to_json(json_data, 'IntendedFor', 'InstitutionAddress', value)
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
           json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)
           #else:
           #      value="j"
           #      json_data = add_fields_to_json(json_data, 'PhaseEncodingDirection', 'InstitutionAddress', value)

           print("PhaseEncodingDirection is added to %s"%i)
            # Adds sliceTiming for Philips scanner
           updated_json = add_fields_to_json(json_data, 'SliceTiming', 'SoftwareVersions', slice_timing)
           print("SliceTiming is added to %s"%i)
           save_as_json(updated_json,i)
           f.close()


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
    
 

