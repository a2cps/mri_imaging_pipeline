FROM nipreps/fmriprep:20.2.3

ADD opt /opt/freesurfer_license
ENV FREESUFERHOME /opt/freesurfer_license

RUN python -m pip install -U templateflow && \
    python -c "from templateflow.api import get; get(['MNI152NLin2009cAsym', 'MNI152NLin6Asym', 'OASIS30ANTs', 'MNIPediatricAsym', 'MNIInfant'])"
ENV TEMPLATEFLOW_HOME /home/fmriprep/.cache/templateflow