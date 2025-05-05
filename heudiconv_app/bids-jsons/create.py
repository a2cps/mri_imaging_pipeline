import json
import os
import re
import typing
from glob import glob

import numpy as np
import pandas as pd

keep_list = [
    "AcquisitionMatricPE",
    "BandwidthPerPixelPhaseEncode",
    "BaseResolution",
    # "BodyPartExamined",
    "CoilCombinationMethod",
    "CoilString",
    "ConsistencyInfo",
    "DeviceSerialNumber",
    "DiffGradientCyclingGE",
    "DiffusionScheme",
    "DwellTime",
    "EchoTime",
    "EchoTrainLength",
    "EffectiveEchoSpacing",
    "FlipAngle",
    "FrequencyEncodingSteps",
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
    "MultibandAccelerationFactor",
    "NonlinearGradientCorrection",
    "NumberOfDiffusionT2GE",
    "NumberOfArms",
    "NumberOfDiffusionDirectionGE",
    "NumberOfExcitations",
    "NumberOfPointsPerArm",
    "ParallelAcquisitionTechnique",
    "ParallelReductionFactorInPlane",
    "ParallelReductionOutOfPlane",
    "PartialFourier",
    "PartialFourierDirection",
    "PartialFourierEnabled",
    "PercentPhaseFOV",
    "PercentSampling",
    "PhaseEncodingAxis",
    "PhaseEncodingDirection",
    "PhaseEncodingPolarityGE",
    "PhaseEncodingSteps",
    "PhaseEncodingStepsNoPartialFourier",
    "PhaseEncodingStepsOutOfPlane",
    "PhaseResolution",
    "PixelBandwidth",
    "PixelSpacing",
    # "PrescanReuseString", # redundant with ShimSetting
    # "ProcedureStepDescription", # varies at SH, deemed unimportant (email exchange)
    "PulseSequenceDetails",
    "PulseSequenceName",
    "ReceiveCoilActiveElements",
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
    "TensorFileNumberGE",
    # "SpoilingState",
    # "TxRefAmp",
    "TotalReadoutTime",
    "VendorReportedEchoSpacing",
    "WaterFatShift",
    "dcmmeta_affine",
    "dcmmeta_reorient_transform",
    "dcmmeta_shape",
    "dcmmeta_slice_dim",
    "dcmmeta_version",
]

root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
bak = os.path.join(root, "bids-jsons")

jsons = glob(os.path.join(bak, "*json"))

d_list = []
for j in jsons:
    with open(j, "r") as f:
        data: dict[str, typing.Any] = json.load(f)
        json_out = {k: v for (k, v) in data.items() if k in keep_list}
        if (affine := json_out.get("dcmmeta_affine")) is not None:
            for i, row in enumerate(affine):
                json_out["dcmmeta_affine"][i] = row[0:-1]
        d = pd.json_normalize(json_out)
        device_serial_number = json_out.get("DeviceSerialNumber")

        if not isinstance(device_serial_number, str):
            raise ValueError("No Device Serial Number?")

        phantom = len(re.findall("phantom_", j)) > 0
        d["phantom"] = phantom
        suffix = re.findall(r"_(dwi|bold|T1w|epi)\.", j)[0]
        d["suffix"] = suffix
        if suffix == "bold":
            if acq := re.findall("(?<=acq-)[a-zA-Z]+", j):
                d["acq"] = acq[0]
            d["task"] = re.findall("task-(rest|cuff)", j)[0]
        elif suffix == "epi":
            d["acq"] = re.findall("acq-(dwib0|fmrib0)", j)[0]
            d["dir"] = re.findall("(?<=dir-)(AP|PA)", j)[0]
        elif suffix == "dwi":
            if phantom and (not device_serial_number == "0007347633TMRFIX"):
                acq = re.findall("acq-(b1000|b2000)", j)[0]
                d["acq"] = acq
                d["bval"] = [
                    np.genfromtxt(
                        f"serial-{device_serial_number}phantom_acq-{acq}_dwi.bval"
                    ).tolist()
                ]
                d["bvec"] = [
                    np.genfromtxt(
                        f"serial-{device_serial_number}phantom_acq-{acq}_dwi.bvec"
                    ).tolist()
                ]
            elif phantom and device_serial_number == "0007347633TMRFIX":
                d["bval"] = [
                    np.genfromtxt(
                        f"serial-{device_serial_number}phantom_dwi.bval"
                    ).tolist()
                ]
                d["bvec"] = [
                    np.genfromtxt(
                        f"serial-{device_serial_number}phantom_dwi.bvec"
                    ).tolist()
                ]

            else:
                d["bval"] = [
                    np.genfromtxt(f"serial-{device_serial_number}_dwi.bval").tolist()
                ]
                d["bvec"] = [
                    np.genfromtxt(f"serial-{device_serial_number}_dwi.bvec").tolist()
                ]

        # parameters stored deeper in the file
        if (data_global := data.get("global")) is not None:
            d["BitsStored"] = data_global.get("const").get("BitsStored")

        # parameters that follow a set whitelist
        # note that WS stores this information in "CoilString" and so does not need to be included
        # in this check
        if device_serial_number in ["70032", "66022", "166295"]:
            d["ReceiveCoilActiveElements"] = [
                [
                    "HC1-6",
                    "HC3-6",
                    "HC1-7",
                    "HC1-7;NC1",
                    "HC1-7;NC1,2",
                    "HC1-7;NC2;SP1",
                    "HC3-7;NC1",
                    "HEA;HEP",
                    "HC1,3-7;NC1",
                ]
            ]

        d_list.append(d)

dd = (
    pd.concat(d_list)
    .set_index(["suffix", "DeviceSerialNumber", "task", "acq"])
    .sort_index()
)
dd.to_csv(os.path.join(root, "assets", "acq-params.tsv"), sep="\t")
