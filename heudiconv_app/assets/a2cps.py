# Provide mapping into reproin heuristic names

from heudiconv.heuristics import reproin

from heudiconv.heuristics.reproin import *

protocols2fix.update({
    '':  # for any study given.  Needs recent heudiconv
        [
            # All those come untested!
            # regular expression, what to replace with
            ('AAHead_Scout_.*', 'anat-scout'),
            ('^dti_.*', 'dwi'),
            ('^space_top_distortion_corr.*_([ap]+)_([12])', r'fmap-epi_dir-\1_run-\2'),
            # I do not think there is a point in keeping any
            # of _ap _32ch _mb8 in the output filename, although
            # could be brought into _acq- if very much desired OR
            # there are some subjects/sessions scanned differently
            ('^(.+)_ap.*_r(0[0-9])', r'func_task-\1_run-\2'),
            # also the same as above...
            ('^t1w_.*', 'anat-T1w'),
            # below are my guesses based on what I saw in README
            ('_r(0[0-9])', r'_run-\1'),
            ('self_other', 'selfother'),

            # For  a2dtn01  on tacc -- based on the wrong field
            #('^ssfse', 'anat-scout'),
            #('^research/ABCD/mprage_promo', 'anat-T1w'),
            #('^research/ABCD/muxepi2', 'dwi'),
            #('^research/ABCD/epi_pepolar', 'fmap-epi_run-1'),  
            #('^research/ABCD/muxepi$', 'func_task-unk_run-unk'), 
            ('^3Plane_Loc.*', 'anat-scout'),
            ('^T1_MPRAGE_R([1-9])', 'anat-T1w'),
            ('^T1_MPRAGE', 'anat-T1w'),
            ('^GE_EPI_B0_(AP|PA)', r'fmap-epi_acq-fmrib0_dir-\1'),
            ('^GE_EPI_B0', 'fmap-epi_acq-fmrib0'),  
            ('^SE_EPI_B0_(AP|PA)', r'fmap-epi_acq-dwib0_dir-\1'),
            ('^SE_EPI_B0', 'fmap-epi_acq-dwib0'),  
            # new rules for new B0 names
            ('^[fF]MRI_B0_(AP|PA)', r'fmap-epi_acq-fmrib0_dir-\1'),    
            ('^[fF]MRI_B0', 'fmap-epi_acq-fmrib0'),     
            ('^DWI_B0_(AP|PA)', r'fmap-epi_acq-dwib0_dir-\1'),   
            ('^DWI_B0', 'fmap-epi_acq-dwib0'),
            # additional variants to support ABCD naming (dMRI_distortionmap_AP/PA and fMRI_distortionmap_AP/PA)
            ('^fMRI_distortionmap_(AP|PA)', r'fmap-epi_acq-fmrib0_dir-\1'),    
            ('^fMRI_distorionmap', 'fmap-epi_acq-fmrib0'),     
            ('^dMRI_distortionmap_(AP|PA)', r'fmap-epi_acq-dwib0_dir-\1'),   
            ('^dMRI_distortionmap', 'fmap-epi_acq-dwib0'),
            # this rule must come *after* DWI_B0
            ('^DWI', 'dwi'),
            ('^REST([12])$', r'func_task-rest_run-\1'),
            ('^Rest([12])$', r'func_task-rest_run-\1'),
            ('^CUFF([12])$', r'func_task-cuff_run-\1'), 
            ('^Cuff([12])$', r'func_task-cuff_run-\1'), 
        ],
})
