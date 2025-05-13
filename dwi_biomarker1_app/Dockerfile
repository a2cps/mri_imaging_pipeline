FROM mambaorg/micromamba:2.0-ubuntu24.10

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

ENV TZ=America/Chicago
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/tapis/entrypoint.py
COPY --chown=$MAMBA_USER:$MAMBA_USER \
    assets/modules_all_in_MNI152NLin2009cAsym_brain.nii.gz \
    /opt/tapis/rois/
COPY --chmod=0775 --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.sh /usr/local/bin/probtrackx2_voxelwise

ENV APPTAINER_SHELL=/usr/local/bin/_apptainer_shell.sh
ENV FSLDIR=/opt/conda
ENV FSLOUTPUTTYPE=NIFTI_GZ

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/tapis/entrypoint.py"]
CMD [ "--help" ]