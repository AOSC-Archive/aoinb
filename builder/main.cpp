#include <string>
#include <iostream>
#include "container.hpp"

using namespace std;
int main(int argc, char **argv) {
  // This program is only used for playing around for now.
  if (argc <= 2) {
    cout << "This program is only used for playing around for now." << endl;
    cout << "Useage: aoinb-build WORK_PATH BUILDKIT_PATH" << endl;
    return 1;
  }

  string work_path = argv[1];
  string buildkit_path = argv[2];
  try {
    // MUST be set before creating any Container objects.
    Container::set_buildkit_path(buildkit_path);
    // Initialize container stable. Create directory structure. Use base folder "buildkit_dir".
    Container stable{"stable", work_path};
    // Mount OverlayFS.
    cout << "Try to mount container: stable." << endl;
    stable.up();
    // Trigger systemd-nspawn to run command "update".
    stable.run("cat /etc/os-release");
    // Umount OverlayFS.
    stable.down();
    // Try to update during up
    Container::update_buildkit();
  } catch (string e) {
    cout << "Exception caught!" << endl;
    cout << e << endl;
  }
}
