#!/bin/bash

set -ev

DOCKERFILES=( Dockerfile_yocto-build-env Dockerfile_balena-push-env )

REVISION=$(git rev-parse --short HEAD)

# Get the absolute script location
pushd `dirname $0` > /dev/null 2>&1
SCRIPTPATH=`pwd`
popd > /dev/null 2>&1

if [ -z "${JOB_NAME}" ]; then
    echo "[ERROR] No job name specified."
    exit 1
fi

for DOCKERFILE in "${DOCKERFILES[@]}"
do
  # Build
  docker build --pull --no-cache --tag resin/${JOB_NAME}:${REVISION} -f ${SCRIPTPATH}/${DOCKERFILE} ${SCRIPTPATH}

  # Tag
  docker tag resin/${JOB_NAME}:${REVISION} resin/${JOB_NAME}:latest

  # Push
  docker push resin/${JOB_NAME}:${REVISION}
  docker push resin/${JOB_NAME}:latest
done
