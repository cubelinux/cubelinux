cmake_minimum_required(VERSION 3.24)
project(discover-bootc-backend LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.10 REQUIRED COMPONENTS Core Gui)
find_package(KF6I18n 6.26 REQUIRED)
find_library(DISCOVER_COMMON_LIBRARY DiscoverCommon PATHS /usr/lib64/plasma-discover REQUIRED)

file(STRINGS "${DISCOVER_SOURCE_DIR}/CMakeLists.txt" _discover_version_line REGEX "^set\\(PROJECT_VERSION ")
string(REGEX REPLACE "^set\\(PROJECT_VERSION \"([^\"]+)\"\\).*" "\\1" DISCOVER_VERSION "${_discover_version_line}")
configure_file(DiscoverConfig.h.in "${CMAKE_CURRENT_BINARY_DIR}/DiscoverConfig.h" @ONLY)

add_library(bootc-backend MODULE BootcBackend.cpp)
target_include_directories(bootc-backend PRIVATE
    ${CMAKE_CURRENT_BINARY_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${DISCOVER_SOURCE_DIR}/libdiscover
)
target_link_libraries(bootc-backend PRIVATE
    ${DISCOVER_COMMON_LIBRARY}
    Qt6::Core
    Qt6::Gui
    KF6::I18n
)
set_target_properties(bootc-backend PROPERTIES
    PREFIX ""
    INSTALL_RPATH "/usr/lib64/plasma-discover"
)
install(TARGETS bootc-backend LIBRARY DESTINATION lib64/qt6/plugins/discover)
