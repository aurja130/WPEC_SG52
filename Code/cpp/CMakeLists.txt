cmake_minimum_required(VERSION 3.26)

project(nd_adjustment LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(HighFive REQUIRED)

add_executable(nda
    src/main.cpp
    src/glls.cpp
    src/linSolve.cpp
)

target_include_directories(nda
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(nda
    PRIVATE
    HighFive
)