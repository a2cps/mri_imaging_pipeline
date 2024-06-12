FROM afni/afni_make_build:AFNI_23.1.10 as AFNI
FROM psadil/brainager:240611

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba install --name base -c conda-forge --no-deps --yes openssl=3.0.7 \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

ENV APPTAINER_SHELL=/usr/local/bin/_apptainer_shell.sh
    
ENV AFNIDIR=/opt/afni/install
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py
COPY --from=AFNI ${AFNIDIR}/3dWarp ${AFNIDIR}/libf2c.so ${AFNIDIR}/libmri.so ${AFNIDIR}/
env PATH=${AFNIDIR}:${PATH}

ENV TZ=US/Central
ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]

