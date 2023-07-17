#!/bin/sh

VERSION_NUMBER=$1 # for example 0.1
GIT_TAG=v${VERSION_NUMBER}

git commit -a -m "upgraded version to ${VERSION_NUMBER}"
git push
git tag -a ${GIT_TAG} -m "version ${GIT_TAG}"
git push origin ${GIT_TAG}

# docker build
export DOCKER_BUILDKIT=1
docker build -t lucwastiaux/clt-chatbot:${VERSION_NUMBER} -f Dockerfile.telegram .
docker push lucwastiaux/clt-chatbot:${VERSION_NUMBER}