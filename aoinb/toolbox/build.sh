#!/bin/bash

binfo() {
bold=$(tput bold)
normal=$(tput sgr0)
echo -e "${bold}[build.sh]${normal} $*"
}

binfo "Begin build"
binfo "This software is in WIP status. Don't rely on it."
export PATH=/buildroot/toolbox:$PATH
cd /buildroot

binfo "Fetching source code"
bash download_source.sh bundle/spec

if [[ $? -ne 0 ]]; then
	binfo "Souce downloading failed! Exiting."
fi

binfo "Reading VER and REL"
source bundle/spec
if [[ -z $VER ]]; then
	binfo "VER undefined. Something's wrong!"
	binfo "Exiting."
	exit 1
fi

binfo "PKGVER=$PKGVER, PKGREL=$PKGREL"

binfo "Copying autobuild to build folder."
cp -r bundle/autobuild build

binfo "Adding PKGVER and PKGREL to autobuild/defines"
echo PKGVER=$VER >> build/autobuild/defines
echo PKGREL=$REL >> build/autobuild/defines

# Changing work dir to build folder
cd build

binfo "Initializing build."
procmon.py autobuild

if [[ $? -eq 0 ]]; then
	binfo "Build successful. Copying result to result folder."
	cd ..
	mkdir output
	cp build/*.deb output/
else
	binfo "Build failed!"
	exit 1
fi
