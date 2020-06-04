import os
import shutil
from components.container import Container


def build(work_dir, config_path, package_path, branch):
    import resource

    if not os.path.exists(package_path):
        raise IOError('Failed to read package bundle: folder does not exists.')

    baseos_dir = work_dir + "/.builder/baseos/"
    if not os.path.exists(baseos_dir):
        raise IOError("BuildKit does not exists, cannot proceed.")

    Container.set_baseos_path(baseos_dir)
    c = Container(branch, work_dir)

    # Prepare instance for first time use
    if not os.path.exists(c.instance_overlay + '/etc/apt/sources.list'):
        print('source.list not found in instance. Copying from config path.')
        source_list_path = config_path + '/source_lists/' + branch + '.list'
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
    c.copy_dir_to_workspace(os.path.abspath(package_path), '/buildroot/bundle')
    # Copy toolbox
    c.copy_dir_to_workspace(os.path.abspath('./toolbox'), '/buildroot/toolbox')
    # Run the build script
    c.workspace_up()
    c.workspace_run('/buildroot/toolbox/build.sh', [])
    c.workspace_down()
    # Print usage info
    print(resource.getrusage(resource.RUSAGE_CHILDREN))
    # Copy result to result folder
    output_path = work_dir + '/output/' + branch
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    for f in os.listdir(c.workspace_overlay + '/buildroot/output'):
        print(output_path)
        shutil.copy(c.workspace_overlay + '/buildroot/output/' + f, output_path)

    c.workspace_cleanup()


def update_baseos(work_dir):
    print('Updating base OS...')
    baseos_dir = work_dir + "/.builder/baseos/"
    if not os.path.exists(baseos_dir):
        raise IOError("BuildKit does not exists, cannot proceed.")
    Container.set_baseos_path(baseos_dir)

    Container.baseos_run('apt-get update --quiet', ['DEBIAN_FRONTEND=noninteractive'])
    Container.baseos_run('apt-get upgrade -y --quiet', ['DEBIAN_FRONTEND=noninteractive'])
    Container.baseos_run('apt-get clean -y --quiet', ['DEBIAN_FRONTEND=noninteractive'])


def load_baseos(work_dir, arch):
    baseos_dir = work_dir + "/.builder/baseos/"
    Container.set_baseos_path(baseos_dir)

    # Remove the old baseos
    if os.path.exists(baseos_dir):
        shutil.rmtree(baseos_dir)

    tar_xz_path = work_dir + "/buildkit_" + arch + ".tar.xz"
    if not os.path.exists(tar_xz_path):
        import urllib.request
        print("Downloading BuildKit from repo.aosc.io...")
        baseos_url = "https://repo.aosc.io/aosc-os/os-" + arch + "/buildkit/aosc-os_buildkit_latest_amd64.tar.xz"
        # urlretriveve is considered a legacy interface, but for convenience it is used here.
        urllib.request.urlretrieve(baseos_url, tar_xz_path)

    # Now extract it
    print('Extracting base OS...')
    Container.install_baseos(tar_xz_path)


def cleanup(work_dir, target):
    if target == 'all':
        print('Deleting everything in the work directory...')
        try:
            shutil.rmtree(work_dir + "/.builder")
            print('Done.')
        except FileNotFoundError:
            print('Work directory already deleted or DNE. Doing nothing.')
    elif target == 'baseos':
        print('Deleting base OS...')
        try:
            base_os_path = work_dir + '/.builder/baseos'
            shutil.rmtree(base_os_path)
        except FileNotFoundError:
            print('Base OS directory already deleted or DNE. Doing nothing.')
    else:
        print('Trying to delete instance ' + target + '...')
        try:
            shutil.rmtree(work_dir + '/.builder/' + target)
            print('Done.')
        except FileNotFoundError:
            print('Instance not found, doing nothing.')
