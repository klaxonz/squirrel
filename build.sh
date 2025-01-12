#!/bin/bash

IMAGE_NAME="klaxonz/squirrel"
VERSION=$(grep '__version__' squirrel-backend/__init__.py | awk -F "'" '{print $2}')

if [ -z "$VERSION" ]; then
    echo "Failed to retrieve version from squirrel-backend/__init__.py"
    exit 1
fi

echo "Building Docker image with version $VERSION..."

docker build --no-cache -t "$IMAGE_NAME:$VERSION" .
docker tag "$IMAGE_NAME:$VERSION" "$IMAGE_NAME:latest"

echo "Image built and tagged as $IMAGE_NAME:$VERSION and $IMAGE_NAME:latest."
