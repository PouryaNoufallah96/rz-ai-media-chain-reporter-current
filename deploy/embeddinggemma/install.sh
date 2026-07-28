#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT=/opt/embeddinggemma
MODEL_REPO=ggml-org/embeddinggemma-300M-qat-q4_0-GGUF
MODEL_NAME=embeddinggemma-300M-qat-Q4_0.gguf
MODEL_URL="https://huggingface.co/${MODEL_REPO}/resolve/main/${MODEL_NAME}"
MODEL_API="https://huggingface.co/api/models/${MODEL_REPO}?blobs=true"
SERVICE_SOURCE="${1:-/tmp/embeddinggemma.service}"
VERSION_FILE="${INSTALL_ROOT}/LLAMA_CPP_VERSION"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this installer as root." >&2
  exit 1
fi
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "This deployment is pinned for the ChainReporter x86_64 VPS." >&2
  exit 1
fi
if [[ ! -f "${SERVICE_SOURCE}" ]]; then
  echo "Service file not found: ${SERVICE_SOURCE}" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  build-essential ca-certificates cmake curl git python3

if ! id embeddinggemma >/dev/null 2>&1; then
  useradd --system --home-dir "${INSTALL_ROOT}" --shell /usr/sbin/nologin embeddinggemma
fi
install -d -o root -g embeddinggemma -m 0750 \
  "${INSTALL_ROOT}" "${INSTALL_ROOT}/bin" "${INSTALL_ROOT}/lib" \
  "${INSTALL_ROOT}/models" "${INSTALL_ROOT}/src"

if [[ -s "${VERSION_FILE}" ]]; then
  LLAMA_CPP_TAG="$(tr -d '[:space:]' < "${VERSION_FILE}")"
else
  LLAMA_CPP_TAG="$(
    python3 -c 'import json, urllib.request; print(json.load(urllib.request.urlopen("https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"))["tag_name"])'
  )"
  printf '%s\n' "${LLAMA_CPP_TAG}" > "${VERSION_FILE}"
fi
if [[ ! "${LLAMA_CPP_TAG}" =~ ^b[0-9]+$ ]]; then
  echo "Unexpected llama.cpp release tag: ${LLAMA_CPP_TAG}" >&2
  exit 1
fi

SOURCE_DIR="${INSTALL_ROOT}/src/llama.cpp"
if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  git clone --depth 1 --branch "${LLAMA_CPP_TAG}" \
    https://github.com/ggml-org/llama.cpp.git "${SOURCE_DIR}"
else
  git -C "${SOURCE_DIR}" fetch --depth 1 origin "refs/tags/${LLAMA_CPP_TAG}:refs/tags/${LLAMA_CPP_TAG}"
  git -C "${SOURCE_DIR}" checkout --detach "${LLAMA_CPP_TAG}"
fi
if [[ ! -x "${SOURCE_DIR}/build/bin/llama-server" ]]; then
  cmake -S "${SOURCE_DIR}" -B "${SOURCE_DIR}/build" \
    -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DLLAMA_CURL=OFF
  cmake --build "${SOURCE_DIR}/build" --config Release --target llama-server -j2
else
  echo "llama-server already built for ${LLAMA_CPP_TAG}; skipping compilation"
fi
install -o root -g embeddinggemma -m 0750 \
  "${SOURCE_DIR}/build/bin/llama-server" "${INSTALL_ROOT}/bin/llama-server"
find "${SOURCE_DIR}/build/bin" -maxdepth 1 -type f -name '*.so*' -exec \
  install -o root -g embeddinggemma -m 0640 '{}' "${INSTALL_ROOT}/lib/" ';'

EXPECTED_MODEL_SHA="$(
  MODEL_NAME="${MODEL_NAME}" MODEL_API="${MODEL_API}" python3 -c '
import json
import os
import urllib.request
data = json.load(urllib.request.urlopen(os.environ["MODEL_API"]))
target = next(item for item in data["siblings"] if item["rfilename"] == os.environ["MODEL_NAME"])
print(target["lfs"]["sha256"])
'
)"
if [[ ! "${EXPECTED_MODEL_SHA}" =~ ^[a-f0-9]{64}$ ]]; then
  echo "Could not obtain the trusted model SHA-256 from Hugging Face." >&2
  exit 1
fi

MODEL_PATH="${INSTALL_ROOT}/models/${MODEL_NAME}"
CURRENT_MODEL_SHA=""
if [[ -f "${MODEL_PATH}" ]]; then
  CURRENT_MODEL_SHA="$(sha256sum "${MODEL_PATH}" | awk '{print $1}')"
fi
if [[ "${CURRENT_MODEL_SHA}" != "${EXPECTED_MODEL_SHA}" ]]; then
  TEMP_MODEL="$(mktemp "${INSTALL_ROOT}/models/.embeddinggemma.XXXXXX")"
  trap 'rm -f "${TEMP_MODEL:-}"' EXIT
  curl --fail --location --retry 3 --output "${TEMP_MODEL}" "${MODEL_URL}"
  DOWNLOADED_SHA="$(sha256sum "${TEMP_MODEL}" | awk '{print $1}')"
  if [[ "${DOWNLOADED_SHA}" != "${EXPECTED_MODEL_SHA}" ]]; then
    echo "EmbeddingGemma checksum mismatch." >&2
    exit 1
  fi
  install -o root -g embeddinggemma -m 0640 "${TEMP_MODEL}" "${MODEL_PATH}"
  rm -f "${TEMP_MODEL}"
  trap - EXIT
fi
printf '%s  %s\n' "${EXPECTED_MODEL_SHA}" "${MODEL_NAME}" \
  > "${INSTALL_ROOT}/models/SHA256SUMS"
cat > "${INSTALL_ROOT}/MODEL_SOURCE" <<EOF
Repository: https://huggingface.co/${MODEL_REPO}
Model: ${MODEL_NAME}
License: https://ai.google.dev/gemma/terms
llama.cpp release: ${LLAMA_CPP_TAG}
EOF

if ! swapon --show=NAME --noheadings | grep -q .; then
  if [[ ! -e /swapfile ]]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile
  if ! grep -q '^/swapfile ' /etc/fstab; then
    printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
  fi
fi

install -o root -g root -m 0644 "${SERVICE_SOURCE}" \
  /etc/systemd/system/embeddinggemma.service
systemctl daemon-reload
systemctl enable --now embeddinggemma.service

for attempt in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8081/health >/dev/null; then
    echo "EmbeddingGemma is healthy on 127.0.0.1:8081."
    exit 0
  fi
  sleep 2
done

systemctl status embeddinggemma.service --no-pager || true
echo "EmbeddingGemma did not become healthy in time." >&2
exit 1
