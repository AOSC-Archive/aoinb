import os
from enum import Enum


class Container:
    buildkit_path = "null" # Must be set before creating any containers!
    up_containers_counter = 0

    class Status(Enum):
        DOWN = 0
        INSTANCE_UP = 1
        WORKSPACE_UP = 2

    @classmethod
    def set_buildkit_path(cls, path):
        cls.buildkit_path = path

    @classmethod
    def increase_up_container(cls):
        cls.up_containers_counter += 1

    @classmethod
    def decrease_up_container(cls):
        cls.up_containers_counter -= 1

    @classmethod
    def update_buildkit(cls):
        pass

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

    def __init__(self, name, base_dir):
        self.base_dir = base_dir
        self.instance_name = name
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
        dirs = [self.base_dir, self.workspace_dir, self.instance_dir, self.instance_overlay, self.instance_workdir,
                self.workspace_overlay, self.workspace_workdir]
        for d in dirs:
            os.makedirs(d)

        # Set the state eventually
        self.state = Container.Status.DOWN

    def workspace_up(self):
        if self.state == Container.Status.DOWN:
            Container.mount_overlay(self.buildkit_path, self.instance_overlay, self.instance_workdir, self.instance_dir)
            Container.mount_overlay(self.instance_dir, self.workspace_workdir, self.workspace_workdir, self.workspace_dir)
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

    def instance_up(self):
        if self.state == Container.Status.DOWN:
            Container.mount_overlay(self.buildkit_path, self.instance_overlay, self.instance_workdir, self.instance_dir)
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

    def __del__(self):
        if self.state == Container.Status.INSTANCE_UP:
            self.instance_down()
        elif self.state == Container.Status.WORKSPACE_UP:
            self.workspace_down()


