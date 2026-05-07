# Multi-stage build for hw-preflight.
#
# Stage 1: build the C++ helper and a wheel.
# Stage 2: a slim image that runs the CLI.

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ninja-build \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .

RUN python -m pip install --upgrade pip build \
    && python -m build --wheel \
    && cmake -S hwprobe -B hwprobe/build -DCMAKE_BUILD_TYPE=Release -G Ninja \
    && cmake --build hwprobe/build -j

# ---------------------------------------------------------------------------

FROM python:3.12-slim AS runtime

# Tools used by some checks: ip(8), timedatectl, systemctl. These are
# optional; checks emit `unavailable` when their binaries are missing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /src/dist/*.whl /tmp/
COPY --from=builder /src/hwprobe/build/hwprobe /usr/local/bin/hwprobe

RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

ENTRYPOINT ["hw-preflight"]
CMD ["run", "--quiet"]
