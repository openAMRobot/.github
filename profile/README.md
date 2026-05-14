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
> ## Ecosystem Repository Structure
>
> ```text
> OpenAMRobot Ecosystem
> │
> ├── openamr
> │   ├── Community entry point
> │   ├── Legacy platform repository
> │   ├── Public project presentation
> │   └── Historical hardware/software documentation
> │
> ├── openamr-platform-sw
> │   ├── ROS 2 robot software
> │   ├── Navigation (Nav2)
> │   ├── Docking
> │   ├── Simulation (Gazebo)
> │   ├── Perception
> │   ├── Drivers
> │   ├── Robot bringup
> │   └── Control systems
> │
> ├── openamr-platform-fw
> │   ├── Embedded firmware
> │   ├── STM32
> │   ├── Teensy
> │   ├── ESP32
> │   ├── Motor interfaces
> │   ├── Sensor interfaces
> │   ├── Safety systems
> │   └── Low-level communication
> │
> ├── openamr-platform-hw
> │   ├── Mechanical CAD
> │   ├── Chassis
> │   ├── Electrical systems
> │   ├── Wiring
> │   ├── PCB designs
> │   ├── BOMs
> │   ├── Manufacturing
> │   └── Assembly documentation
> │
> ├── openamrobot-interfaces
> │   ├── ROS 2 messages
> │   ├── ROS 2 services
> │   ├── ROS 2 actions
> │   ├── Shared schemas
> │   └── Interface contracts
> │
> ├── openamrobot-comm
> │   ├── REST APIs
> │   ├── WebSocket bridges
> │   ├── MQTT communication
> │   ├── Fleet communication
> │   ├── Middleware
> │   ├── Cloud communication
> │   └── Telemetry infrastructure
> │
> ├── openamrobot-ui
> │   ├── Operator UI
> │   ├── Dashboards
> │   ├── Fleet visualization
> │   ├── Teleoperation
> │   ├── Maps & telemetry
> │   ├── Monitoring
> │   └── Human-robot interaction
> │
> ├── openamrobot-docs
> │   ├── Tutorials
> │   ├── Onboarding
> │   ├── Safety documentation
> │   ├── Architecture documentation
> │   ├── Compatibility matrices
> │   ├── Contributor documentation
> │   └── Ecosystem standards
> │
> ├── Future ecosystem expansion
> │   │
> │   ├── openamrobot-humanoid
> │   │   ├── Dual-arm upper body
> │   │   ├── Humanoid manipulation
> │   │   ├── Arm coordination
> │   │   ├── Linear lift systems
> │   │   ├── Human interaction
> │   │   └── Embodied AI integration
> │   │
> │   ├── openamrobot-fleet
> │   │   ├── Fleet management
> │   │   ├── Multi-robot orchestration
> │   │   ├── Remote monitoring
> │   │   └── Cloud coordination
> │   │
> │   ├── openamrobot-ai
> │   │   ├── Computer vision
> │   │   ├── Perception pipelines
> │   │   ├── ML inference
> │   │   ├── Grasp planning
> │   │   └── AI-assisted autonomy
> │   │
> │   └── openamrobot-simulation-assets
> │       ├── Robot models
> │       ├── Industrial environments
> │       ├── Test scenarios
> │       └── Benchmark environments
> │
> └── Legacy repositories
>     ├── EOD-robot
>     ├── OpenAMR_UI_dev
>     ├── OpenAMR_UI_package
>     ├── OpenAMR_UI
>     └── Botshare_docs
> ```
>
> ## Active Core Repositories
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
> ## Legacy Repositories
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
> Active development should target the modular ecosystem repositories listed above.
