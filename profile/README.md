# OpenAMRobot: Open Embodied AI & Mobile Manipulation Ecosystem

OpenAMRobot is an open, modular, and affordable embodied AI robotics ecosystem initiated, operated, and controlled by **Botshare LTD** (Cyprus Company ID HE479056).

The project began as an autonomous dual-arm mobile robot platform and is now evolving toward a full-cycle infrastructure for:

- mobile manipulation
- teleoperation
- imitation learning
- embodied AI research
- human-centered robot policy training
- and AI-driven robotics development

OpenAMRobot combines:

- autonomous mobile robotics
- dual-arm manipulation
- adjustable linear lift systems
- AI-based perception
- wearable embodied AI data collection
- ROS 2 software infrastructure
- embedded firmware
- simulation and navigation systems
- teleoperation and policy training pipelines
- and modular edge AI architectures

into a flexible, scalable, and research-oriented robotics ecosystem.

![Dual-arm Mobile Robot vision](https://github.com/openAMRobot/openamr/blob/main/docs/hardware/pictures/OpenAMRobot_AI_ecosystem.png)

The platform is designed not as a fixed product, but as an open and extensible infrastructure that can be adapted for:

- industrial automation
- embodied AI research
- logistics and warehouse robotics
- educational platforms
- teleoperation systems
- human-robot collaboration
- and next-generation autonomous robotic applications.

OpenAMRobot focuses on building affordable and reproducible robotics infrastructure while reducing dependence on closed proprietary ecosystems and vendor lock-in.

![Dual-arm Mobile Robot vision](https://github.com/openAMRobot/openamr/blob/main/docs/hardware/pictures/OpenAMR_10.png)

Our mission is to make advanced mobile robotics accessible by providing high-quality, open-source, production-oriented designs that help SMEs, entrepreneurs, researchers, students, and robotics specialists build reliable and affordable autonomous robots without reinventing foundational technology.

---
## Commercial Availability

OpenAMRobot is available as:

- Open-source software
- DIY development kit
- Fully assembled mobile robot
- Dual-arm Embodied AI platform
- Custom engineering project
- OEM platform

# Commercial Options

OpenAMRobot is available in multiple formats depending on your needs.

| Offering | Starting Price |
|----------|---------------:|
| Mobile Robot Platform - full initial price (components and chassis production), MIT license | **€3,500** |
| DIY Development Kit Mobile Robot Platform (assembled complete hardware, electronics, documentation & software package) | **€5,000** |
| Dual-Arm Embodied AI Robot | **from €10,000** |

> **Note:** Prices are indicative starting prices for standard configurations. Final pricing depends on hardware options, sensors, robotic arms, computing platform, manufacturing location, and customization requirements.

If you are interested in purchasing a platform or discussing your requirements, please contact us - info@botshare.ai.

## Engineering & Customization Services

Beyond the open-source platform, we help startups, SMEs, research laboratories, and enterprises develop custom robotic solutions based on OpenAMRobot.

Our services include:

- Robotics architecture and system design
- Hardware and electronics development
- PCB design and embedded firmware
- ROS 2 software development
- AI and computer vision integration
- Mechanical design and CAD
- Simulation and digital twins
- Autonomous navigation
- Mobile manipulation
- Product development
- Rapid prototyping
- Manufacturing support
- Corporate training and technical workshops

Whether you need a custom mobile robot, a proof of concept, or a complete production-ready solution, our engineering team can help accelerate your development.

---
## 🎥 Demo (release v0.0.1)

[![Watch the OpenAMRobot demo](https://img.youtube.com/vi/i6PCJFTgUF8/maxresdefault.jpg)](https://youtu.be/i6PCJFTgUF8)

▶️ **Click the image to watch the demo**

> [!NOTE]
>
> Download the complete product release (Hardware + Software + Firmware + UI + Documentation) here:
>
> **https://github.com/openAMRobot/openamrobot-release/releases/latest**

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

## Ecosystem Repository Structure

```
openAMRobot/
│
├── .github/                  # org-wide config & community health files
│
├── openamrobot-manifest      # workspace manifest: which repos + which versions
├── openamrobot-interfaces    # shared ROS 2 msgs/services/actions + device.yaml schema
├── openamrobot-comm          # comm protocols, middleware, transport
├── openamrobot-ui            # operator UI, dashboards, Device Package panels
├── openamrobot-manipulation  # arm framework + manipulation server + arm packages (franka, rebot)
├── openamrobot-docs          # central docs, onboarding, compatibility
├── openamrobot-release       # frozen, versioned product snapshots
│
├── openamr-platform-sw       # AMR ROS 2: sim, nav2, docking, control, drivers, perception
├── openamr-platform-fw       # AMR firmware: motor/sensor bridges, safety I/O
├── openamr-platform-hw       # AMR mechanical, electrical, CAD, BOM
├── openamr-upperbody-sw      # arm+lift model, lift control, MoveIt, bringup
├── openamr-upperbody-fw      # lift controller, end-effector, safety I/O
├── openamr-upperbody-hw      # lift mechanics, mounting plates, wiring, BOM

```

## Active Core Repositories

| Repository | Purpose |
|---|---|
| [`openamr`](https://github.com/openAMRobot/openamr) | Main platform repo & community entry point (being transferred into `openamr-platform-hw`) |
| [`openamr-platform-sw`](https://github.com/openAMRobot/openamr-platform-sw) | ROS 2 software: simulation, navigation, docking, drivers, perception, bringup |
| [`openamr-platform-fw`](https://github.com/openAMRobot/openamr-platform-fw) | Embedded firmware, microcontroller systems, motor interfaces, hardware communication |
| [`openamr-platform-hw`](https://github.com/openAMRobot/openamr-platform-hw) | CAD, chassis, electrical, BOMs, manufacturing files, mechatronics |
| [`openamr-upperbody-sw`](https://github.com/openAMRobot/openamr-upperbody-sw) | Arm + lift model, lift control, MoveIt on the combined model, bringup |
| [`openamr-upperbody-fw`](https://github.com/openAMRobot/openamr-upperbody-fw) | Lift controller, end-effector, upper-body safety I/O |
| [`openamr-upperbody-hw`](https://github.com/openAMRobot/openamr-upperbody-hw) | Lift mechanics, mounting plates, upper-body wiring, BOM |
| [`openamrobot-manipulation`](https://github.com/openAMRobot/openamrobot-manipulation) | Arm-integration framework: manipulation server, Device Package format, reference arm packages (Franka, ReBot) |
| [`openamrobot-interfaces`](https://github.com/openAMRobot/openamrobot-interfaces) | Shared ROS 2 messages, services, actions, schemas, interface contracts |
| [`openamrobot-comm`](https://github.com/openAMRobot/openamrobot-comm) | APIs, middleware, telemetry, transport protocols, interoperability |
| [`openamrobot-ui`](https://github.com/openAMRobot/openamrobot-ui) | Operator interfaces, dashboards, visualization, user-facing apps |
| [`openamrobot-docs`](https://github.com/openAMRobot/openamrobot-docs) | Central documentation, onboarding, tutorials, safety, compatibility |

## Legacy Repositories

These repositories are preserved for historical context, migration support, forks, and compatibility reference. Active development targets the modular ecosystem repositories above. Repositories explicitly marked **archived** by GitHub are read-only.

- [`OpenAMR_UI_dev`](https://github.com/openAMRobot/OpenAMR_UI_dev) — archived; superseded by `openamrobot-ui`
- [`OpenAMR_UI_package`](https://github.com/openAMRobot/OpenAMR_UI_package) — archived; superseded by `openamrobot-ui`
- [`Botshare_docs`](https://github.com/openAMRobot/Botshare_docs) — legacy documentation source; superseded by `openamrobot-docs`
- [`EOD-robot`](https://github.com/openAMRobot/EOD-robot) — archived legacy EOD variant
>
> Active development should target the modular ecosystem repositories listed above.

---

## OEM & Partnership Opportunities

We welcome collaboration with:

- Robotics startups
- Universities
- Research institutes
- System integrators
- Industrial automation companies
- Manufacturing partners

Potential collaboration models include:

- OEM manufacturing
- White-label platforms
- Joint product development
- Technology transfer
- University education programs
- Industrial pilot projects

---

## Project Aim

While maintaining its original goals of accessibility and modularity, OpenAMRobot is evolving toward human-centric mobile robotics.

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

## Looking for a Custom Robot?

Need something beyond the standard platform?

We can customize OpenAMRobot for your application, including:

- custom chassis
- additional sensors
- robotic arms
- lifting mechanisms
- industrial I/O
- safety systems
- custom operator interfaces
- cloud integration
- fleet management
- AI and computer vision

Get in touch to discuss your project.

## Who Uses OpenAMRobot?

OpenAMRobot is designed for:

- Robotics startups
- Universities
- Research laboratories
- Corporate R&D teams
- Industrial automation companies
- System integrators
- SMEs exploring robotics
- AI and Embodied AI developers

# For Companies

OpenAMRobot is more than an open-source project.

We partner with companies to accelerate robotics development through:

- Engineering consulting
- Product architecture reviews
- Custom robot development
- Rapid prototyping
- Pilot projects
- Technology transfer
- Corporate training
- Manufacturing support
- Long-term R&D partnerships

Whether you're building your first robot or expanding an existing product, OpenAMRobot provides a proven foundation that can significantly reduce development time and cost.

---

### Quick Start for Contributors

1. Fork the relevant repository
2. Create a new branch
3. Make changes following project guidelines
4. Submit a Pull Request

Please read the repository-specific `CONTRIBUTING.md` before submitting contributions.

---

## Recognition of Contributors

OpenAMRobot is built by people, and contributors are always credited.

We recognize contributors through:

- GitHub commit history
- pull requests
- contributors lists
- documentation acknowledgements
- release notes
- maintainer roles for long-term contributors

---

## Maintainers

Maintainers are contributors who:

- actively review pull requests
- help guide technical decisions
- support the community
- improve architecture and governance

Maintainer roles are earned through contribution and trust.

## Maintainer

- **[@rajindulkar22](https://github.com/rajindulkar22)** — Project Maintainer

## Contributors

A sincere thank you to our contributors for their valuable time, effort, and contributions to the project:

- **[@Nahush11](https://github.com/Nahush11)**
- **[@SHuttooo](https://github.com/SHuttooo)**

---

## Support OpenAMRobot

Support:

- open-source robotics
- ROS 2 development
- AI robotics education
- dual-arm mobile robot research
- affordable robotics infrastructure

## 💜 Support OpenAMRobot

Support open-source robotics, ROS 2 development, AI robotics education, and dual-arm mobile robot research.

### ⚡ Back the build — one-time, no strings

| Tier | What it says about you | Link |
|---|---|---|
| ⚡ **First Mover - €5** | You got here first, and you didn't overthink it. Your name goes on the backers wall - permanently - as one of the people who moved before it was obvious. Five euros, one good instinct. | <a href="https://buy.stripe.com/eVqcN5b99eeAaSd7WPgUM06" target="_blank" rel="noopener noreferrer">💳&nbsp;Back&nbsp;it&nbsp;→</a> |
| 🎯 **Sharpshooter - €25** | You spotted it early and called it. Name on the wall + a shareable "OpenAMRobot Backer" badge - proof you saw it coming while everyone else was still scrolling. | <a href="https://buy.stripe.com/4gMdR9ell1rO2lH90TgUM07" target="_blank" rel="noopener noreferrer">💳&nbsp;Back&nbsp;it&nbsp;→</a> |
| 🕶️ **Insider - €50** | You want in behind the curtain. Everything above + the backer-only build log and early files - every breakthrough, every faceplant, unfiltered. You see it before the internet does. | <a href="https://buy.stripe.com/eVq14nfpp4E0gcx2CvgUM08" target="_blank" rel="noopener noreferrer">💳&nbsp;Back&nbsp;it&nbsp;→</a> |
| 🔩 **Immortal - €100** | Your name goes on the actual robot. Physically. Forever. A machine will roll around carrying your name long after any of us remember why - and you'll have the photo to prove you were there. | <a href="https://buy.stripe.com/00w00jdhhb2o4tPfphgUM09" target="_blank" rel="noopener noreferrer">💳&nbsp;Back&nbsp;it&nbsp;→</a> |
| 🏆 **Founding Backer - €250** | Not merely a supporter — a founding backer. Everything above + a personal thank-you in a build video. When this becomes something, you were one of the people who decided it would. | <a href="https://buy.stripe.com/28EeVdcdddawaSdeldgUM0a" target="_blank" rel="noopener noreferrer">💳&nbsp;Back&nbsp;it&nbsp;→</a> |

### 🔁 Monthly subscriptions — build it with us, every month

| Tier | What you get | Link |
|---|---|---|
| 😇 **Benefactor - €5/mo** | This month, officially not wasted. €5 to help build an open robot for everyone - cheaper than the coffee you'll forget you bought. Your name goes on the wall. History will remember you - well, me for sure. 🤖 | <a href="https://buy.stripe.com/9B6cN5dhh9Yk7G1cd5gUM05" target="_blank" rel="noopener noreferrer">💳&nbsp;Subscribe&nbsp;→</a> |
| ❤️ **Community - €19/mo** | You're in. Community access, project & roadmap updates, basic documentation, and community Q&A. (Private consultation not included.) | <a href="https://buy.stripe.com/6oUcN55OPc6s3pL4KDgUM00" target="_blank" rel="noopener noreferrer">💳&nbsp;Subscribe&nbsp;→</a> |
| 🔧 **Builder - €79/mo** | For the ones who actually build. Everything in Community + builder docs, monthly group Q&A, selected tutorials, early design updates, and discounts on digital packs. (Private consultation not included.) | <a href="https://buy.stripe.com/14A28r0uvdaw9O9eldgUM01" target="_blank" rel="noopener noreferrer">💳&nbsp;Subscribe&nbsp;→</a> |
| 🚀 **Pro Support - €299/mo** | Expert support for advanced builders, early founders, and small labs. Includes 1 private consulting call per month and up to 3 hours/month of technical guidance. | <a href="https://buy.stripe.com/dRm4gz4KLdaw6BX4KDgUM02" target="_blank" rel="noopener noreferrer">💳&nbsp;Subscribe&nbsp;→</a> |
| 🏢 **Startup Support - €750/mo** | For robotics startups and teams heading toward a prototype. Includes 2 private consulting calls per month, roadmap support, GitHub/documentation review, supplier review, and up to 6 hours/month. | <a href="https://buy.stripe.com/7sY8wPfpp8Ugf8t90TgUM03" target="_blank" rel="noopener noreferrer">💳&nbsp;Subscribe&nbsp;→</a> |
| 🔬 **Lab Support - €1,500/mo** | For universities, corporate labs, and training centers. Includes 4 private sessions per month, lab implementation support, architecture reviews, training-roadmap support, and up to 10 hours/month. | <a href="https://buy.stripe.com/eVq14ndhh2vSaSda4XgUM04" target="_blank" rel="noopener noreferrer">💳&nbsp;Subscribe&nbsp;→</a> |

**❤️ GitHub Sponsors:** <a href="https://github.com/sponsors/openAMRobot" target="_blank" rel="noopener noreferrer"> 🐙 &nbsp;github.com/sponsors/openAMRobot&nbsp;→</a>

*Every contribution - €5 or €1,500 - literally builds this robot. No billion-dollar lab required. **You're not merely donating. You're helping build it.** 🤖*

---

## Planned releases (next 6 months)

- Carrier PCB (compute + power + sensors)
  - Current discussion: https://github.com/orgs/openAMRobot/discussions/9

- Hub-motor drivetrain with suspension
  - mechanical + control integration

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

## Licensing, ownership, and contributions

OpenAMRobot is a project of **Botshare LTD**. Botshare LTD owns the transferable economic rights in original OpenAMRobot materials created by or validly assigned to it. Third-party materials remain subject to their respective owners, licences, and notices.

Public availability under MIT or another applicable open-source or open-hardware licence grants the permissions stated in that licence; it does not transfer ownership of underlying copyright, trademarks, patents, or other intellectual property.

Accepted external contributions require:

1. DCO sign-off for every commit; and
2. an accepted Individual or Corporate Contributor Agreement governing assignment of transferable economic rights to Botshare LTD.

Contributor attribution and legally non-waivable authorship or moral rights remain recognized.

See the canonical [IP Policy](https://github.com/openAMRobot/.github/blob/main/IP_POLICY.md), [Contribution Guide](https://github.com/openAMRobot/.github/blob/main/CONTRIBUTING.md), and [Contributor Agreement Process](https://github.com/openAMRobot/.github/blob/main/CLA.md).

**Botshare LTD** · HE479056 · Chrysanthou Mylona 1, Panayides Building, Office 1, 3030 Limassol, Cyprus · alex@botshare.ai · https://botshare.ai
