FROM mambaorg/micromamba:2.0-ubuntu24.10

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

ENV TZ=America/Chicago
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

ENV FSLDIR=/opt/conda
ENV FSLOUTPUTTYPE=NIFTI_GZ

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py" ]
CMD [ "--help" ]
