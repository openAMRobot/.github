## Hi there 👋

# OpenAMRobot: affordable Autonomous Dual-arm Mobile Robot

We’re a robotics team from the Mechatronics Lab at BHT University (Berlin) focused on democratizing mobile robotics through high-quality, open-source designs. Our goal is to enable SMEs, entrepreneurs, and specialists to learn and build reliable, affordable AMRs with clear, production-ready guidance.

**Planned releases (next 6 months):**
- Carrier PCB (compute + power + sensors)
- Autodocking + wireless charging (ROS2 package & routines)
- Operator UI (ROS2) for teleop, maps, telemetry, way points and logs
- Hub-motor drivetrain with suspension (mechanical + control)
- Robotic arm integration (mounts, drivers, wiring, examples)
- ML-based CV for object recognition & grasp cues
- Complete documentation: HW/Wiring diagrams, BOMs, assembly & tests
- Educational notes: academic/learning guides for each subsystem

Join us to prototype, adapt, and deploy open AMRs—together.

## 🚀 Project aim

OpenAMR provides a detailed guide for building an affordable and versatile autonomous mobile robot. Our robot is designed to:

- **Automate goods movement:** efficiently move goods in warehouses, manufacturing plants, and farms.
- **Enhance operational efficiency:** improve logistics and material transport with advanced navigation and modular design.
- **Be Cost-Effective:** achieve a preliminary production cost of under €3000.

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
- **`Botshare_book`**: [The Botshare Book: AI, Robotics & Smart Automation](https://botshareai.github.io/Botshare_book/)
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

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/paypalme/BotshareAI)
[![Donate on GitHub](https://github.com/sponsors/openAMRobot)
[![Donate on Patreon](https://github.com/sponsors/openAMRobot)

Every contribution, big or small, helps us grow. Thank you for your support!



|     :mortar_board: Attention! Our new educational project!     |
|----------|
|      :books: **[The AI Robotics Playbook: From learning to implementation](https://botshareai.github.io/Botshare_book/)**      |



