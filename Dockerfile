ARG PYTHON_VERSION="3.10"

FROM python:${PYTHON_VERSION}

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG AUX_GROUP_IDS=""
ARG TIMEZONE="Europe/Warsaw"

SHELL ["/bin/bash", "-c"]

RUN set -Eeuxo pipefail && \
  addgroup --gid "${GROUP_ID}" user && \
  adduser --disabled-password --uid "${USER_ID}" --gid "${GROUP_ID}" user && \
  echo "${AUX_GROUP_IDS}" | xargs -n1 echo | xargs -I% addgroup --gid % group% && \
  echo "${AUX_GROUP_IDS}" | xargs -n1 echo | xargs -I% usermod --append --groups group% user && \
  apt-get update && \
  apt-get install --no-install-recommends -y \
    apt-transport-https \
    git \
    gpg-agent \
    software-properties-common \
    tzdata && \
  echo "${TIMEZONE}" > /etc/timezone && \
  cp "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime && \
  apt -qy autoremove && \
  apt clean && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /home/user

ENV EXAMPLE_PROJECTS_PATH="/home/user"

RUN set -Eeuxo pipefail && \
  git clone https://github.com/mbdevpl/argunparse argunparse && \
  git clone https://github.com/mbdevpl/transpyle transpyle && \
  git clone https://github.com/mbdevpl/typed-astunparse typed-astunparse

WORKDIR /home/user/project

COPY --chown=${USER_ID}:${GROUP_ID} requirements*.txt ./

USER user

RUN set -Eeuxo pipefail && \
  pip3 install --user -r requirements_ci.txt

VOLUME ["/home/user/project"]
