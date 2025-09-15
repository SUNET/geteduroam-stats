#!/usr/bin/env bash

set -e

script_name=$(basename "$0")

echo "running SUNET/geteduroam-stats/$script_name"

# We expect Jenkins to have set GIT_COMMIT for us.
if [ "$GIT_COMMIT" = "" ]; then
    echo "$script_name: GIT_COMMIT is not set, exiting"
    exit 1
fi

VERSION=$(git tag --contains "$GIT_COMMIT" | head -1)
if [ "$VERSION" = "" ]; then
    echo "$script_name: did not find a tag related to revision $GIT_COMMIT, using rev as version"
    VERSION=$GIT_COMMIT
fi

DOCKER_TAG="docker.sunet.se/geteduroam-stats:$VERSION"
echo "$script_name: building DOCKER_TAG $DOCKER_TAG"

docker build --build-arg "VERSION=$VERSION" --tag "$DOCKER_TAG" .
docker push "$DOCKER_TAG"
