#!/usr/bin/env python3

import argparse
import os
import tomlkit
# For prepare_buildkit
import urllib
from container import Container


parser = argparse.ArgumentParser(description='The builder component for AOINB.')
parser.add_argument('operation', help='What job to do for today?', type=str,
                    choices=['build', 'load-buildkit'])
parser.add_argument('package', help='Where spec and autobuild/* are located.', type=str)
parser.add_argument('branch', help='Which branch to use. (stable, for example)', type=str)

parser.add_argument('-c','--config_path', help='Where auinb-builder configuration files are located.', type=str)

args = parser.parse_args()

if not os.path.exists(args.config_path):
    raise IOError('Failed to read config: folder does not exists.')

if not os.path.exists(args.package):
    raise IOError('Failed to read package bundle: folder does not exists.')

with open(args.config_path + '/config.toml', 'r') as f:
    config = tomlkit.parse(f.read())

buildkit_dir = config["workDir"] + "/.builder/buildkit/"
if not os.path.exists(buildkit_dir):
    print("BuildKit does not exists, creating directory.")
    os.makedirs(buildkit_dir)

Container.set_buildkit_path(buildkit_dir)

if args.operation == 'load-buildkit':
    print("Downloading and extracting buildkit.")
    Container.install_buildkit(config["mirrorBaseUrl"], config["arch"])
elif args.operation == 'build':
    c = Container(args.branch, config['workDir'])
    # Prepare build env
    c.workspace_mkdir('/buildroot')
    c.copy_dir_to_workspace(os.path.abspath(args.package), '/buildroot/bundle')
    # Copy toolbox
    c.copy_dir_to_workspace(os.path.abspath('./toolbox'), '/buildroot/toolbox')
    # Run the build script
    c.workspace_up()
    c.workspace_run('/buildroot/toolbox/build.sh')


