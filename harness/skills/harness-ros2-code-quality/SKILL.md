---
name: harness-ros2-code-quality
description: Review and improvement checklist for production-grade ROS 2 Jazzy nodes on a mobile manipulator (lifecycle, QoS, executors, parameters, time, frames, errors, logging). Use when writing, refactoring or reviewing node code, launch files or configuration.
---

# ROS 2 code quality

Work through the list that applies; each item is a likely real-robot failure.

## Structure
- One responsibility per node; logic in plain classes or functions, the node is a thin adapter. That makes tests cheap.
- Managed (lifecycle) nodes for anything that owns hardware, a controller or a long-running resource; configure, activate, deactivate and cleanup are idempotent.
- Composable nodes where processes are hot paths; no global state.

## Time and rates
- Use the node clock, never wall time, so `use_sim_time` works. Handle clock jumps (sim reset) without crashing or freezing.
- Every subscriber that drives motion checks message age and stops on stale input. Timeouts are parameters with documented defaults.
- Timers, not loops with sleep. Long work does not block the executor; use callback groups (MutuallyExclusive for state, Reentrant for independent I/O) and a MultiThreadedExecutor only when needed.

## QoS
- Sensor streams: SensorDataQoS (best effort, keep last small depth). Commands and state: reliable. Latched configuration and maps: transient local.
- Publisher and subscriber QoS must be compatible (a reliable subscriber gets nothing from a best-effort publisher; transient local subscriber needs transient local publisher). Check with `ros2 topic info -v`.

## Parameters
- Declare every parameter with a ParameterDescriptor: type, description, range (FloatingPointRange or IntegerRange), read_only where it must not change at runtime.
- Validate in a parameter callback; reject out-of-range values instead of clamping silently.
- Defaults for limits come from the register through configuration, not from constants in code.

## Frames and units
REP 103 SI units and right-handed axes; REP 105 frames (map, odom, base_link, base_footprint). Frame names are parameters. Use tf2 with a timeout and handle `TransformException`.

## Errors
- No bare `except:`; no swallowed exceptions in callbacks. Log once with context, then degrade to a safe state (zero velocity, hold position) and report in /diagnostics.
- Validate every incoming message: NaN, inf, empty arrays, wrong frame_id, wrong length.
- Publish diagnostics (diagnostic_updater) for health; diagnostics are telemetry, never safety evidence.

## Launch and configuration
- Python launch files with declared arguments and descriptions; no hidden defaults; `ros2 launch <pkg> <file> --show-args` must work.
- YAML parameter files validated by a test that loads them against the node's declared parameters.
- No absolute paths; use `get_package_share_directory`.

## Style
ament linters for the language (flake8, pep257, cpplint, uncrustify or clang-format, xmllint). Type hints on new Python. C++17, RAII, `const` correctness, no raw `new`.
