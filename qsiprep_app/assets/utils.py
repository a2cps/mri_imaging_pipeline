import os,glob,json
from pathlib import Path
from nilearn.image import load_img,index_img
import pandas as pd
from collections import OrderedDict


def add_session_to_json(json_filename, value):
    """
    Adds session number to the bids json file so that it
    can filter and process a specific session.

    json_filename: bids filter file in json format
    value: Session to be added
    """
    json_data = load_json(json_filename)
    new_dict = OrderedDict()
    json_data['t1w']['session']=value.split('-')[1]
    json_data['dwi']['session']=value.split('-')[1]
    # sort the dictionary
    new_dict = OrderedDict(sorted(json_data.items(), key=lambda t: t[0]))
    save_as_json(new_dict,json_filename)
    return json_filename

def load_json(json_filename):
    f = open(json_filename,'r')
    json_data = json.load(f)
    return json_data

def save_as_json(data,json_filename):
    with open(json_filename, 'w') as data_file:
         json.dump(data, data_file,indent=4)

def get_b0_index(df,bval_value):
    ind = df.index[df['bvals'] == bval_value].tolist()
    return ind

def split_shells(basepath,subject_id,session):
    """
    Computes the DWI measures like FA,RD,MD etc using Kodi's processing
    pipeline.
    basepath: path where outputs from qsiprep is saved
    subject_id: subject id of the participant
    session: session of the participant.
    """
    basepath = os.path.join(basepath,'qsiprep')
    subject_id = 'sub-'+str(subject_id)
    if os.path.exists(os.path.join(basepath,subject_id,session,'dti-metrics')):
        pass
    else:
        os.mkdir(os.path.join(basepath,subject_id,session,'dti-metrics'))
    resultpath=os.path.join(basepath,subject_id,session,'dti-metrics')
    # Find the filepaths of dwi dataset
    bval_filepath = glob.glob(os.path.join(basepath,subject_id,session,'dwi','*T1w_desc-preproc_dwi.bval'))[0]
    dwi_filepath = glob.glob(os.path.join(basepath,subject_id,session,'dwi','*T1w_desc-preproc_dwi.nii.gz'))[0]
    bvec_filepath = glob.glob(os.path.join(basepath,subject_id,session,'dwi','*T1w_desc-preproc_dwi.bvec'))[0]
    mask_file = glob.glob(os.path.join(basepath,subject_id,session,'dwi','*mask.nii.gz'))[0]
    # Extract the base filename; useful when saving the results
    base_fname = str(Path(bval_filepath).name).split('.')[0]

    # Read the processed bval and bvec files
    bval_file = pd.read_table(bval_filepath,header=None)
    bval_file.columns=['bvals']
    bvec_file = pd.read_csv(bvec_filepath,header=None,sep=' ')
    bvec_file = bvec_file.T
    dwi_data = load_img(dwi_filepath)

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
    f_3000 = os.path.join(resultpath,base_fname+'_2nd_shell.nii.gz')
    f_2000 = os.path.join(resultpath,base_fname+'_3rd_shell.nii.gz')
    f_1000 = os.path.join(resultpath,base_fname+'_4rth_shell.nii.gz')
    f_500 = os.path.join(resultpath,base_fname+'_5th_shell.nii.gz')

    dwi_data_3000.to_filename(f_3000)
    dwi_data_2000.to_filename(f_2000)
    dwi_data_1000.to_filename(f_1000)
    dwi_data_500.to_filename(f_500)

    bval_3000.to_csv(os.path.join(resultpath,base_fname+'_2nd_shell.bval'),header=None, index=None)
    bval_2000.to_csv(os.path.join(resultpath,base_fname+'_3rd_shell.bval'),header=None, index=None)
    bval_1000.to_csv(os.path.join(resultpath,base_fname+'_4rth_shell.bval'),header=None, index=None)
    bval_500.to_csv(os.path.join(resultpath,base_fname+'_5th_shell.bval'),header=None, index=None)

    bvec_3000.to_csv(os.path.join(resultpath,base_fname+'_2nd_shell.bvec'),header=None, index=None,sep=' ')
    bvec_2000.to_csv(os.path.join(resultpath,base_fname+'_3rd_shell.bvec'),header=None, index=None,sep=' ')
    bvec_1000.to_csv(os.path.join(resultpath,base_fname+'_4rth_shell.bvec'),header=None, index=None,sep=' ')
    bvec_500.to_csv(os.path.join(resultpath,base_fname+'_5th_shell.bvec'),header=None, index=None,sep=' ')
    return f_3000,f_1000,f_2000,f_500,mask_file
