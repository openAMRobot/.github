# OpenAMRobot

## Open Embodied AI Ecosystem

> ![OpenAMRobot Ecosystem](https://github.com/openAMRobot/openamr/blob/main/docs/hardware/pictures/OpenAMRobot_AI_ecosystem.png)

OpenAMRobot is an open, modular, and affordable embodied AI robotics ecosystem focused on:

- Mobile Manipulation
- Teleoperation
- Imitation Learning
- Vision-Language-Action (VLA) Robotics
- Human-Centered Robot Policy Training

The project combines:
- ROS 2 based robotics
- Dual-arm mobile manipulation
- Wearable AI data collection
- AI training & simulation pipelines
- Open-source hardware & software infrastructure

---

# Open Embodied AI Pipeline

Human Demonstration  
→ Wearable AI Kit  
→ Dataset Generation  
→ Policy Training  
→ Simulation  
→ ROS 2 Execution  
→ Real-World Deployment  
→ Feedback & Improvement

---

# Core Architecture

## 1. Wearable AI Data Collection Kit

Human demonstration and teleoperation system designed for embodied AI research.

### Components
- RGB-D Head Camera
- IMU Tracking (Head / Body / Wrists)
- Optional Wrist Cameras
- Optional EOG-based Gaze Estimation
- Backpack Edge Compute Unit

### Goals
- Human Demonstration Recording
- Teleoperation
- Dataset Generation
- Shared Autonomy
- Robot Policy Training

---

## 2. OpenAMRobot Platform

ROS 2 based mobile manipulation platform.

### Robot Components
- Dual 6-DoF Arms
- Mobile Base
- Depth Cameras
- RGB Cameras
- 3D LiDAR
- IMU Sensors

### Capabilities
- Navigation
- Manipulation
- Teleoperation
- Human-Robot Collaboration
- Autonomous Task Execution

---

# AI & VLA Stack

## AI Training
- Imitation Learning
- Behavior Cloning
- Policy Learning
- Diffusion / Transformer Policies

## Vision-Language-Action (VLA)
Vision  
→ Language  
→ Action

### Current Direction
- High-Level Policy Inference
- Long-Horizon Task Execution
- Shared Autonomy
- Human-Centered Robot Learning

### Technologies
- NVIDIA GR00T (optional)
- NVIDIA Isaac Lab (optional)
- NVIDIA Isaac Sim (optional)

---

# Compute Architecture

## Low-Level Control
- STM32 / Teensy / MCU
- Motors
- Encoders
- Safety I/O

## Mid-Level Compute
- Raspberry Pi 5
- Navigation
- SLAM
- ROS 2 System Management

## High-Level AI Compute
- NVIDIA Jetson Orin / Orin NX
- Perception
- Manipulation
- VLA / Policy Inference

## Wearable Edge Compute
- RK3588-based Modules (optional)
- Sensor Fusion
- Data Synchronization
- Streaming & Compression

---

# Software Stack

## Robotics
- ROS 2
- MoveIt 2
- Nav2
- TF2
- rosbag2

## AI / ML
- PyTorch
- OpenCV
- CUDA
- HuggingFace Transformers

## Simulation
- Gazebo
- NVIDIA Isaac Sim (optional)
- NVIDIA Isaac Lab (optional)

---

# Key Principles

- Open Source
- Modular
- Affordable
- DIY Friendly
- Research Oriented
- Human-Centered
- Reduced Vendor Lock-In

---

# Roadmap

## Phase 1
Open Mobile Robot Platform
- Navigation
- SLAM
- Mobile Manipulation

## Phase 2
Teleoperation & Data Pipeline
- Wearable AI Kit
- Human Demonstration
- Dataset Generation

## Phase 3
Imitation Learning & Policies
- Policy Training
- Simulation Integration
- VLA Experiments

## Phase 4
Shared Autonomy & Embodied AI
- Human-Robot Collaboration
- Long-Horizon Tasks
- Semi-Autonomous Manipulation

## Phase 5
Open Ecosystem & Community
- Open Datasets
- Research Collaboration
- Educational Infrastructure

---

# Mission

Democratize embodied AI and robotics by building open, affordable, and scalable infrastructure for the next generation of intelligent robotic systems.

