#! /bin/bash

VERSION_FILE="pyproject.toml"
PREVIOUS_VERSION=$(git describe --abbrev=0 --tags)
# Remove leading 'v' char.
PREVIOUS_VERSION=${PREVIOUS_VERSION#?}
# Using sed to remove leading and trailing double quotes.
CURRENT_VERSION=$(grep -m 1 version $VERSION_FILE | awk '{print $3}' | sed -e 's/^"//' -e 's/"$//')

if [ $CURRENT_VERSION == $PREVIOUS_VERSION ]; then
  echo "ERROR: Version has not been updated in '$VERSION_FILE'!"
  echo "Don't forget to also update the CHANGELOG."
  echo "Current version: $CURRENT_VERSION"
  echo "Released version: $PREVIOUS_VERSION"
  exit 1
fi
