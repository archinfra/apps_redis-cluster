FROM oliver006/redis_exporter:v1.89.0 AS upstream

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=upstream /redis_exporter /usr/local/bin/redis_exporter

USER 1001
ENTRYPOINT ["/usr/local/bin/redis_exporter"]
