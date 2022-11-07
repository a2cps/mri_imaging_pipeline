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
    # "BodyPartExamined",
    # "CoilCombinationMethod",
    "CoilString",
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
    # "MatrixCoilMode",
    "MRAcquisitionType",
    "MagneticFieldStrength",
    "Manufacturer",
    "ManufacturersModelName",
    "MultibandAccelerationFactor",
    # "NumberOfArms",
    # "NumberOfExcitations",
    # "NumberOfPointsPerArm",
    # "ParallelAcquisitionTechnique",
    # "ParallelReductionFactorInPlane",
    # "ParallelReductionOutOfPlane"
    "PartialFourier",
    # "PartialFourierDirection",
    "PartialFourierEnabled",
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
        data = json.load(f)
        json_out = {k: v for (k, v) in data.items() if k in keep_list}
        if json_out.__contains__("dcmmeta_affine"):
            # print(json_out.get('dcmmeta_affine'))
            affine = json_out.get("dcmmeta_affine")
            for i, row in enumerate(affine):
                json_out["dcmmeta_affine"][i] = row[0:-1]
        d = pd.json_normalize(json_out)
        scanner = re.findall("site-(NS|SH|WS|UM1|UM2|UI|UC)", j)[0]
        d["scanner"] = scanner
        phantom = len(re.findall("phantom_", j)) > 0
        d["phantom"] = phantom
        suffix = re.findall("_(dwi|bold|T1w|epi)\.", j)[0]
        d["suffix"] = suffix
        if suffix == "bold":
            if acq := re.findall("(?<=acq-)[a-zA-Z]+", j):
                d["acq"] = acq[0]
            d["task"] = re.findall("task-(rest|cuff)", j)[0]
        elif suffix == "epi":
            d["acq"] = re.findall("acq-(dwib0|fmrib0)", j)[0]
            d["dir"] = re.findall("(?<=dir-)(AP|PA)", j)[0]
        elif suffix == "dwi":
            if phantom and (not scanner == "UM2"):
                acq = re.findall("acq-(b1000|b2000)", j)[0]
                d["acq"] = acq
                d["bval"] = [
                    np.genfromtxt(f"site-{scanner}phantom_acq-{acq}_dwi.bval").tolist()
                ]
                d["bvec"] = [
                    np.genfromtxt(f"site-{scanner}phantom_acq-{acq}_dwi.bvec").tolist()
                ]
            elif phantom and scanner == "UM2":
                d["bval"] = [np.genfromtxt(f"site-{scanner}phantom_dwi.bval").tolist()]
                d["bvec"] = [np.genfromtxt(f"site-{scanner}phantom_dwi.bvec").tolist()]

            else:
                d["bval"] = [np.genfromtxt(f"site-{scanner}_dwi.bval").tolist()]
                d["bvec"] = [np.genfromtxt(f"site-{scanner}_dwi.bvec").tolist()]

        # parameters stored deeper in the file
        if data.__contains__("global"):
            d["BitsStored"] = data.get("global").get("const").get("BitsStored")

        # parameters that follow a set whitelist
        # note that WS stores this information in "CoilString" and so does not need to be included
        # in this check
        if scanner in ["NS", "SH"]:
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

dd = pd.concat(d_list).set_index(["suffix", "scanner", "task", "acq"]).sort_index()
dd.to_csv(os.path.join(root, "assets", "acq-params.tsv"), sep="\t")
