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
RELEASE_FILE=${DIST_DIR}/${TARGET_CODENAME}/Release

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
fi


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
if [ $SKIP_BUILD -eq 0 ]; then
    dpkg-buildpackage -us -uc -b
fi

# Create the packages directory if it doesn't already exist
mkdir -p $PACKAGE_DIR

# dpkg-buildpackage creates the .deb package in the parent directory
# Move the built .deb package and related files to the PACKAGE_DIR directory
mv ${GIT_REPO_ROOT}/../${PACKAGE_NAME}_* $PACKAGE_DIR/

mkdir -p $DIST_DIR
mkdir -p $APT_REPO_DIR
cd $GITHUB_PAGES_DIR    # Required to prevent the github pages part of the path from being included in the Packages file Filename field.
dpkg-scanpackages . /dev/null | gzip -9c > ${APT_REPO_DIR}/Packages.gz
dpkg-scanpackages . /dev/null > ${APT_REPO_DIR}/Packages
cd $GIT_REPO_ROOT 

# Generate Release file (example; adjust as needed)
cat > $RELEASE_FILE << EOF
Archive: ${TARGET_CODENAME}
Component: main
Origin: ${ORIGIN}
Label: ${LABEL}
Architecture: all # Indicate that the repository contains architecture-independent packages
EOF



do_hash() {
    HASH_NAME=$1
    HASH_CMD=$2
    echo "${HASH_NAME}:"
    for f in $(find -type f); do
        f=$(echo $f | cut -c3-) # remove ./ prefix
        if [ "$f" = "Release" ]; then
            continue
        fi
        echo " $(${HASH_CMD} ${f}  | cut -d" " -f1) $(wc -c $f)"
    done
}

do_hash MD5Sum md5sum >> $RELEASE_FILE
do_hash SHA1 sha1sum >> $RELEASE_FILE
do_hash SHA256 sha256sum >> $RELEASE_FILE

exit 0

# Append the hash sums to the Release file
echo -e "\nMD5Sum:" >> $RELEASE_FILE
md5sum ${APT_REPO_DIR}/Packages >> $RELEASE_FILE
md5sum ${APT_REPO_DIR}/Packages.gz >> $RELEASE_FILE

echo -e "\nSHA1:" >> $RELEASE_FILE
sha1sum ${APT_REPO_DIR}/Packages >> $RELEASE_FILE
sha1sum ${APT_REPO_DIR}/Packages.gz >> $RELEASE_FILE

echo -e "\nSHA256:" >> $RELEASE_FILE
sha256sum ${APT_REPO_DIR}/Packages >> $RELEASE_FILE
sha256sum ${APT_REPO_DIR}/Packages.gz >> $RELEASE_FILE

# Sign the Release file (optional, but recommended for public repositories)
# gpg --default-key "YourEmail" --output stable/Release.gpg --detach-sign stable/Release

echo "Repository updated successfully."

# Remove the build tree - we don't need it
echo "Cleaning"
debian/rules clean

