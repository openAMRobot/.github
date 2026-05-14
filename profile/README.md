## Hi there 👋

# OpenAMRobot: affordable Autonomous Dual-arm Mobile Robot

OpenAMRobot is an affordable, open-source autonomous dual-arm mobile robot platform developed by the Botshare robotics team.

The project focuses on building a modular, end-to-end mobile manipulation ecosystem that combines:

- autonomous mobile robotics
- robotic arm integration
- adjustable linear lift systems
- AI-based perception
- ROS 2 software infrastructure
- embedded firmware
- operator interfaces
- simulation and navigation systems

into a flexible, production-oriented robotics platform.

OpenAMRobot is designed not as a fixed product, but as a modular ecosystem that can be adapted, extended, and deployed across different industrial, research, logistics, educational, and service robotics scenarios.

![Dual-arm Mobile Robot vision](https://github.com/openAMRobot/openamr/blob/main/docs/hardware/pictures/OpenAMR_10.png)

Our mission is to make advanced mobile robotics accessible by providing high-quality, open-source, production-oriented designs that help SMEs, entrepreneurs, researchers, students, and robotics specialists build reliable and affordable autonomous robots without reinventing foundational technology.

---

> [!IMPORTANT]
> ## OpenAMRobot Ecosystem Architecture
>
> OpenAMRobot is transitioning from a monolithic repository structure into a modular robotics ecosystem focused on:
>
> - maintainability
> - scalability
> - interoperability
> - contributor onboarding
> - long-term open-source collaboration
> - simulation-first robotics development
>
> ![OpenAMRobot Ecosystem](https://github.com/openAMRobot/openamr/blob/main/docs/hardware/pictures/OpenAMRobot_ecosystem.png)
>
> ### Active Core Repositories
>
> | Repository | Purpose |
> |---|---|
> | [`openamr`](https://github.com/openAMRobot/openamr) | Main OpenAMRobot platform repository and community entry point |
> | [`openamr-platform-sw`](https://github.com/openAMRobot/openamr-platform-sw) | ROS 2 software, simulation, navigation, docking, drivers, perception, and robot bringup |
> | [`openamr-platform-fw`](https://github.com/openAMRobot/openamr-platform-fw) | Embedded firmware, low-level microcontroller systems, motor interfaces, and hardware communication |
> | [`openamr-platform-hw`](https://github.com/openAMRobot/openamr-platform-hw) | CAD, chassis, electrical systems, BOMs, manufacturing files, and mechatronics |
> | [`openamrobot-interfaces`](https://github.com/openAMRobot/openamrobot-interfaces) | Shared ROS 2 messages, services, actions, schemas, and interface contracts |
> | [`openamrobot-comm`](https://github.com/openAMRobot/openamrobot-comm) | APIs, middleware, telemetry, transport protocols, interoperability, and communication infrastructure |
> | [`openamrobot-ui`](https://github.com/openAMRobot/openamrobot-ui) | Operator interfaces, dashboards, visualization tools, and user-facing applications |
> | [`openamrobot-docs`](https://github.com/openAMRobot/openamrobot-docs) | Central documentation, onboarding, tutorials, safety, compatibility matrices, and contributor documentation |
>
> ### Platform Direction
>
> OpenAMRobot is evolving toward:
>
> - dual-arm autonomous mobile robotics
> - human-centric mobile manipulation
> - modular ROS 2 robotics infrastructure
> - AI-assisted perception and interaction
> - fleet-ready robotics systems
> - simulation-first development
> - affordable and production-oriented open robotics
>
> ### Legacy Repositories
>
> The following repositories are considered legacy repositories and are preserved primarily for:
>
> - historical context
> - migration support
> - forks
> - archived development history
> - compatibility references
>
> Legacy repositories:
>
> - [`EOD-robot`](https://github.com/openAMRobot/EOD-robot)
> - [`OpenAMR_UI_dev`](https://github.com/openAMRobot/OpenAMR_UI_dev)
> - [`OpenAMR_UI_package`](https://github.com/openAMRobot/OpenAMR_UI_package)
> - [`OpenAMR_UI`](https://github.com/openAMRobot/OpenAMR_UI)
> - [`Botshare_docs`](https://github.com/openAMRobot/Botshare_docs)
>
> Active development should target the new modular ecosystem repositories listed above.

---

## Planned releases (next 6 months)

- OpenAMRobot organization ecosystem structure
  - Current discussion:
  - https://github.com/orgs/openAMRobot/discussions/15

- Carrier PCB (compute + power + sensors)
  - Current discussion:
  - https://github.com/orgs/openAMRobot/discussions/9

- Autodocking + wireless charging
  - ROS 2 package & routines
  - Current discussion:
  - https://github.com/orgs/openAMRobot/discussions/13

- Hub-motor drivetrain with suspension
  - mechanical + control integration

- Operator UI (ROS 2)
  - teleoperation
  - maps
  - telemetry
  - waypoints
  - logs
  - https://github.com/openAMRobot/openamrobot-ui

- Robotic arm integration and linear lift integration
  - mounts
  - drivers
  - wiring
  - examples

- ML-based computer vision
  - object recognition
  - grasp cues
  - perception pipelines

- Complete documentation
  - hardware
  - wiring diagrams
  - BOMs
  - assembly procedures
  - testing workflows

- Training and upskilling materials
  - robotics
  - ROS 2
  - AI
  - embedded systems
  - mechatronics

---

A key focus of the next development phase is AI-based perception and intuitive human-robot interaction.

Depth-camera-driven computer vision enables:

- reliable navigation
- object recognition
- pick-and-place assistance
- operator guidance
- task supervision
- dynamic environment interaction

while higher-level interaction tools aim to simplify:

- configuration
- deployment
- supervision
- diagnostics
- workflow reconfiguration

for SMEs and robotics integrators.

OpenAMRobot continues to prioritize:

- open development
- affordability
- modularity
- production-oriented engineering
- maintainability
- practical deployment

As an open-source initiative, the platform remains broadly applicable across multiple industrial and research niches while being validated through concrete real-world use cases.

Join us to prototype, adapt, and deploy OpenAMRobots — together.

---

# Support OpenAMRobot

Support:

- open-source robotics
- ROS 2 development
- AI robotics education
- dual-arm mobile robot research
- affordable robotics infrastructure

## Monthly subscriptions

| Tier | Price | Link |
|---|---:|---|
| Community | €19/month | <a href="https://buy.stripe.com/6oUcN55OPc6s3pL4KDgUM00" target="_blank">Subscribe</a> |
| Builder | €79/month | <a href="https://buy.stripe.com/14A28r0uvdaw9O9eldgUM01" target="_blank">Subscribe</a> |
| Pro Support | €299/month | <a href="https://buy.stripe.com/dRm4gz4KLdaw6BX4KDgUM02" target="_blank">Subscribe</a> |
| Startup Support | €750/month | <a href="https://buy.stripe.com/7sY8wPfpp8Ugf8t90TgUM03" target="_blank">Subscribe</a> |
| Lab Support | €1,500/month | <a href="https://buy.stripe.com/eVq14ndhh2vSaSda4XgUM04" target="_blank">Subscribe</a> |

GitHub Sponsors:
https://github.com/sponsors/openAMRobot

Every contribution, big or small, helps us grow. Thank you for your support!

---

# Project Aim

OpenAMRobot is evolving toward human-centric mobile robotics.

The platform emphasizes:

- shoulder-to-shoulder collaboration with human operators
- operator-in-the-loop control
- task handover
- assistance-oriented robotics
- modular automation systems

rather than isolated or rigid automation.

Robotic arm integration and height-adjustable linear actuators are treated as enabling components that allow the robot to adapt ergonomically to different tasks, workstations, and human collaborators.

The platform bridges:

- real-world deployment
- research
- education
- AI robotics
- industrial automation
- embodied AI experimentation

while addressing practical automation challenges in:

- manufacturing
- logistics
- CEP
- grocery delivery
- warehouse automation
- industrial assistance workflows

---

## Our system is built to

### Advance intelligent automation

Integrate computer vision and ML for:

- perception
- object recognition
- adaptive grasping
- autonomous assistance

in dynamic environments.

### Enable modular versatile manipulation

Combine:

- dual-arm robotic architecture
- interchangeable payload systems
- open hardware design
- modular ROS 2 software

for flexibility and customization.

### Remain open and cost-efficient

Target affordable and reproducible robotics technology suitable for:

- research
- education
- prototyping
- SMEs
- startups
- robotics labs

---

# Get involved

OpenAMRobot is an open collaboration.

You can contribute by:

- reporting bugs or issues
- proposing improvements
- submitting pull requests
- improving documentation
- improving tutorials
- contributing hardware
- contributing firmware
- contributing ROS 2 software
- contributing AI and CV pipelines
- improving simulation infrastructure

## Quick Start for Contributors

1. Fork the relevant repository
2. Create a new branch
3. Make changes following project guidelines
4. Submit a Pull Request

Please read the repository-specific `CONTRIBUTING.md` before submitting contributions.

---

# Recognition of Contributors

OpenAMRobot is built by people, and contributors are always credited.

We recognize contributors through:

- GitHub commit history
- pull requests
- contributors lists
- documentation acknowledgements
- release notes
- maintainer roles for long-term contributors

---

# Maintainers

Maintainers are contributors who:

- actively review pull requests
- help guide technical decisions
- support the community
- improve architecture and governance

Maintainer roles are earned through contribution and trust.

---

# Useful resources

- [`openamrobot-docs`](https://github.com/openAMRobot/openamrobot-docs)
- [`openamr-platform-sw`](https://github.com/openAMRobot/openamr-platform-sw)
- [`openamrobot-ui`](https://github.com/openAMRobot/openamrobot-ui)
- [`openamrobot-interfaces`](https://github.com/openAMRobot/openamrobot-interfaces)
- [`openamrobot-comm`](https://github.com/openAMRobot/openamrobot-comm)
- [`openamr-platform-fw`](https://github.com/openAMRobot/openamr-platform-fw)
- [`openamr-platform-hw`](https://github.com/openAMRobot/openamr-platform-hw)

---

# Fun facts

- The project originated from long-term robotics R&D work in Kharkiv, Ukraine.
- Development continues through collaboration between researchers, students, engineers, and robotics enthusiasts.
- The ecosystem strongly emphasizes affordability, openness, modularity, and practical deployment.

---

# License and Rights

## License

Most repositories are currently licensed under the MIT License unless stated otherwise.

See repository-specific LICENSE files for details.

## Rights and Contributions

- Contributors retain copyright to their individual contributions.
- By contributing, contributors allow the OpenAMRobot ecosystem to use, modify, and distribute contributions under the repository license.
- The OpenAMRobot organization coordinates long-term ecosystem stewardship and infrastructure development.

We are not restricting you with IP — we are enabling you with our groundwork.
