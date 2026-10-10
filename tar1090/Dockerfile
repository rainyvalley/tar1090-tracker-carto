ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements
# Python deps come from Alpine packages rather than pip, so they track the
# base image's Alpine branch (security fixes included) instead of PyPI.
# hadolint ignore=DL3018
RUN \
    apk add --no-cache \
        python3 \
        py3-flask \
        py3-requests \
        py3-waitress

# Copy root filesystem
COPY rootfs /

# Set executable permissions
RUN chmod a+x /usr/bin/run.sh

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="rainyvalley <68121220+rainyvalley@users.noreply.github.com>" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="rainyvalley" \
    org.opencontainers.image.authors="rainyvalley <68121220+rainyvalley@users.noreply.github.com>" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://github.com/rainyvalley/tar1090-tracker-carto" \
    org.opencontainers.image.source="https://github.com/rainyvalley/tar1090-tracker-carto" \
    org.opencontainers.image.documentation="https://github.com/rainyvalley/tar1090-tracker-carto/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

# Port the app listens on (reached through HA ingress)
EXPOSE 5000

# Run
CMD ["/usr/bin/run.sh"]
