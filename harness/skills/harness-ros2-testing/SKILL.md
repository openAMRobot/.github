---
name: harness-ros2-testing
description: How to write and run tests for ROS 2 Jazzy packages in OpenAMRobot (pytest, gtest, launch_testing, colcon), including flake control and the test pyramid. Use whenever a mission adds, fixes or runs tests in a ROS 2 repository.
---

# ROS 2 testing

## Pyramid, fastest first
1. Pure logic (parsers, kinematics, state machines, planners, converters): plain pytest or gtest, no ROS context, milliseconds. Put logic in importable functions so it can be tested this way; that refactor is tier B.
2. Node-level: create the node in-process with `rclpy.init(context=...)` and a dedicated executor, publish inputs, spin until a condition with a timeout, assert outputs. For C++, `rclcpp` with `SingleThreadedExecutor::spin_some` in a loop.
3. Launch-level (`launch_testing` or `launch_pytest`): start the real launch file, wait for readiness (lifecycle state, topic, service), assert topic graph and behaviour, check exit codes in a post-shutdown test with `launch_testing.asserts.assertExitCodes`.
4. Simulation scenarios: see harness-simulation-validation.

## Package wiring
- ament_python: tests under `test/`, `<test_depend>` for pytest, launch_testing, launch_testing_ros; `setup.cfg` or `pytest.ini` with `junit_family=xunit2`.
- ament_cmake: `find_package(ament_cmake_gtest)` and `ament_add_gtest`; `ament_cmake_pytest` with `ament_add_pytest_test`; launch tests with `add_launch_test(test/x.test.py TIMEOUT 120)`.
- Lint tests come from `ament_lint_auto`; do not disable a linter to pass. A per-file exclusion needs an issue on the same line.

## Running
```
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths <src> --ignore-src -r -y
colcon build --symlink-install --event-handlers console_direct+
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --all --verbose
```
Iterate on one package with `--packages-select <pkg>`; before finishing run `--packages-above <pkg>` so every dependent package is tested too.

## Make tests deterministic
- Isolate DDS: `ROS_DOMAIN_ID` unique per test process (use the `domain_coordinator` package or a random id in a fixture) and `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.
- Never `time.sleep` to wait for a result; spin until a predicate with a timeout and a clear failure message.
- Use `use_sim_time` and publish /clock yourself when time matters.
- Seed every random generator. No network, no real devices.
- A test that is flaky is a bug. Run a new test three times; if results differ, fix it or label the issue needs-human:flaky. Never retry-until-green.

## Known traps (found in real runs, keep this list growing)
- launch_testing ignores `pytest.mark.xfail`, and its loader drops a method-level `unittest.expectedFailure`. For a strict expected failure put `@unittest.expectedFailure` on its own test class, with the tracking issue on the same line, so an unexpected pass fails the run (platform-sw #103).
- JUnit output records an expected failure as a pass. Copy the unittest result lines ("expected failures=1") into the job summary so a reader sees it.
- The launch_testing pytest plugin collects `test_*.launch.py` even when `collect_ignore` lists it. Name simulation launch tests `sim_*.launch.py` (or similar) and run them with `launch_test`, so `colcon test` on every PR stays fast.
- ROS 2 Jazzy needs Python 3.12 (Ubuntu 24.04 system Python). Never use actions/setup-python or a newer interpreter for ROS steps; ROS scripts hard-code /usr/bin/python3.
- DDS discovery in containers can take tens of seconds. Wait for the graph (node or publisher present) with a timeout of at least 30 s before asserting.
- Stopping a launch with SIGTERM can orphan the `gz sim` server child. Tests that start Gazebo assert that no process they started is left and record exit codes; an orphan is a finding, not something to kill quietly.
- A node whose `main()` calls `rclpy.shutdown()` after the SIGINT handler already did raises RCLError and exits 1; guard with `if rclpy.ok():`.

## What good tests check on this robot
Topic names and types match the contracts, QoS profiles match between publisher and subscriber, frames follow REP 105 and the register, parameters have bounds, nodes survive NaN, inf, empty and stale messages, commands time out to zero velocity, lifecycle transitions are clean, shutdown leaves no process.

## Rules from AGENTS.md
A zero-test suite fails. Every skip, xfail and importorskip names its issue on the same line. SKIP is not PASS. Show the revert run.
