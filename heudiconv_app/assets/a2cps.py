# Provide mapping into reproin heuristic names
import pydicom

from heudiconv.heuristics import reproin

from heudiconv.heuristics.reproin import *

protocols2fix.update(
    {
        "": [
            # regular expression, what to replace with
            # At the start of data collection, repeated scans were marked _R#
            # (e.g., T1_MPRAGE_R1 is the first repeat of T1).
            # for any scan that has a repeat suffix (e.g., _R2), strip the suffix
            # this lets them be marked as duplicates, which can then be deleted after heudiconv
            # (they'll end with a suffix _dup)
            (r"(.*)([_\s]R[1-9]*)$", r"\1"),
            ("AAHead_Scout_.*", "anat-scout"),
            ("^dti_.*", "dwi"),
            ("^space_top_distortion_corr.*_([ap]+)_([12])", r"fmap-epi_dir-\1_run-\2"),
            # I do not think there is a point in keeping any
            # of _ap _32ch _mb8 in the output filename, although
            # could be brought into _acq- if very much desired OR
            # there are some subjects/sessions scanned differently
            ("^(.+)_ap.*_r(0[0-9])", r"func_task-\1_run-\2"),
            # also the same as above...
            ("^t1w_.*", "anat-T1w"),
            # below are my guesses based on what I saw in README
            ("_r(0[0-9])", r"_run-\1"),
            ("self_other", "selfother"),
            # For  a2dtn01  on tacc -- based on the wrong field
            # ('^ssfse', 'anat-scout'),
            # ('^research/ABCD/mprage_promo', 'anat-T1w'),
            # ('^research/ABCD/muxepi2', 'dwi'),
            # ('^research/ABCD/epi_pepolar', 'fmap-epi_run-1'),
            # ('^research/ABCD/muxepi$', 'func_task-unk_run-unk'),
            ("^3Plane_Loc.*", "anat-scout"),
            (r"^(T1[_\s])*MPRAGE", "anat-T1w"),
            ("^GE_EPI_B0_(AP|PA)", r"fmap-epi_acq-fmrib0_dir-\1"),
            ("^GE_EPI_B0", "fmap-epi_acq-fmrib0"),
            ("^SE_EPI_B0_(AP|PA)", r"fmap-epi_acq-dwib0_dir-\1"),
            ("^SE_EPI_B0", "fmap-epi_acq-dwib0"),
            # new rules for new B0 names
            ("^[fF]MRI_B0_(AP|PA)", r"fmap-epi_acq-fmrib0_dir-\1"),
            ("^[fF]MRI_B0", "fmap-epi_acq-fmrib0"),
            ("^DWI_B0_(AP|PA)", r"fmap-epi_acq-dwib0_dir-\1"),
            ("^DWI_B0", "fmap-epi_acq-dwib0"),
            # additional variants to support ABCD naming (dMRI_distortionmap_AP/PA and fMRI_distortionmap_AP/PA)
            ("^fMRI_distortionmap_(AP|PA)", r"fmap-epi_acq-fmrib0_dir-\1"),
            ("^fMRI_distorionmap", "fmap-epi_acq-fmrib0"),
            ("^dMRI_distortionmap_(AP|PA)", r"fmap-epi_acq-dwib0_dir-\1"),
            ("^dMRI_distortionmap", "fmap-epi_acq-dwib0"),
            # the next few refer to variations on names provided by second
            # UM scanner
            ("^ORIG: DTI$", "dwi"),
            ("^ORIG: DWI$", "dwi"),
            ("^REV_POL: DTI$", "fmap-epi_acq-dwib0"),
            ("^REV_POL: DWI$", "fmap-epi_acq-dwib0"),
            ("^ORIG T1_MPRAGE$", "anat-T1w"),
            # this rule must come *after* DWI_B0
            ("^DWI", "dwi"),
            (r"^REST([12])([_\s]R[1-9]*)*$", r"func_task-rest_run-\1"),
            (r"^Rest([12])([_\s]R[1-9]*)*$", r"func_task-rest_run-\1"),
            (r"^CUFF([12])([_\s]R[1-9]*)*$", r"func_task-cuff_run-\1"),
            (r"^Cuff([12])([_\s]R[1-9]*)*$", r"func_task-cuff_run-\1"),
            # phantom scan heuristics
            # anat should grab one that has ORIG
            (".*(anat-T1w)[-_]acq[-_]GRE$", r"\1"),
            # also expect ORIG in some DWI (and sometimes also a suffix )
            (".*(b[12]000).*", r"dwi-dwi_acq-\1"),
            ("func[-_]bold[-_]acq[-_]QA", "func_task-rest"),
            # WS/UI had some atypical names early on
            ("REST1_17DSV", "func_task-rest"),
            ("^Ax.*GRE.*", "anat-T1w"),
            ("^fMRI QA$", "func_task-rest"),
            ("^ORIG DWI ([12]000)$", r"dwi-dwi_acq-b\1"),
            # UM (ABCD) phantom heuristics
            ("ORIG: MB_Diffusion_QA", "dwi"),  # b3000
            ("MB_fMRI_QA", "func_task-rest_acq-mb"),
            ("Standard_fBIRN_QA", "func_task-rest_acq-fBIRN"),
            ("Coil_QA", "anat-T1w"),
            # after UM1 was upgraded, they stopped using typical A2CPS rules for some scans
            ("t1spgr_208sl", "anat-T1w"),
            # after SH upgrade
            ("Tra T1 MPRAGE orthog", "anat-T1w"),
            ("^T1_MPRAGE_ND$", "anat-T1w"),
        ],
    }
)


