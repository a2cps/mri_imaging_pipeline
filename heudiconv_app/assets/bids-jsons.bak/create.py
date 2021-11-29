import json
import os
import re
from glob import glob

import pandas as pd
import numpy as np

keep_list = [
  "AcquisitionMatricPE",
  "BandwidthPerPixelPhaseEncode",
  "BaseResolution",
  "BodyPartExamined",
  "CoilCombinationMethod",
  "ConsistencyInfo",
  "DeviceSerialNumber",
  "DiffusionScheme",
  "DwellTime",
  "EchoTime",
  "EchoTrainLength",
  "EffectiveEchoSpacing",
  "FlipAngle",
  "ImageOrientationPatientDICOM",
  "ImageType",
  "ImagingFrequency",
  "InPlanePhaseEncodingDirectionDICOM",
  "InversionTime",
  "MatrixCoilMode",
  "MRAcquisitionType",
  "MagneticFieldStrength",
  "Manufacturer",
  "ManufacturersModelName",
  "Modality",
  "MultibandAccelerationFactor",
  "NumberOfArms",
  "NumberOfExcitations",
  "NumberOfPointsPerArm",
  "ParallelAcquisitionTechnique",
  "ParallelReductionFactorInPlane",
  "ParallelReductionOutOfPlane"
  "PartialFourier",
  "PartialFourierDirection",
  "PartialFourierEnabled",
  "PatientPosition",
  "PercentPhaseFOV",
  "PercentSampling",
  "PhaseEncodingAxis",
  "PhaseEncodingDirection",
  "PhaseEncodingPolarityGE",
  "PhaseEncodingSteps",
  "PhaseEncodingStepsNoPartialFourier",
  "PhaseResolution",
  "PixelBandwidth",
  "PixelSpacing",
  "PulseSequenceDetails",
  "ReceiveCoilName",
  "ReconMatrixPE",
  "RefLinesPE",
  "RepetitionTime",
  "ScanOptions",
  "ScanningSequence",
  "SequenceName",
  "SequenceVariant",
  "SliceThickness",
  "SliceTiming",
  "SoftwareVersions",
  "SpacingBetweenSlices",
  "SpoilingState",
  # "TxRefAmp",
  "TotalReadoutTime",
  "VendorReportedEchoSpacing",
  "WaterFatShift",
  "dcmmeta_affine",
  "dcmmeta_reorient_transform",
  "dcmmeta_shape"
  "dcmmeta_slice_dim",
  "dcmmeta_version"]

root = os.path.join("/home/psadil/Documents/git/a2cps/mri_imaging_pipeline/heudiconv_app/assets")
bak = os.path.join(root, "bids-jsons")

jsons = glob(os.path.join(bak, "*json"))

d_list = []
for j in jsons:
  with open(j, "r") as f:
    data = json.load(f)
    json_out = {k:v for (k,v) in data.items() if k in keep_list}
    if json_out.__contains__('dcmmeta_affine'):
      # print(json_out.get('dcmmeta_affine'))
      affine = json_out.get('dcmmeta_affine')
      for i,row in enumerate(affine):
        json_out['dcmmeta_affine'][i] = row[0:-1]
    d = pd.json_normalize(json_out)
    scanner = re.findall('site-([A-Z]{2,3}[12]?)', j)[0]
    d['scanner'] = scanner
    d['source'] = 'bids_json'
    suffix = re.findall('_(dwi|bold|T1w|epi)\.', j)[0]
    d['suffix'] = suffix
    if suffix == 'bold':
      d['task'] = re.findall('task-(rest|cuff)', j)[0]
    elif suffix == 'epi':
      d['acq'] = re.findall('acq-(dwib0|fmrib0)', j)[0]
    elif suffix == 'dwi':
      d['bval'] = [np.genfromtxt(f'site-{scanner}_dwi.bval').tolist()]
      d['bvec'] = [np.genfromtxt(f'site-{scanner}_dwi.bvec').tolist()]

    d_list.append(d)     
    # with open(os.path.join(out, os.path.basename(f.name)), 'w', encoding="utf-8") as file:
    #   json.dump(json_out, file, indent=1)

dd = (pd.concat(d_list)
  .set_index(['suffix','scanner','task', 'acq'])
  .sort_index()
)
dd.to_csv(os.path.join(root, 'acq-params.tsv'), sep="\t")
