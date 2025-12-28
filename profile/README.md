## Hi there 👋

# OpenAMRobot: affordable Autonomous Dual-arm Mobile Robot

OpenAMRobot is an affordable, open-source autonomous dual-arm mobile robot platform developed by a robotics team at the Mechatronics Lab of BHT University (Berlin). The project focuses on building a modular, end-to-end mobile manipulation system that combines a mobile base, robotic arm integration, adjustable linear lift for the arms, and AI-based perception into a single, production-oriented architecture. OpenAMRobot is designed not as a fixed product, but as a flexible platform that can be adapted, extended, and deployed across different industrial and research scenarios.

Our mission is to make advanced mobile robotics accessible by providing high-quality, open-source, production-oriented designs that help SMEs, entrepreneurs, and specialists build reliable, affordable autonomous robots without reinventing foundational technology.

**Planned releases (next 6 months):**
- Carrier PCB (compute + power + sensors) [Сurrent discussion](https://github.com/orgs/openAMRobot/discussions/9)
- Autodocking + wireless charging (ROS2 package & routines) [Сurrent discussion](https://github.com/orgs/openAMRobot/discussions/13)
- Hub-motor drivetrain with suspension (mechanical + control)
- Operator UI (ROS2) for teleop, maps, telemetry, way points and logs
- Robotic arm integration and linear lift integration (mounts, drivers, wiring, examples)
- ML-based CV for object recognition & grasp cues
_____________________________________________________________________
- Complete documentation: HW/Wiring diagrams, BOMs, assembly & tests
- Training and upskilling notes: learning guides for each subsystem

A key focus of the next development phase is AI-based perception and intuitive human-robot interaction. Depth-camera-driven computer vision enables reliable navigation, object recognition, and pick-and-place assistance in dynamic environments, while higher-level interaction tools aim to simplify configuration, supervision, and task reconfiguration for SMEs. OpenAMRobot continues to prioritize open, cost-efficient, and production-ready designs, targeting practical deployment, straightforward maintenance, and rapid adaptation to new workflows without requiring deep robotics expertise. As an open-source initiative, the project remains broadly applicable across multiple industrial niches, while being validated through concrete, representative use cases.

Join us to prototype, adapt, and deploy open AMRs - together.

[![Support on Patreon - Supporter Tier – €5/month](https://img.shields.io/badge/Support%20on-Patreon-orange)](https://www.patreon.com/cw/Botshare)
[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/paypalme/BotshareAI)
[![Donate on GitHub](https://img.shields.io/badge/Sponsor%20on-GitHub-pink?logo=github-sponsors)](https://github.com/sponsors/openAMRobot)

## 🚀 Project aim

While maintaining its original goals of accessibility and modularity, OpenAMRobot is evolving toward human-centric mobile robotics. The platform emphasizes shoulder-to-shoulder collaboration with human operators in shared workspaces, supporting operator-in-the-loop control, task handover, and assistance-oriented behaviors rather than full isolation or rigid automation. Robotic arm integration and height-adjustable linear actuators are treated as enabling components, allowing the robot to adapt ergonomically to different tasks, workstations, and human collaborators.

OpenAMR is an open-source initiative developing a versatile, modular dual-arm autonomous mobile robot designed as an end-to-end embodied AI system.
The platform bridges real-world deployment with research and education, while addressing practical automation challenges in manufacturing, last-mile logistics, CEP, grocery delivery, and related industries.

### Our system is built to:

- **Advance intelligent automation:** integrate computer vision and ML for perception, object recognition, and adaptive grasping in dynamic environments.
- **Enable modular, versatile manipulation:** combine a dual-arm robotic architecture with interchangeable payload tools and open hardware design for flexibility and customization.
- **Remain open and cost-efficient:** target a total production cost below €3500 for the mobile base and €3500 for the dual-arm upper module, providing accessible, reproducible technology for research, education, and prototyping.

Beyond the platform itself, OpenAMR serves as a collaborative foundation for learning and innovation in robotics, embedded systems, computer vision, machine learning, and mechanical design - empowering engineers, students, and creators to build, adapt, and evolve the next generation of autonomous robotic systems.

### Key features:

- **High manufacturability:** designed with simplicity in mind to facilitate easy production with basic technologies.
- **Advanced navigation:** utilizes LiDAR SLAM technology for accurate navigation and obstacle avoidance.
- **Modular design:** features a customizable platform for various attachments, including conveyors, elevators, and more.

## 📁 Repository structure

Here’s an overview of our project structure:
### 🤖[OpenAMR/](https://github.com/openAMRobot/OpenAMR)
-   #### ├── [Wiki/](https://github.com/openAMRobot/OpenAMR/wiki) 
-   #### ├── .github/
-   │ ├── ISSUE_TEMPLATE.md
-   │ ├── PULL_REQUEST_TEMPLATE.md
-   │ ├── CODEOWNERS
-   │ └── README.md
-   #### 📖├── [docs/](https://github.com/openAMRobot/OpenAMR/tree/main/docs)
-   #### 🛠️│ ├── hardware/
-   │ │ ├── CAD_files/
-   │ │ ├── schematics/
-   │ │ ├── BOM/
-   │ │ ├── pictures/
-   │ │ ├── datasheets/
-   │ │ ├── README.md
-   │ │ ├── build-guide.md
-   │ │ ├── assembly-guide.md
-   │ │ └── FAQ.md
-   #### 🖥️│ ├── software/
-   │ │ ├── UI/
-   │ │ │ ├── src/
-   │ │ ├── ROS/
-   │ │ │ ├── src/
-   │ │ ├── Firmware/
-   │ │ │ ├── src/
-   │ │ ├── README.md
-   │ │ ├── setup-guide.md
-   │ │ ├── usage-guide.md
-   │ │ └── FAQ.md
-   │ └── README.md
-   #### ├── .gitignore
-   #### ├── README.md
-   #### ├── CONTRIBUTING.md
-   #### ├── CODE_OF_CONDUCT.md
-   #### └── LICENSE
### 👨‍💻[OpenAMR_UI_package/](https://github.com/openAMRobot/OpenAMR_UI_package)
### 📥[OpenAMR_UI_dev/](https://github.com/openAMRobot/OpenAMR_UI_dev)

## Explanation
- **`Botshare_book`**: [The Botshare Book: AI, Robotics & Smart Automation](https://botshareai.github.io/Botshare_book/) (in progress...)
- **`Wiki`**: [contains comprehensive documentation on the project](https://github.com/openAMRobot/OpenAMR/wiki/Setup-your-robot)
- **`.github/`**: contains GitHub-specific files including templates for issues and pull requests and the general README
- **`docs/`**: contains documentation for both hardware and software aspects of the project.
  - **`hardware/`**: includes CAD files, schematics, BOM, pictures, datasheets, and guides for building and assembling the robot.
  - **`software/`**: contains source code and documentation for UI, ROS, and Firmware.
- **`.gitignore`**: specifies files and directories to be ignored by Git.
- **`README.md`**: detailed README file for the project.
- **`CONTRIBUTING.md`**: guidelines for contributing to the project.
- **`CODE_OF_CONDUCT.md`**: code of conduct for community interactions.
- **`LICENSE`**: the license under which the project is distributed.

## 🤝 Contribution guidelines

We welcome contributions from everyone! To get involved:

- **Open an issue:** use our [Issue Template](https://github.com/openAMRobot/.github/blob/main/ISSUE_TEMPLATE.md) to report bugs or suggest improvements.
- **Submit a pull request:** Follow our [Pull Request Template](https://github.com/openAMRobot/.github/blob/main/PULL_REQUEST_TEMPLATE.md) to propose changes.
- **Read contributing guidelines:** Review our [CONTRIBUTING.md](https://github.com/openAMRobot/OpenAMR/blob/main/CONTRIBUTING.md) for detailed contribution instructions.

## 👩‍💻 Useful resources

- **[Linorobot](https://github.com/linorobot/linorobot2):** find detailed guides on firmware and software (ROS2, Tensy board connection, firmware, etc).
- **[Documentation](https://github.com/openAMRobot/OpenAMR/tree/main/docs):** find detailed guides on hardware and software.
- **[Setup Guides](https://github.com/openAMRobot/docs/blob/main/software/setup-guide.md):** learn how to get started with the robot’s software.
- **[Usage Guides](https://github.com/openAMRobot/docs/blob/main/software/usage-guide.md):** instructions for using and customizing the software.
- **[Wiki](https://github.com/openAMRobot/OpenAMR/wiki/Setup-your-robot):** detailed description on how to set up robot (AMR).
- **[The Botshare Book](https://botshareai.github.io/Botshare_book/):** The AI Robotics playbook: From learning to implementation.

## 🍿 Fun facts

- **Breakfast club:** our team enjoys a variety of breakfasts, from Berlin pastries to Ukrainian borsch, keeping our creativity and energy high!
- **Origin story:** this project originated from a two-year research effort in Kharkiv, Ukraine, under Botshare. We decided to open-source our work under the MIT license to benefit the community.

## 📸 Visuals

Here’s what our completed robot looks like:

![Mobile robot general view](https://github.com/openAMRobot/OpenAMR/blob/main/docs/hardware/pictures/AMR_SME_logistics.jpg)

## 🧙 Get involved

Join us in advancing robotics technology! We're based at the Mechatronics Lab of the BHT University in Berlin and are eager to grow this project with contributions from like-minded individuals. Dive into our documentation, ask questions, and help us make this technology accessible to everyone. Together, we can transform automation and robotics for small and medium enterprises worldwide.

Feel free to explore, contribute, and innovate!

### Support Our Project
Help us bring innovative AI & robotics project to the next level!

[![Support on Patreon - Supporter Tier – €5/month](https://img.shields.io/badge/Support%20on-Patreon-orange)](https://www.patreon.com/cw/Botshare)
[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/paypalme/BotshareAI)
[![Donate on GitHub](https://img.shields.io/badge/Sponsor%20on-GitHub-pink?logo=github-sponsors)](https://github.com/sponsors/openAMRobot)

Every contribution, big or small, helps us grow. Thank you for your support!



|     :mortar_board: Attention! Our new educational project!     |
|----------|
|      :books: **[The AI Robotics Playbook: From learning to implementation](https://botshareai.github.io/Botshare_book/)**  (in progress...)    |



