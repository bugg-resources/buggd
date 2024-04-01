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

# Directory for storing the .deb package and related files
DEB_DIR="packages"
# Create the packages directory if it doesn't already exist
mkdir -p "$DEB_DIR"

# Move the built .deb package and related files to the DEB_DIR directory
# This assumes the parent directory of the current script is the root of your repo
# Adjust the pattern as necessary to match your package naming scheme
mv ../${PACKAGE_NAME}_* $DEB_DIR/

# Now proceed to generate the APT repository structure and Packages file
# Assuming you are in the root of your repo after moving the files
mkdir -p "dists"
cd $DEB_DIR
dpkg-scanpackages . /dev/null | gzip -9c > ../dists/stable/main/binary-all/Packages.gz
dpkg-scanpackages . /dev/null > ../dists/stable/main/binary-all/Packages

# Go to the dists directory to prepare the Release file
cd ../dists

# Generate Release file
# [The rest of the Release file generation process goes here, as previously described]

echo "Repository updated successfully."

# Remove the build tree - we don't need it
echo "Cleaning"
debian/rules clean

