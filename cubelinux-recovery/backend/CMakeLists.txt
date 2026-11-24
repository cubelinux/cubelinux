cmake_minimum_required(VERSION 3.20)
project(cubelinux_recovery_backend LANGUAGES CXX)

find_package(Qt6 6.6 REQUIRED COMPONENTS Core)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(cubelinux-recovery-common STATIC recovery-common.cpp)
target_link_libraries(cubelinux-recovery-common PUBLIC Qt6::Core)
target_compile_options(cubelinux-recovery-common PRIVATE -Wall -Wextra -Wpedantic)

add_executable(cubelinux-recovery-reboot recovery-reboot.cpp)
target_link_libraries(cubelinux-recovery-reboot PRIVATE cubelinux-recovery-common Qt6::Core)
target_compile_options(cubelinux-recovery-reboot PRIVATE -Wall -Wextra -Wpedantic)

add_executable(cubelinux-recovery-update recovery-update.cpp)
target_link_libraries(cubelinux-recovery-update PRIVATE cubelinux-recovery-common Qt6::Core)
target_compile_options(cubelinux-recovery-update PRIVATE -Wall -Wextra -Wpedantic)

install(TARGETS cubelinux-recovery-reboot cubelinux-recovery-update
    RUNTIME DESTINATION libexec)
