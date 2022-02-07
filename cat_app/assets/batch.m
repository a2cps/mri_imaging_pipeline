% Batch file for CAT12 segmentation, mean GM ROI extraction to csv,
% TIV & tissue volume extraction for SPM12 standalone installation
%
% ----> CREATE INDIVIDUAL OUTPUT FOLDER BEFORE <----
%
%  input:
%  <*T1w.nii.gz>
%_______________________________________________________________________
% $Id: cat_standalone_batch.txt 1720 23-Sep-2020 22:55:58 fhoffstaedter $
%------------------------------------------------------------------OUTPUTDIR-----

% Used CAT12 version r1720

% INPUT FILE
matlabbatch{1}.spm.tools.cat.estwrite.data(1) = '<UNDEFINED>';
matlabbatch{1}.spm.tools.cat.estwrite.nproc = '<UNDEFINED>';
