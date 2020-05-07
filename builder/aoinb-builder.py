#!/usr/bin/env python3

import os
import tomlkit
import shutil
from container import Container


def build(args):
    if not os.path.exists(args.package):
        raise IOError('Failed to read package bundle: folder does not exists.')

    baseos_dir = config["workDir"] + "/.builder/baseos/"
    if not os.path.exists(baseos_dir):
        raise IOError("BuildKit does not exists, cannot proceed.")

    Container.set_baseos_path(baseos_dir)
    c = Container(args.branch, config['workDir'])

    # Prepare instance for first time use
    if not os.path.exists(c.instance_overlay + '/etc/apt/source.list'):
        print('source.list not found in instance. Copying from config path.')
        source_list_path = args.config_path + '/source_lists/' + args.branch + '.list'
        if not os.path.exists(source_list_path):
            raise IOError('Corresponding source list not found!')
        else:
            if not os.path.exists(c.instance_dir + '/etc/apt'):
                c.instance_mkdir('/etc/apt/')
            c.copy_to_instance(source_list_path, '/etc/apt/sources.list')

    # First do an instance update before build
    c.instance_up()
    c.instance_run('apt-get update -q', [])
    c.instance_run('apt-get dist-upgrade -y -q', [])
    c.instance_run('apt-get clean -y', [])
    c.instance_down()

    # Prepare build env
    c.workspace_mkdir('/buildroot')
    c.copy_dir_to_workspace(os.path.abspath(args.package), '/buildroot/bundle')
    # Copy toolbox
    c.copy_dir_to_workspace(os.path.abspath('./toolbox'), '/buildroot/toolbox')
    # Run the build script
    c.workspace_up()
    c.workspace_run('/buildroot/toolbox/build.sh', [])
    c.workspace_down()
    c.workspace_cleanup()


def update_baseos(args):
    print('Updating base OS...')
    baseos_dir = config["workDir"] + "/.builder/baseos/"
    if not os.path.exists(baseos_dir):
        raise IOError("BuildKit does not exists, cannot proceed.")
    Container.set_baseos_path(baseos_dir)

    Container.baseos_run('apt-get update --quiet', ['DEBIAN_FRONTEND=noninteractive'])
    Container.baseos_run('apt-get upgrade -y --quiet', ['DEBIAN_FRONTEND=noninteractive'])
    Container.baseos_run('apt-get clean -y --quiet', ['DEBIAN_FRONTEND=noninteractive'])


def load_baseos(args):
    baseos_dir = config["workDir"] + "/.builder/baseos/"
    Container.set_baseos_path(baseos_dir)

    # Remove the old baseos
    if os.path.exists(baseos_dir):
        shutil.rmtree(baseos_dir)

    arch = str(config['arch'])
    tar_xz_path = config['workDir'] + "/buildkit_" + arch + ".tar.xz"
    if not os.path.exists(tar_xz_path):
        import urllib.request
        print("Downloading BuildKit from repo.aosc.io...")
        baseos_url = "https://repo.aosc.io/aosc-os/os-" + arch + "/buildkit/aosc-os_buildkit_latest_amd64.tar.xz"
        # urlretriveve is considered a legacy interface, but for convenience it is used here.
        urllib.request.urlretrieve(baseos_url, tar_xz_path)

    # Now extract it
    print('Extracting base OS...')
    Container.install_baseos(tar_xz_path)


def cleanup(args):
    if args.target == 'all':
        print('Deleting everything in the work directory...')
        try:
            shutil.rmtree(config["workDir"] + "/.builder")
            print('Done.')
        except FileNotFoundError:
            print('Work directory already deleted or DNE. Doing nothing.')
    elif args.target == 'baseos':
        print('Deleting base OS...')
        try:
            base_os_path = config['workDir'] + '/.builder/baseos'
            shutil.rmtree(base_os_path)
        except FileNotFoundError:
            print('Base OS directory already deleted or DNE. Doing nothing.')
    else:
        print('Trying to delete instance ' + args.target + '...')
        try:
            shutil.rmtree(config['workDir'] + '/.builder/' + args.target)
            print('Done.')
        except FileNotFoundError:
            print('Instance not found, doing nothing.')


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

    parser_update_baseos = subparser.add_parser('update-baseos', help='Update base OS or instance.')
    parser_update_baseos.set_defaults(func=update_baseos)

    parser_load_baseos = subparser.add_parser('load-baseos',
                                                help='Load base OS into build environment. '
                                                     'Note: this operation will remove the old BuildKit installation.')
    parser_load_baseos.set_defaults(func=load_baseos)

    parser_cleanup = subparser.add_parser('cleanup', help='Something feels wrong? Start everything all over again.')
    parser_cleanup.add_argument('target', help='To clean up specific instance, base os, or everything?')
    parser_cleanup.set_defaults(func=cleanup)

    args = parser.parse_args()

    if not os.path.exists(os.path.abspath(args.config_path)):
        raise IOError('Failed to read config: folder ' + os.path.abspath(args.config_path) + ' does not exists')

    with open(args.config_path + '/config.toml', 'r') as f:
        config = tomlkit.parse(f.read())

    # Prepare workdir
    if not os.path.exists(config['workDir']):
        print('Work directory does not exists, creating...')
        os.makedirs(config['workDir'])

    args.func(args)
    try:
        pass
    except AttributeError as e:
        print('Too few arguments.')
        parser.print_help()
        parser.exit()
