import sys,glob,os
from pathlib import Path
from utils import split_shells
try:
    inputfile = sys.argv[1]
    subject_id = sys.argv[2]
    ses = sys.argv[3]
    print("Computing DWI measures for %s ... "%inputfile)
    # Split shells, f_3000 -> 2nd shell, f_2000 -> 3rd shell, f_1000 -> 4rth shell, f_500 -> 5th shell
    f_3000,f_2000,f_1000,f_500,mask_name= split_shells(inputfile,subject_id,ses)

    basepath = str(Path(f_3000).parents[0])
    fname = str(Path(f_3000).stem)
    bvecs_3000 = glob.glob(os.path.join(basepath,'*T1w_desc-preproc_dwi_2nd_shell.bvec'))[0]
    bvals_3000 = glob.glob(os.path.join(basepath,'*T1w_desc-preproc_dwi_2nd_shell.bval'))[0]
    #mask_name = glob.glob(os.path.join(basepath,'*mask.nii.gz'))[0]
    print(mask_name)
    #mask_name = os.path.join(basepath,fname+'_mask.nii.gz')
    output_basename = os.path.join(basepath,'sub-'+subject_id+'_'+ses+'_2nd_shell_dwi_measures')
    #cmd = 'bet %s %s' %(f_3000,mask_name)
    #print(cmd) # for ipython use !echo {cmd}
    #os.system(cmd) # for ipython use !{cmd}

    cmd = 'dtifit -k %s -o %s -m %s -r %s -b %s' %(f_3000,output_basename,mask_name,bvecs_3000,bvals_3000)
    print(cmd) # for ipython use !echo {cmd}
    os.system(cmd) # for ipython use !{cmd}
except:
    raise ValueError("Please specify the full path of the qsiprep output")
