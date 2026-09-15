# Derived from the public Bitnami redis-cluster runtime contract (Apache-2.0)
# while using the Redis OSS image as the Redis binary source.
#
# Upstream Bitnami source is pinned so the runtime contract is reproducible.

FROM debian:bookworm-slim AS bitnami-source
ARG BITNAMI_CONTAINERS_REF=31d7973ac4a12f31662cf06c0e636d858e984184
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && git clone https://github.com/bitnami/containers.git /src/bitnami-containers \
    && cd /src/bitnami-containers \
    && git checkout "${BITNAMI_CONTAINERS_REF}"

FROM redis:8.10.1-bookworm

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       hostname \
       openssl \
       procps \
    && rm -rf /var/lib/apt/lists/*

# Reuse the public Apache-2.0 Bitnami shell contract so the forked 13.0.5
# chart remains compatible while archinfra progressively removes this layer.
COPY --from=bitnami-source /src/bitnami-containers/bitnami/redis-cluster/8.10/debian-12/prebuildfs/ /
COPY --from=bitnami-source /src/bitnami-containers/bitnami/redis-cluster/8.10/debian-12/rootfs/ /

RUN mkdir -p \
      /opt/bitnami/redis/bin \
      /opt/bitnami/redis/etc \
      /opt/bitnami/redis/etc.default \
      /opt/bitnami/redis/logs \
      /opt/bitnami/redis/tmp \
      /bitnami/redis/data \
    && for bin in /usr/local/bin/redis-*; do \
         ln -sf "${bin}" "/opt/bitnami/redis/bin/$(basename "${bin}")"; \
       done \
    && : > /opt/bitnami/redis/etc/redis-default.conf \
    && /opt/bitnami/scripts/redis-cluster/postunpack.sh \
    && chown -R 1001:1001 /opt/bitnami/redis /bitnami/redis

ENV APP_VERSION="8.10.1" \
    BITNAMI_APP_NAME="redis-cluster" \
    IMAGE_REVISION="archinfra.1" \
    PATH="/opt/bitnami/redis/bin:/usr/local/bin:$PATH"

EXPOSE 6379 16379

USER 1001
ENTRYPOINT ["/opt/bitnami/scripts/redis-cluster/entrypoint.sh"]
CMD ["/opt/bitnami/scripts/redis-cluster/run.sh"]