def filter_dicom(dcmdata: pydicom.Dataset) -> bool:
    """Return True if a DICOM dataset should be filtered out, else False"""
    exclude = False
    if dcmdata.SeriesDescription == "<MPR Collection>":
        exclude = True
    # participants from second scanner at UM
    # "The way the extra volume is collected, distortion correction has to be
    # turned on.  This means that the series 3 DTI has GE's distortion
    # correction applied already, while series 310 is the original DTI data.
    # To match what is acquired on other scanners, you probably want the B0
    # volume (series 311) and the original DTI data (series 312 [sic: 310]).
    # Unfortunately, that means you also get series 3, which you probably don't
    # want."
    # For T1w, we get both a modified "T1_MPRAGE" and "ORIG T1_MPRAGE". This
    # prevents the modifed one from going through conversion
    elif (
        dcmdata.__contains__("DeviceSerialNumber")
        and dcmdata.DeviceSerialNumber == "0007347633TMRFIX"
        and (
            dcmdata.SeriesDescription == "DTI"
            or dcmdata.SeriesDescription == "DWI"
            or dcmdata.SeriesDescription == "T1_MPRAGE"
        )
    ):
        exclude = True
    # similar issue for UI phantom scans
    elif (
        dcmdata.__contains__("DeviceSerialNumber")
        and dcmdata.DeviceSerialNumber == "000000312996MR3T"
        and (
            dcmdata.SeriesDescription in ["dwi-dwi_acq-b1000", "dwi-dwi_acq-b2000"]
            or dcmdata.SeriesDescription == "anat-T1w_acq-GRE"
        )
    ):
        exclude = True
    elif "QA_4.1.21" in dcmdata.ProtocolName and (
        dcmdata.SeriesDescription == "DWI 2000"
        or dcmdata.SeriesDescription == "DWI 1000"
    ):
        # there is an ORIG DWI [12]000 that must be picked up, but not these
        exclude = True
    # SH20146V1 was sent with with a set of derived T1w images that included the flag "MPR"
    # in the ImageType field, presumably indicing "multi-plane reconstruction". We don't want
    # these derived images in the bids dataset
    #
    # at least some UC files that are carried along with the zip do not have the ImageType field,
    # so we have to check for it's existence
    elif dcmdata.__contains__("ImageType") and "MPR" in dcmdata.ImageType:
        exclude = True
    # SH sends derived dwi phantom scans. the following excludes those
    elif any(suffix in dcmdata.SeriesDescription for suffix in ["ADC", "TRACE"]):
        exclude = True

    # after the SH upgrade, (i.e., software "syngo MR XA30"), SH sends the raw anatomical as
    # T1_MPRAGE_ND ("No Distorction Correction"), but also always a derived scan called T1_MPRAGE
    elif (
        dcmdata.__contains__("DeviceSerialNumber")
        and dcmdata.DeviceSerialNumber == "66022"
        and dcmdata.SoftwareVersions == "syngo MR XA30"
        and (dcmdata.SeriesDescription == "T1_MPRAGE")
    ):
        exclude = True

    return exclude
