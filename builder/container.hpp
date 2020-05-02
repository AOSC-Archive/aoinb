#ifndef CONTAINER_HPP
#define CONTAINER_HPP

#include <string>
#include <filesystem>

namespace fs = std::filesystem;
using fs::path;



class Container {
public:
  // buildkit_path MUST be set before using conainter.
  // Otherwise an exception will be thrown.
  static void set_buildkit_path(std::string path);
  static int update_buildkit();

  Container(std::string instance_name, path base_dir);
  ~Container();
  void up();
  void down();
  int run(std::string command);
  void cleanup();

private:
  enum Status {UP, DOWN};
  Status status = Status::DOWN; // true -> up, false -> down
  // Dual layer: base | instance | workspace
  std::string instance_name;
  path base_dir; // Where the mounuting happens
  path instance_dir;
  path instance_overlay;
  path instance_overlay_workdir;
  path workspace_dir; // Where the actual build happen
  path workspace_overlay;
  path workspace_overlay_workdir;

  static path buildkit_dir; // Extracted BuildKit
  // In order to prevent update-os during running.
  static int up_containers_counter;
  static void add_up_counter();
  static void reduce_up_counter();
};

#endif // CONTAINER_HPP
