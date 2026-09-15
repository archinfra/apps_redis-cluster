# Archinfra Redis Cluster runtime
#
# Redis is built from the upstream Redis 8.10.1 source commit on Debian 12.
# The initial runtime keeps the public Bitnami redis-cluster shell contract
# (Apache-2.0) so the forked chart can migrate without rewriting bootstrap
# semantics in the same release.

FROM debian:bookworm-slim AS redis-builder
ARG REDIS_VERSION=8.10.1
ARG REDIS_COMMIT=3399357e7c17b668289386b8a15a3037bc4527b1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
       build-essential \
       libssl-dev \
       pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && git init /src/redis \
    && cd /src/redis \
    && git remote add origin https://github.com/redis/redis.git \
    && git fetch --depth 1 origin "${REDIS_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${REDIS_COMMIT}"
RUN make -C /src/redis -j"$(nproc)" BUILD_TLS=yes \
    && make -C /src/redis install BUILD_TLS=yes PREFIX=/opt/redis-dist

FROM debian:bookworm-slim AS bitnami-source
ARG BITNAMI_CONTAINERS_REF=31d7973ac4a12f31662cf06c0e636d858e984184
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && git init /src/bitnami-containers \
    && cd /src/bitnami-containers \
    && git remote add origin https://github.com/bitnami/containers.git \
    && git sparse-checkout init --cone \
    && git sparse-checkout set bitnami/redis-cluster/8.10/debian-12 \
    && git fetch --depth 1 origin "${BITNAMI_CONTAINERS_REF}" \
    && git checkout --detach FETCH_HEAD

FROM debian:bookworm-slim

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       hostname \
       libssl3 \
       openssl \
       procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=redis-builder /opt/redis-dist/bin/ /opt/bitnami/redis/bin/

# Transitional compatibility layer derived from the public Bitnami source.
COPY --from=bitnami-source /src/bitnami-containers/bitnami/redis-cluster/8.10/debian-12/prebuildfs/ /
COPY --from=bitnami-source /src/bitnami-containers/bitnami/redis-cluster/8.10/debian-12/rootfs/ /
COPY wait-for-port /usr/local/bin/wait-for-port

RUN mkdir -p \
      /opt/bitnami/redis/etc \
      /opt/bitnami/redis/etc.default \
      /opt/bitnami/redis/logs \
      /opt/bitnami/redis/tmp \
      /bitnami/redis/data \
    && chmod 0755 /usr/local/bin/wait-for-port \
    && for bin in /opt/bitnami/redis/bin/redis-*; do \
         ln -sf "${bin}" "/usr/local/bin/$(basename "${bin}")"; \
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
