#!/bin/bash

# Exit on error
set -e

# Ensure package name is provided
PACKAGE_NAME="buggd"
if [ -z "$PACKAGE_NAME" ]; then
    echo "Package name is not set. Please edit the script and set the PACKAGE_NAME variable."
    exit 1
fi

# Extract version from pyproject.toml
VERSION=$(python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")

# Check if VERSION is empty
if [ -z "$VERSION" ]; then
    echo "Version could not be extracted from pyproject.toml. Exiting."
    exit 1
fi

# Extract email from git configuration
export EMAIL=$(git config --get user.email)
if [ -z "$EMAIL" ]; then
    echo "Git email is not set. Please set it or modify the script to hardcode the EMAIL variable."
    exit 1
fi

# Update debian/changelog
dch -v "$VERSION-1" "Version $VERSION released" -D stable --force-distribution

# Build the package
dpkg-buildpackage -us -uc -b

