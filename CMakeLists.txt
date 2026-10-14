cmake_minimum_required(VERSION 3.18)
project(pcap_crowd_crush_simulation LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Scaffold only: add executable targets as each backend is implemented.
# Enable CUDA and discover MPI/OpenMP when their targets are introduced.
