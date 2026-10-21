# PostgreSQL 16 on Alpine with pgvector (ADR 0037). Same base and libc as before, so
# existing data volumes keep working; tests build and use this same image.
FROM postgres:16-alpine

ARG PGVECTOR_VERSION=0.8.0

RUN apk add --no-cache --virtual .build-deps git build-base \
    && git clone --branch "v${PGVECTOR_VERSION}" --depth 1 \
       https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && make -C /tmp/pgvector OPTFLAGS="" with_llvm=no \
    && make -C /tmp/pgvector install with_llvm=no \
    && rm -rf /tmp/pgvector \
    && apk del .build-deps
