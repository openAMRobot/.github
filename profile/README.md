# OpenAMRobot: the open dual-arm mobile robot anyone can teach

OpenAMRobot is a general-purpose, open-source dual-arm mobile manipulator for embodied AI. People who know the work teach the robot by demonstration (show, correct, judge) instead of writing robot code. CAD, electronics, firmware, ROS 2 software, simulation and docs are all published, so any team can build, adapt and improve it.

![OpenAMRobot 2.0](https://raw.githubusercontent.com/openAMRobot/openamrobot-docs/a6682534c14a8c063834fd20f6fc36d283cc3b56/docs/assets/openamrobot-2.0/openamrobot2_render_three_quarter_right.jpg)

▶️ **Video:** [OpenAMRobot 2.0 in simulation](https://www.youtube.com/watch?v=rQ5obdNkIZE) · 📢 **Announcement:** [Discussion #27](https://github.com/orgs/openAMRobot/discussions/27) · 📚 **Docs:** [docs.openamrobot.ai](https://docs.openamrobot.ai)

> The video shows order picking in a simulated dark store. Grocery is one use case we test with, not a limit: the same robot can be taught lab and hospital logistics, kitting, replenishment, research and teaching tasks.

## OpenAMRobot 2.0 at a glance

| | |
|---|---|
| Upper body | Two OpenArm 2.0 arms (7 DoF each) on a lift, shoulder height 1000 to 1350 mm |
| Compute | NVIDIA Jetson Orin NX; STM32H723 base controller over micro-ROS Ethernet |
| Base | Hub motors with fail-safe brakes, 25.6 V LiFePO4 105 Ah, wireless charging |
| Sensing | 2D LiDAR, depth camera, head and in-hand cameras, ultrasonic, ToF cliff sensors, IMU |
| Safety | Two E-stops cut motor power, CAN only on the robot, 1.5 m/s speed ceiling |
| Software | ROS 2, Nav2, MoveIt 2, ros2_control, browser operator UI, embodied AI pipeline (demonstration recording, ACT baseline, evaluation) |
| Size | Under 120 kg, up to 1.7 m tall |

## Timeline

- **20 Nov 2026:** v2.0.0-rc.1 pre-release (design, software, manufacturing package)
- **23 Nov to 18 Dec:** physical integration and testing in Berlin
- **18 Dec 2026:** v2.0.0 final release
- **December:** hands-on hackathon at MotionLab.Berlin
- **January 2027:** OpenAMRobot 3.0 cycle starts

Previous release: [v0.0.1 (July 2026)](https://github.com/openAMRobot/openamrobot-release/releases/tag/v0.0.1), [demo video](https://youtu.be/i6PCJFTgUF8)

## Repositories

| Repository | Purpose |
|---|---|
| [`openamr-platform-sw`](https://github.com/openAMRobot/openamr-platform-sw) | Mobile base ROS 2: simulation, navigation, docking, drivers, perception, bringup |
| [`openamr-platform-fw`](https://github.com/openAMRobot/openamr-platform-fw) | Base firmware: motors, sensors, safety I/O |
| [`openamr-platform-hw`](https://github.com/openAMRobot/openamr-platform-hw) | Base CAD, electrical, BOM, manufacturing files |
| [`openamr-upperbody-sw`](https://github.com/openAMRobot/openamr-upperbody-sw) | Arms + lift, MoveIt on the combined model, bringup |
| [`openamr-upperbody-fw`](https://github.com/openAMRobot/openamr-upperbody-fw) | End-effector and upper-body safety I/O |
| [`openamr-upperbody-hw`](https://github.com/openAMRobot/openamr-upperbody-hw) | Lift, mounting plates, wiring, BOM |
| [`openamrobot-manipulation`](https://github.com/openAMRobot/openamrobot-manipulation) | Arm framework, manipulation server, Device Package format |
| [`openamrobot-interfaces`](https://github.com/openAMRobot/openamrobot-interfaces) | Shared ROS 2 messages, services, actions, schemas |
| [`openamrobot-comm`](https://github.com/openAMRobot/openamrobot-comm) | Middleware, telemetry, transport protocols |
| [`openamrobot-ui`](https://github.com/openAMRobot/openamrobot-ui) | Operator UI and dashboards |
| [`openamrobot-docs`](https://github.com/openAMRobot/openamrobot-docs) | Documentation, onboarding, safety, compatibility |
| [`openamrobot-release`](https://github.com/openAMRobot/openamrobot-release) | Frozen, versioned releases (hardware + firmware + software + docs) |

Legacy (reference only): [`openamr`](https://github.com/openAMRobot/openamr), [`Botshare_docs`](https://github.com/openAMRobot/Botshare_docs), [`OpenAMR_UI_dev`](https://github.com/openAMRobot/OpenAMR_UI_dev), [`OpenAMR_UI_package`](https://github.com/openAMRobot/OpenAMR_UI_package), [`EOD-robot`](https://github.com/openAMRobot/EOD-robot).

## Contribute

About 20 contributors build 2.0 in the open. Start with [Discussions](https://github.com/orgs/openAMRobot/discussions), pick an issue, and read the [Contribution Guide](https://github.com/openAMRobot/.github/blob/main/CONTRIBUTING.md).

**Maintainers:** [@BotshareAI](https://github.com/BotshareAI) (Alex Reznichenko, project lead), [@panthera-momagdii](https://github.com/panthera-momagdii) (Mohamed Sayed, tech lead)

## Work with us

Botshare LTD, the company behind OpenAMRobot, offers pilots, integration, custom engineering and training around the platform. Contact: info@botshare.ai. Support the project: [GitHub Sponsors](https://github.com/sponsors/openAMRobot) or [other ways](https://github.com/openAMRobot/.github/blob/main/FUNDING.md).

## Licensing, ownership, and contributions

Software MIT, documentation CC BY 4.0, hardware CERN-OHL-P-2.0.

OpenAMRobot is a project of **Botshare LTD**. Botshare LTD owns the transferable economic rights in original OpenAMRobot materials created by or validly assigned to it. Third-party materials remain subject to their respective owners, licences, and notices.

Public availability under MIT or another applicable open-source or open-hardware licence grants the permissions stated in that licence; it does not transfer ownership of underlying copyright, trademarks, patents, or other intellectual property.

Accepted external contributions require:

1. DCO sign-off for every commit; and
2. an accepted Individual or Corporate Contributor Agreement governing assignment of transferable economic rights to Botshare LTD.

Contributor attribution and legally non-waivable authorship or moral rights remain recognized.

See the canonical [IP Policy](https://github.com/openAMRobot/.github/blob/main/IP_POLICY.md), [Contribution Guide](https://github.com/openAMRobot/.github/blob/main/CONTRIBUTING.md), and [Contributor Agreement Process](https://github.com/openAMRobot/.github/blob/main/CLA.md).

**Botshare LTD** · HE479056 · Chrysanthou Mylona 1, Panayides Building, Floor 2, Office 1, 3030 Limassol, Cyprus · info@botshare.ai · https://botshare.ai
