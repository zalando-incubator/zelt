#! /bin/bash

LAST_MERGE=$(git log --pretty="format:%H" --merges -n 1)
VERSION_FILE="pyproject.toml"
PREVIOUS_VERSION=$(git show $LAST_MERGE:$VERSION_FILE | grep version | awk '{print $3}')
CURRENT_VERSION=$(grep -m 1 version $VERSION_FILE | awk '{print $3}')

if [ $CURRENT_VERSION == $PREVIOUS_VERSION ]; then
  echo "ERROR: Version has not been updated in '$VERSION_FILE'!"
  echo "Don't forget to also update the CHANGELOG."
  echo "Current version: $CURRENT_VERSION"
  echo "Released version: $PREVIOUS_VERSION"
  exit 1
fi
