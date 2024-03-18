FROM poldracklab/mriqc:0.15.1

COPY assets /tapis/assets
RUN chmod +x /tapis/assets/runner-template.sh

ENTRYPOINT ["/tapis/assets/runner-template.sh"]
