---
name: harness-simulation-validation
description: How to write, run and judge headless Gazebo simulation scenarios for the OpenAMRobot base and upper body in CI, and what simulation results may and may not claim. Use when adding scenarios, analysing nightly simulation results or reviewing a claim that cites simulation.
---

# Simulation validation

## Stack
ROS 2 Jazzy with Gazebo Harmonic through ros_gz. CI runs headless: launch with `gui:=false use_rviz:=false` and the server-only Gazebo flags (`gz sim -s -r --headless-rendering` where sensors render). Everything uses `use_sim_time:=true`.

## Scenario files
One YAML file per scenario under the repository's `sim_scenarios/` (created by a tier B task), run by a deterministic launch_testing runner, not by an agent. Fields:
```
id: nav-corridor-01
launch: openamrobot_bringup bringup.launch.py sim:=true gui:=false use_rviz:=false
world: <world file>
seed: 7
timeout_s: 300
steps:                       # in order
  - wait_active: [bt_navigator, controller_server, collision_monitor]
  - navigate_to: {x: 4.0, y: 0.0, yaw: 0.0, frame: map, timeout_s: 120}
  - inject: {type: obstacle, x: 2.0, y: 0.0, at_s: 20}
expect:
  - single_publisher: /cmd_vel
  - goal_reached: true
  - min_clearance_m: {gte: <from register>}
  - no_process_crash: true
metrics: [time_to_goal_s, path_length_m, min_clearance_m, cmd_vel_max, cpu_percent, rtf]
```
Thresholds come from the register or from a recorded baseline, never invented. The runner writes `results/<id>.json` and records a rosbag2 (MCAP) for failures only.

## Scenario families worth having
Bringup start and stop cycles; single /cmd_vel publisher; navigation to goals in two worlds; obstacle appears mid-path (stop then replan); docking approach and undock; localisation recovery after a kidnap; sensor dropout (LiDAR, camera, ultrasonic topic stops); command source loss (teleop stops publishing); clock reset; arm reach and lift motion in the upper body world once the combined model is on main.

## Judging
- A scenario passes only if every expect holds and the run finished; a timeout is a failure, not a skip.
- Compare metrics with the last 7 nightly runs; flag a regression when a metric is worse than the worst of those runs. Real-time factor below 0.5 makes timing metrics invalid: report them as not measured.
- Run a failing scenario three times before calling it a regression; differing results make it needs-human:flaky.

## Model-fidelity record (one per simulation suite)
Simulation is only as good as the model behind it, and more detail is not more accuracy. Each suite keeps `sim_scenarios/FIDELITY.md` with: repository commits, Xacro/URDF and Gazebo and plugin versions; every physical parameter used (wheel radius and separation, masses and inertias, joint and velocity limits, sensor poses, rates, noise and latency, controller periods) with its provenance (register entry, approved CAD, supplier data, measured on the robot, or provisional) and date; the behaviour under test; the valid envelope; known omissions; residuals against bench or robot measurements where they exist; the next validation layer. A provisional parameter limits the claim; never invent one to make a scenario pass, and never tune a safety or stop behaviour to simulation.

## What simulation is not
Simulation is V4 on the validation ladder. It is never physical stopping evidence, never safety evidence, and never closes a P-03, E-01 or M-01 physical gate. Say so in every result.
