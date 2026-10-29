FROM ros:jazzy-ros-base@sha256:066420e07f60aa18262f2479981def87ebcfcec42eefb0c0c57c4a46098348ca

ARG DEBIAN_FRONTEND=noninteractive

# LiDAR driver policy:
# Do not install the legacy ros-jazzy-rplidar-ros package in this baseline.
# OpenAMRobot 2.0 targets RPLIDAR S3 using sllidar_ros2.
# The S3 source driver is being pinned via openamrobot-manifest PR #18;
# its installation and hardware validation are separate from this baseline.
# camera_ros is intentionally retained for the existing robot: the
# openamrobot_perception/package.xml declares an exec_depend on camera_ros,
# and its IMX708 real-robot launch runs camera_ros/camera_node.
# OpenAMRobot 2.0's Gemini 336L/Orbbec path has separate driver integration.
#
# Common CI and ROS workspace tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    git \
    curl \
    \
    # Platform ROS dependencies \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-common \
    ros-jazzy-slam-toolbox \
    ros-jazzy-nav2-bt-navigator \
    ros-jazzy-nav2-behaviors \
    ros-jazzy-nav2-controller \
    ros-jazzy-nav2-lifecycle-manager \
    ros-jazzy-nav2-map-server \
    ros-jazzy-nav2-amcl \
    ros-jazzy-nav2-planner \
    ros-jazzy-nav2-smoother \
    ros-jazzy-nav2-waypoint-follower \
    ros-jazzy-nav2-velocity-smoother \
    ros-jazzy-nav2-collision-monitor \
    ros-jazzy-opennav-docking \
    ros-jazzy-laser-filters \
    ros-jazzy-rviz2 \
    ros-jazzy-twist-mux \
    ros-jazzy-camera-ros \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-xacro \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-apriltag-msgs \
    ros-jazzy-apriltag-ros \
    ros-jazzy-nav2-msgs \
    ros-jazzy-robot-localization \
    ros-jazzy-topic-tools \
    ros-jazzy-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp