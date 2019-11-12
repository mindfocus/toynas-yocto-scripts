#!/bin/bash
set -e

source /manage-docker.sh

trap 'cleanup fail' SIGINT SIGTERM

# Start docker
echo "[INFO] Starting docker."
dockerd --data-root /scratch/docker > /var/log/docker.log &
wait_docker

_local_image=$(docker load -i /host/resin-image.docker | cut -d: -f1 --complement | tr -d " " )

echo "[INFO] Logging into $deployTo as balenaos"
if [ "$DEPLOY_TO" = "staging" ]; then
	export BALENARC_BALENA_URL=balena-staging.com
	balena login --token $BALENAOS_STAGING_TOKEN
else
	balena login --token $BALENAOS_PRODUCTION_TOKEN
fi

case $ESR_LINE in
	next|current|sunset)
		SLUG="${SLUG}-esr"
		;;
	__ignore__)
		;;
	*)
		echo "Invalid ESR line"
		exit 1
		;;
esac

echo "[INFO] Pushing $_local_image to balenaos/$SLUG"

_releaseID=$(balena deploy "balenaos/$SLUG" "$_local_image" | sed -n 's/.*Release: //p')
if [ "$DEVELOPMENT_IMAGE" = "yes" ]; then
	_variant="development"
else
	_variant="production"
fi

balena tag set version $VERSION_HOSTOS --release $_releaseID
balena tag set variant $_variant --release $_releaseID
balena tag set status "Untested" --release $_releaseID
if [ "$ESR_LINE" != "__ignore__" ]; then
	balena tag set "ESR-line" $ESR_LINE --release $_releaseID
fi

cleanup
exit 0