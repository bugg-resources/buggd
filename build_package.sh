#!/bin/bash

# Exit on error
set -e

PACKAGE_ROOT="$(dirname "$O")"
TARGET_CODENAME="bookworm"

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
dch -v "${VERSION}-1" "Version $VERSION released" -D stable --force-distribution

# Build the package
echo WARNING: skipping
#dpkg-buildpackage -us -uc -b

# Directory for storing the .deb package and related files
DEB_DIR=${PACKAGE_ROOT}/packages
# Create the packages directory if it doesn't already exist
mkdir -p $DEB_DIR

# dpkg-buildpackage creates the .deb package in the parent directory
# Move the built .deb package and related files to the DEB_DIR directory
mv ${PACKAGE_ROOT}/../${PACKAGE_NAME}_* $DEB_DIR/

# Now proceed to generate the APT repository structure and Packages file
DIST_DIR=${PACKAGE_ROOT}/dists
mkdir -p $DIST_DIR
# See Debian Repo Format specification section 1.1 for more details
REPO_DIR=${DIST_DIR}/${TARGET_CODENAME}/main/binary-all
mkdir -p $REPO_DIR
cd $DEB_DIR
echo `realpath .`
dpkg-scanpackages . /dev/null | gzip -9c > ${REPO_DIR}/Packages.gz
dpkg-scanpackages . /dev/null > ${REPO_DIR}/Packages

RELEASE_FILE=${DIST_DIR}/${TARGET_CODENAME}/Release
# Generate Release file (example; adjust as needed)
cat > $RELEASE_FILE << EOF
Archive: stable
Component: main
Origin: YourNameOrOrganization
Label: YourLabel
Architecture: all # Indicate that the repository contains architecture-independent packages
EOF

# Append the hash sums to the Release file
echo -e "\nMD5Sum:" >> $RELEASE_FILE
md5sum ${REPO_DIR}/Packages >> $RELEASE_FILE
md5sum ${REPO_DIR}/Packages.gz >> $RELEASE_FILE

echo -e "\nMD5Sum:" >> $RELEASE_FILE
sha1sum ${REPO_DIR}/Packages >> $RELEASE_FILE
sha1sum ${REPO_DIR}/Packages.gz >> $RELEASE_FILE

echo -e "\nMD5Sum:" >> $RELEASE_FILE
sha256sum ${REPO_DIR}/Packages >> $RELEASE_FILE
sha256sum ${REPO_DIR}/Packages.gz >> $RELEASE_FILE

# Sign the Release file (optional, but recommended for public repositories)
# gpg --default-key "YourEmail" --output stable/Release.gpg --detach-sign stable/Release

echo "Repository updated successfully."

# Remove the build tree - we don't need it
echo "Cleaning"
debian/rules clean

