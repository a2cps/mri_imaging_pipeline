FROM nipreps/fmriprep:25.2.5

RUN apt-get update && \
    apt-get install -y curl bzip2 && \
    rm -rf /var/lib/apt/lists/*

# 2. Download the standalone micromamba binary
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
ENV PREFIX=/app/.pixi/envs/fmriprep

# 3. Inject the package directly into the orphaned pixi environment
RUN ./bin/micromamba install -y --prefix ${PREFIX} -c conda-forge --freeze-installed \
    impi_rt=2021.12 \
    ucx=1.17.0 \
    rdma-core=52.0 \
    mpi4py=3.1.6 \
    polars=1.33.1 \
    pip \
    git \
    && ./bin/micromamba run --prefix ${PREFIX} pip install \
    --no-deps \
    git+https://github.com/a2cps/biomarker-extractor.git@6ef6883 \
    && ./bin/micromamba clean --all --yes \
    && rm bin/micromamba

# files searched for in entrypoint.py
COPY assets/entrypoint.py assets/license.txt /opt/fmriprep_app/
ENV TZ=US/Central

ENTRYPOINT ["/app/.pixi/envs/fmriprep/bin/python",  "/opt/fmriprep_app/entrypoint.py"]
CMD [ "--help" ]

