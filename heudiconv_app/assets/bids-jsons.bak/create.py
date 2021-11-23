import json
import os
from glob import glob

keep_list = [
  "AcquisitionMatricPE",
  "BandwidthPerPixelPhaseEncode",
  "BaseResolution",
  "BodyPartExamined",
  "DeviceSerialNumber",
  "DwellTime",
  "EchoTime",
  "EchoTrainLength",
  "EffectiveEchoSpacing",
  "FlipAngle",
  "ImageOrientationPatientDICOM",
  "ImageType",
  "ImagingFrequency",
  "InPlanePhaseEncodingDirectionDICOM",
  "MRAcquisitionType",
  "MagneticFieldStrength",
  "Manufacturer",
  "ManufacturersModelName",
  "Modality",
  "MultibandAccelerationFactor",
  "PartialFourier",
  "PatientPosition",
  "PercentPhaseFOV",
  "PercentSampling",
  "PhaseEncodingDirection",
  "PhaseEncodingSteps",
  "PhaseResolution",
  "PixelBandwidth",
  "PixelSpacing",
  "PulseSequenceDetails",
  # "ReceiveCoilActiveElements",
  "ReceiveCoilName",
  "ReconMatrixPE",
  "RefLinesPE",
  "RepetitionTime",
  "ScanOptions",
  "ScanningSequence",
  "SequenceName",
  "SequenceVariant",
  # "ShimSetting",
  "SliceThickness",
  "SliceTiming",
  "SoftwareVersions",
  "SpacingBetweenSlices",
  "TotalReadoutTime",
  "dcmmeta_affine",
  "dcmmeta_reorient_transform",
  "dcmmeta_shape"
  "dcmmeta_slice_dim",
  "dcmmeta_version"]

root = os.path.join("/home/psadil/Documents/git/a2cps/mri_imaging_pipeline/heudiconv_app/assets")
bak = os.path.join(root, "bids-jsons.bak")
out = os.path.join(root, "bids-jsons")

jsons = glob(os.path.join(bak, "*json"))


for j in jsons:
  with open(j, "r") as f:
    data = json.load(f)
    json_out = {k:v for (k,v) in data.items() if k in keep_list}
    if json_out.__contains__('dcmmeta_affine'):
      # print(json_out.get('dcmmeta_affine'))
      affine = json_out.get('dcmmeta_affine')
      for i,row in enumerate(affine):
        json_out['dcmmeta_affine'][i] = row[0:-1]
    with open(os.path.join(out, os.path.basename(f.name)), 'w', encoding="utf-8") as file:
      json.dump(json_out, file, indent=1)

