cmake_minimum_required(VERSION 3.11)
project(aoinb-builder)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

add_executable(aoinb-builder main.cpp container.cpp)
