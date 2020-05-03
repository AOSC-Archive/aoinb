#!/bin/bash

binfo() {
bold=$(tput bold)
normal=$(tput sgr0)
echo -e "${bold}[build.sh]${normal} $*"
}

binfo "Begin build"
binfo "This software is in WIP status. Don't rely on it."
# Remove this line before use!
rm -r build/

binfo "Fetching source code"
bash download_source.sh bundle/spec

binfo "Reading VER and REL"
source bundle/spec
if [[ -z $VER ]]; then
	binfo "VER undefined. Something's wrong!"
	binfo "Exiting."
	exit 1
else
	PKGVER=$VER
	PKGREL=$REL
	binfo "PKGVER=$PKGVER, PKGREL=$PKGREL"
fi

binfo "Copying autobuild to build folder."
cp -r bundle/autobuild build

# Changing work dir to build folder
cd build

binfo "Initializing build."
autobuild
