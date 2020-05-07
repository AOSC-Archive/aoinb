#!/bin/bash

_help_message() {
	printf "\
Useage

	download_source SPEC_FILE
"
}

dinfo() {
bold=$(tput bold)
normal=$(tput sgr0)
echo -e "${bold}[download_source.sh]${normal} $*"
}

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
	_help_message
	exit 0
fi

if [ -z "$1" ]; then
	dinfo "Please specify a package group."
	_help_message
	exit 1
fi

source $1

if [ -n "$SRCTBL" ] && [ -n "$CHKSUM" ]; then
	# Set stuff first
	PKGVER=$VER
	PKGREL=$REL
	# Split the CHKSUM, require GNU sed
	SPLIT=$(sed 's/::/\n/g' <<< $CHKSUM)
	# And make it an array
	arr=($SPLIT)
	chksum_type=${arr[0]}
	chksum_digit=${arr[1]}

	downloader.tcl $VER.bin SRCTBL $SRCTBL ${SPLIT[0]} ${SPLIT[1]}

	if [[ $? -eq 0 ]]; then
		dinfo "SRCTBL Download success."
		mkdir build
		tar xf $VER.bin -C build
		if [[ -n $SUBDIR ]] && [[ -d $SUBDIR ]]; then
			dinfo "SUBDIR detected. Moving source files to build/ root."
			mv build/$SUBDIR/* build/
		else
			dinfo "SUBDIR undefined. Moving source files from the first avaliable dir to build/ root."
			mv build/$(ls build | head -n 1)/* build/
		fi
	else
		dinfo "SRCTBL Download failed!"
		exit 1
	fi
elif [ -n "$GITSRC" ] && [ -n "$GITCO" ]; then
	downloader.tcl build GITSRC $GITSRC '' $GITCO
	if [[ $? -eq 0 ]]; then
		dinfo "GITSRC download success."
	else
		dinfo "GITSRC download failed!"
		exit 1
	fi
elif [ -n "$SVNSRC" ] && [ -n "$SVNCO" ]; then
	downloader.tcl build SVNSRC $SVNSRC '' $SVNCO
	if [[ $? -eq 0 ]]; then
		dinfo "SVNSRC download success."
	else
		dinfo "SVNSRC download failed!"
		exit 1
	fi
elif [ -n "$HGSRC" ] && [ -n "$HGCO" ]; then
	downloader.tcl build HGSRC $HGSRC '' $HGCO
	if [[ $? -eq 0 ]]; then
		dinfo "HGSRC download success."
	else
		dinfo "HGSRC download failed!"
		exit 1
	fi
else
	dinfo "Not found."
	exit 1
fi
