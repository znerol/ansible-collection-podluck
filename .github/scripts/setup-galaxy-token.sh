#!/bin/sh

set -eu

mkdir -p ~/.ansible
umask 0077
echo "token: ${ANSIBLE_GALAXY_TOKEN}" > ~/.ansible/galaxy_token
