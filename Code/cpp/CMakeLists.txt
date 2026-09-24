cmake_minimum_required(VERSION 3.26)

if(POLICY CMP0167)
    cmake_policy(SET CMP0167 NEW)
endif()

project(nd_adjustment LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(HighFive REQUIRED)
find_package(Eigen3 REQUIRED)


add_executable(nda
    src/main.cpp
    src/glls.cpp
    src/linSolve.cpp
    src/input_parser.cpp
    src/output_hdf5.cpp
)

target_include_directories(nda
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(nda
    PRIVATE
    HighFive
    Eigen3::Eigen
)