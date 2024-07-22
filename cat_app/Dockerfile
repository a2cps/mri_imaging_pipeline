FROM mambaorg/micromamba:1.5-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV TZ=America/Chicago
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all


ENV MCRROOT=/opt/mcr
ENV MCR_INHIBIT_CTF_LOCK=1


ENV MATLAB_VERSION=R2017b
ENV MCR_VERSION=v93
USER root
ADD --chown=$MAMBA_USER:$MAMBA_USER https://ssd.mathworks.com/supportfiles/downloads/${MATLAB_VERSION}/deployment_files/${MATLAB_VERSION}/installers/glnxa64/MCR_${MATLAB_VERSION}_glnxa64_installer.zip /tmp/
RUN unzip -q /tmp/MCR_${MATLAB_VERSION}_glnxa64_installer.zip -d /tmp/mcr_install \
    && /tmp/mcr_install/install -destinationFolder ${MCRROOT} -agreeToLicense yes -mode silent \
    && rm -rf /tmp/mcr_install /tmp/*

# cat12
ENV CAT_VERSION=12.9
ENV CAT_REVISION=r2577
ENV SPMROOT=/opt/CAT${CAT_VERSION}_${CAT_REVISION}_${MATLAB_VERSION}_MCR_Linux
ADD --chown=$MAMBA_USER:$MAMBA_USER https://www.neuro.uni-jena.de/cat12/CAT${CAT_VERSION}_${MATLAB_VERSION}_MCR_Linux.zip /tmp/
RUN unzip -q /tmp/CAT${CAT_VERSION}_${MATLAB_VERSION}_MCR_Linux.zip -d /opt 
# \
#     && ${SPMROOT}/run_spm12.sh ${MCRROOT}/v93 --version

# RUN cp -l ${SPMROOT}/standalone/cat_standalone.sh /usr/local/bin/

ENV APPTAINER_SHELL=/usr/local/bin/_apptainer_shell.sh

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]
