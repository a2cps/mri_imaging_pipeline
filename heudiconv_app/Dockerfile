FROM bids/validator:v1.9.9 AS validator

FROM mambaorg/micromamba:1.5.6-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

RUN micromamba install --name base --yes --file /tmp/env.yml  \
    && rm -rf ~/.cache/pip \
    && rm -f /tmp/env*yml \
    && micromamba clean --yes --all 

USER root

COPY --from=validator /src/bids-validator /opt/bids-validator
RUN  ln -s /opt/bids-validator/bin/bids-validator /usr/local/bin/bids-validator

COPY --chown=$MAMBA_USER:$MAMBA_USER assets /tapis/assets
RUN chmod +x /tapis/assets/runner-template.sh

USER $MAMBA_USER

ENTRYPOINT ["/tapis/assets/runner-template.sh"]