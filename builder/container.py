import os
import tarfile
import subprocess
import shutil
from enum import Enum


class Container(object):
    baseos_path = "null" # Must be set before creating any containers!
    up_containers_counter = 0

    class Status(Enum):
        DOWN = 0
        INSTANCE_UP = 1
        WORKSPACE_UP = 2

    @classmethod
    def set_baseos_path(cls, path):
        cls.baseos_path = path

    @classmethod
    def increase_up_container(cls):
        cls.up_containers_counter += 1

    @classmethod
    def decrease_up_container(cls):
        cls.up_containers_counter -= 1

    @classmethod
    def install_baseos(cls, tar_xz_path):
        if cls.baseos_path != 'null':
            tar = tarfile.open(tar_xz_path, "r:xz")
            tar.extractall(path=cls.baseos_path, numeric_owner=True)
        else:
            raise RuntimeError('Base OS path not set!')

    @classmethod
    def baseos_run(cls, command):
        if cls.baseos_path != 'null':
            cls.nspawn_run(cls.baseos_path, command)
        else:
            raise RuntimeError('Base OS path not set!')

    @staticmethod
    def mount_overlay(lower, upper, work, destination):
        command = "mount -t overlay overlay -o lowerdir=" + lower + ",upperdir=" + upper + ",workdir=" + work + " " + destination
        res = os.system(command)
        if res != 0:
            raise OSError("Failed to mount OverlayFS")

    @staticmethod
    def umount_overlay(path):
        command = "umount " + path
        res = os.system(command)
        if res != 0:
            raise OSError("Failed to umount OverlayF")

    @staticmethod
    def nspawn_run(dir, command):
        cmd = ['systemd-nspawn', '-D', dir] + command.split()
        # TODO: Implement logging to file
        process = subprocess.Popen(cmd, bufsize=1, universal_newlines=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        for line in process.stdout:
            print(line, end='')
        process.wait()
        errcode = process.returncode
        if errcode != 0:
            print("Process exit with code " + str(errcode))

    def __init__(self, name, base_dir):
        self.base_dir = base_dir
        self.instance_name = name
        # Prepare output dir
        self.output_dir = base_dir + "/" + "output" + "/" + name
        # Prepare exposed dir locations
        self.workspace_dir = base_dir + "/" + self.instance_name
        # Prepare hidden dir locations
        hidden_dir = base_dir + "/.builder/" + self.instance_name + "/"  # ".builder/stable/", for example
        self.instance_dir = hidden_dir + "instance"
        self.instance_overlay = hidden_dir + "instance-overlay"
        self.instance_workdir = hidden_dir + "instance-workdir"
        self.workspace_overlay = hidden_dir + "workspace-overlay"
        self.workspace_workdir = hidden_dir + "workspace-workdir"

        # And create them
        dirs = [self.base_dir, self.output_dir, self.workspace_dir, self.instance_dir, self.instance_overlay,
                self.instance_workdir, self.workspace_overlay, self.workspace_workdir]
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

        # Set the state eventually
        self.state = Container.Status.DOWN

    # dir should be the path inside the container
    def workspace_mkdir(self, dir):
        os.makedirs(self.workspace_overlay + dir)

    # destination_path should be the path inside the container
    def copy_to_workspace(self, source_path, destination_path):
        shutil.copy2(source_path, self.workspace_overlay + destination_path)

    # destination_path should be the path inside the container
    def copy_dir_to_workspace(self, source_path, destination_path):
        shutil.copytree(source_path, self.workspace_overlay + destination_path,
                        symlinks=True)

    def workspace_up(self):
        if self.state == Container.Status.DOWN:
            Container.mount_overlay(self.baseos_path, self.instance_overlay, self.instance_workdir, self.instance_dir)
            Container.mount_overlay(self.instance_dir, self.workspace_overlay, self.workspace_workdir, self.workspace_dir)
            self.state = Container.Status.WORKSPACE_UP
            self.__class__.increase_up_container()
        else:
            raise RuntimeError("Cannot bring up workspace while container is up.")

    def workspace_down(self):
        if self.state == Container.Status.WORKSPACE_UP:
            Container.umount_overlay(self.workspace_dir)
            Container.umount_overlay(self.instance_dir)
            self.state = Container.Status.DOWN
            self.__class__.decrease_up_container()
        else:
            raise RuntimeError("Cannot bring down workspace while container is not up or in other status.")

    def workspace_run(self, command):
        if self.state == Container.Status.WORKSPACE_UP:
            self.nspawn_run(self.workspace_dir, command)
        else:
            print("Workspace is not on!")

    def workspace_cleanup(self):
        if self.state == Container.Status.DOWN:
            shutil.rmtree(self.workspace_workdir)
            # Create it again :)
            os.makedirs(self.workspace_overlay)
        else:
            raise RuntimeError("Cannot cleanup workspace: containter still up.")

    # dir should be the path inside the instance container
    def instance_mkdir(self, dir):
        os.makedirs(self.instance_overlay + dir)

    # destination_path should be the path inside the instance container
    def copy_to_instance(self, source_path, destination_path):
        shutil.copy2(source_path, self.instance_overlay + destination_path)

    # destination_path should be the path inside the instance container
    def copy_dir_to_instance(self, source_path, destination_path):
        shutil.copytree(source_path, self.instance_overlay + destination_path,
                        symlinks=True)

    def instance_up(self):
        if self.state == Container.Status.DOWN:
            Container.mount_overlay(self.baseos_path, self.instance_overlay, self.instance_workdir, self.instance_dir)
            self.state = Container.Status.INSTANCE_UP
            self.__class__.increase_up_container()
        else:
            raise RuntimeError("Cannot bring up instance while container is up.")

    def instance_down(self):
        if self.state == Container.Status.INSTANCE_UP:
            Container.umount_overlay(self.instance_dir)
            self.state = Container.Status.DOWN
            self.__class__.decrease_up_container()
        else:
            raise RuntimeError("Cannot bring down instance while container is not up or in other status.")

    def instance_run(self, command):
        if self.state == Container.Status.INSTANCE_UP:
            self.nspawn_run(self.instance_dir, command)
        else:
            print("Instance is not on!")

    def __del__(self):
        if self.state == Container.Status.INSTANCE_UP:
            self.instance_down()
        elif self.state == Container.Status.WORKSPACE_UP:
            self.workspace_down()


