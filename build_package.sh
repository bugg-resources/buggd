#!/bin/bash

# Exit on error
set -e

PACKAGE_NAME="buggd"
ORIGIN="Bugg Project"
LABEL="buggd daemon package"
TARGET_CODENAME="bookworm" # Debian codename for the target distribution

GIT_REPO_ROOT="$(dirname "$O")" # buggd git repo root directory

# Now proceed to generate the APT repository structure and Packages file
# See Debian Repo Format specification section 1.1 for more details
# https://wiki.debian.org/DebianRepository/Format
GITHUB_PAGES_DIR=${GIT_REPO_ROOT}/docs
DIST_DIR=${GITHUB_PAGES_DIR}/dists
APT_REPO_DIR=${DIST_DIR}/${TARGET_CODENAME}/main/binary-all
PACKAGE_DIR=${GITHUB_PAGES_DIR}/pool/main/b/${PACKAGE_NAME}

PACKAGES_FILE=${APT_REPO_DIR}/Packages
RELEASE_FILE=${DIST_DIR}/${TARGET_CODENAME}/Release

mkdir -p $GITHUB_PAGES_DIR
mkdir -p $DIST_DIR
mkdir -p $APT_REPO_DIR
mkdir -p $PACKAGE_DIR

SKIP_BUILD=0 # Set to 1 to skip the build step, useful for testing
DEBUG=1
if [ $DEBUG -eq 1 ]; then
    echo "PACKAGE_NAME=$PACKAGE_NAME"
    echo "ORIGIN=$ORIGIN"
    echo "LABEL=$LABEL"
    echo "TARGET_CODENAME=$TARGET_CODENAME"
    echo "GIT_REPO_ROOT=$GIT_REPO_ROOT"
    echo "GITHUB_PAGES_DIR=$GITHUB_PAGES_DIR"
    echo "DIST_DIR=$DIST_DIR"
    echo "APT_REPO_DIR=$APT_REPO_DIR"
    echo "PACKAGE_DIR=$PACKAGE_DIR"
    echo "RELEASE_FILE=$RELEASE_FILE"
    echo "PACKAGES_FILE=$PACKAGES_FILE"
fi


if [ -z "$PACKAGE_NAME" ]; then
    echo "Package name is not set. Please edit the script and set the PACKAGE_NAME variable."
    exit 1
fi

### Update the changelog with the current version, from pyproject.toml.
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
dch -v "${VERSION}-1" "Version $VERSION released" -D stable --force-distribution

# Build the package
echo "Building the package..."
if [ $SKIP_BUILD -eq 0 ]; then
    dpkg-buildpackage -us -uc -b
else
    echo "WARNING: Skipping the build step."
fi

echo "Creating the Packages file..."
# Create the Packages and Packages.gz files
apt-ftparchive packages ${GITHUB_PAGES_DIR}/pool > ${PACKAGES_FILE}
gzip -f -k ${PACKAGES_FILE} 

echo "Creating the Release file..."
# Create the Release file
apt-ftparchive release ${DIST_DIR}/${TARGET_CODENAME} > ${RELEASE_FILE}

# dpkg-buildpackage creates the .deb package in the parent directory
# Move the built .deb package and related files to the PACKAGE_DIR directory
cp ${GIT_REPO_ROOT}/../${PACKAGE_NAME}_* $PACKAGE_DIR/


# TODO:
# Sign the Release file (optional, but recommended for public repositories)
# gpg --default-key "YourEmail" --output stable/Release.gpg --detach-sign stable/Release

echo "Repository updated successfully."

# Remove the build tree - we don't need it
echo "Cleaning"
debian/rules clean

