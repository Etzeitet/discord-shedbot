#!/usr/bin/bash

VERSION="${1}"

if [[ -z ${VERSION} ]]; then
    VERSION="$(awk -F'[ \"]' '/VERSION/ {print $4}' shedbot/main.py)"
fi

echo "Version: ${VERSION}"
docker build -t "oakmoss/shedbot:${VERSION}" -t oakmoss/shedbot:latest .
