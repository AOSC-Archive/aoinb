#!/usr/bin/env python3

import os
import tomlkit
import shutil
from container import Container


def build(args):
    if not os.path.exists(args.package):
        raise IOError('Failed to read package bundle: folder does not exists.')

    buildkit_dir = config["workDir"] + "/.builder/buildkit/"
    if not os.path.exists(buildkit_dir):
        raise IOError("BuildKit does not exists, cannot proceed.")

    Container.set_buildkit_path(buildkit_dir)
    c = Container(args.branch, config['workDir'])
    if not os.path.exists(c.instance_overlay + '/etc/apt/source.list'):
        print('source.list not found in instance. Copying from config path.')
        source_list_path = args.config_path + '/source_lists/' + args.branch + '.list'
        if not os.path.exists(source_list_path):
            raise IOError('Corresponding source list not found!')
        else:
            c.instance_mkdir('/etc/apt/')
            c.copy_to_instance(source_list_path, '/etc/apt/sources.list')
            c.instance_up()
            c.instance_run('apt update')
            c.instance_run('apt full-upgrade')
    # Prepare build env
    c.workspace_mkdir('/buildroot')
    c.copy_dir_to_workspace(os.path.abspath(args.package), '/buildroot/bundle')
    # Copy toolbox
    c.copy_dir_to_workspace(os.path.abspath('./toolbox'), '/buildroot/toolbox')
    # Run the build script
    c.workspace_up()
    c.workspace_run('/buildroot/toolbox/build.sh')
    c.workspace_cleanup()


def load_buildkit(args):
    buildkit_dir = config["workDir"] + "/.builder/buildkit/"
    Container.set_buildkit_path(buildkit_dir)

    # Remove the old buildkit
    if os.path.exists(buildkit_dir):
        shutil.rmtree(buildkit_dir)

    arch = str(config['arch'])
    tar_xz_path = config['workDir'] + "/buildkit_" + arch + ".tar.xz"
    if (args.buildkit_path == 'null') and (not os.path.exists(tar_xz_path)):
        import urllib.request
        print("Downloading BuildKit from repo.aosc.io .")
        buildkit_url = "https://repo.aosc.io/aosc-os/os-" + arch + "/buildkit/aosc-os_buildkit_latest_amd64.tar.xz"
        # urlretriveve is considered a legacy interface, but for convenience it is used here.
        urllib.request.urlretrieve(buildkit_url, tar_xz_path)
    elif os.path.exists(tar_xz_path):
        pass
    else:
        tar_xz_path = args.buildkit_path

    # Now extract it
    print('Extracting BuildKit.')
    Container.install_buildkit(tar_xz_path)


def cleanup(args):
    print('Deleting work directory...')
    try:
        shutil.rmtree(config["workDir"] + "/.builder")
        print('Done.')
    except FileNotFoundError:
        print('Work directory already deleted or DNE. Doing nothing.')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='The builder component for AOINB.')
    parser.add_argument('-c','--config_path', help='Where aoinb-builder configuration files are located.',
                        type=str, default='/var/cache/aoinb/conf')

    subparser = parser.add_subparsers()
    parser_build = subparser.add_parser('build', help='Build a package.')
    parser_build.add_argument('package', help='Where spec and autobuild/* are located.', type=str)
    parser_build.add_argument('branch', help='Which branch to use. (stable, for example)', type=str)
    parser_build.set_defaults(func=build)

    parser_load_buildkit = subparser.add_parser('load-buildkit',
                                                help='Load BuildKit into build environment. '
                                                     'Note: this operation will remove the old BuildKit installation.')
    parser_load_buildkit.set_defaults(func=load_buildkit)

    parser_cleanup = subparser.add_parser('cleanup', help='Something feels wrong? Start everything all over again.')
    parser_cleanup.set_defaults(func=cleanup)

    args = parser.parse_args()

    if not os.path.exists(os.path.abspath(args.config_path)):
        raise IOError('Failed to read config: folder ' + os.path.abspath(args.config_path) + 'does not exists')

    with open(args.config_path + '/config.toml', 'r') as f:
        config = tomlkit.parse(f.read())

    try:
        args.func(args)
    except AttributeError as e:
        print('Too few arguments.')
        parser.print_help()
        parser.exit()
