FROM mambaorg/micromamba:2.0-ubuntu24.10

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

ENV TZ=America/Chicago
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

ENV APPTAINER_SHELL=/usr/local/bin/_apptainer_shell.sh

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/2013_Wager_NEJM_NPS/*gz /opt/conda/lib/python3.12/site-packages/biomarkers/data/2013_Wager_NEJM_NPS/
ADD --chown=$MAMBA_USER:$MAMBA_USER https://github.com/canlab/Neuroimaging_Pattern_Masks/raw/refs/heads/master/Multivariate_signature_patterns/2017_Woo_SIIPS1/nonnoc_v11_4_137subjmap_weighted_mean.nii.gz /opt/conda/lib/python3.12/site-packages/biomarkers/data/2017_Woo_SIIPS1/
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]
