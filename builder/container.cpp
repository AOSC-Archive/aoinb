#include "container.hpp"

extern "C" {
#include <sys/mount.h>
#include <string.h>
}
#include <iostream>
using namespace std;

// Some helper functions
void test_and_create(string dir) {
  if (!fs::is_directory(dir)) {
    fs::create_directories(dir);
  }
}

// Initialize static memebrs
path Container::buildkit_dir = string("");
int Container::up_containers_counter = 0;


void Container::set_buildkit_path(std::string path) {
 buildkit_dir = string(path);
}

int Container::update_buildkit() {
  if (up_containers_counter != 0) {
    string msg = "Cannot update buildkit: " + to_string(up_containers_counter) + " container still running.";
    throw msg;
  }
  string command = "systemd-nspawn -D " + string(buildkit_dir) + ' ' +
                  "apt update && apt upgrade && apt autoremove";
  return system(command.c_str());
}

void Container::add_up_counter() {
  up_containers_counter += 1;
}

void Container::reduce_up_counter() {
  up_containers_counter -= 1;
}

Container::Container(string instance_name, path base_dir) :
    instance_name(instance_name), base_dir(base_dir) {
  // First check if buildkit_dir is set.
  if (buildkit_dir == "") {
    throw "Buildkit Directory not set!";
  }

  status = Status::DOWN;
  workspace_dir = string(base_dir) + string("/" + instance_name);

  // All the following should go to $WORK_DIR/.builder/$INSTANCE/
  string instance_thing_dir = string(base_dir) + "/.builder/" + instance_name;
  instance_dir = instance_thing_dir + string("/instance");
  instance_overlay = instance_thing_dir + string("/instance-overlay");
  instance_overlay_workdir = instance_thing_dir + string("/instance-workdir");
  workspace_overlay = instance_thing_dir + string("/workspace-overlay");
  workspace_overlay_workdir = instance_thing_dir + string("/workspace-workdir");

  // And finally try to create these directories
  test_and_create(base_dir);
  test_and_create(instance_dir);
  test_and_create(instance_overlay);
  test_and_create(instance_overlay_workdir);
  test_and_create(workspace_dir);
  test_and_create(workspace_overlay);
  test_and_create(workspace_overlay_workdir);
}

Container::~Container() {
  // Make sure things are properly umount-ed.
  down();
}

void mount_overlay(path lower, path upper, path work, path desti) {
  string d_str = desti;

  string option =
      "lowerdir=" + string(lower) + ',' +
      "upperdir=" + string(upper) + ',' +
      "workdir=" + string(work);

  int r = mount("overlay", d_str.c_str(), "overlay", 0, option.c_str());

  if (r != 0) {
    string errmsg = "Mount OverlayFS error: ";
    errmsg.append(strerror(errno));
    throw errmsg;
  }
}

void umount_overlay(path target) {
  int result = umount(string(target).c_str());
  if (result != 0) {
    string errmsg = "Umount OverlayFS error: ";
    errmsg.append(strerror(errno));
    throw errmsg;
  }
}

void Container::up() {
  mount_overlay(buildkit_dir, instance_overlay, instance_overlay_workdir, instance_dir);
  mount_overlay(instance_dir, workspace_overlay, workspace_overlay_workdir, workspace_dir);

  status = Status::UP;
  add_up_counter();
}

void Container::down() {
  umount_overlay(workspace_dir);
  umount_overlay(instance_dir);

  status = Status::DOWN;
  reduce_up_counter();
}

int Container::run(std::string command) {
  string actual_command = "systemd-nspawn -D " + string(workspace_dir) + ' ' + command;
  return system(actual_command.c_str());
}

void Container::cleanup() {
  if (status == Status::UP) {
    string msg = "Cannot cleanup while container is up.";
    throw msg;
  }

  fs::remove_all(workspace_dir);
  // The previous step will also delete the directory. Need to recreate it.
  fs::create_directory(workspace_dir);
}
