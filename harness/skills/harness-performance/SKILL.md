---
name: harness-performance
description: How to measure and improve runtime performance of OpenAMRobot ROS 2 nodes on the Jetson Orin NX target, using simulation and CI as proxies, with regression rules. Use for the weekly performance audit and for optimisation tasks.
---

# Performance

## What matters on this robot
Control and safety loop latency (command in to /cmd_vel out), message rates of sensors and controllers, CPU and memory per node (the Jetson Orin NX shares CPU and GPU), startup time of the bringup, and policy inference latency for the embodied AI stack.

## Measuring in CI and simulation
- Rates and latency: `ros2 topic hz`, `ros2 topic delay` (needs header stamps), or a small measurement node that records stamps; ros2_tracing (tracetools) for callback-level latency when available.
- CPU and memory per process: sample `/proc/<pid>/stat` and `status` or psutil during a fixed scenario; report mean and 95th percentile.
- Python hot spots: py-spy record on the scenario. C++: perf or valgrind callgrind on a unit benchmark.
- Startup: time from launch to all lifecycle nodes active.
Write `.harness-out/perf.json` with metric, value, unit, scenario, commit, runner type.

## Regression rule
Compare with the last four weekly results on the same runner type. Report a regression when a metric is more than 20 percent worse than the median. CI runners are not the Jetson: numbers are relative, never acceptance values.

## Optimising
Measure first, change one thing, measure again, keep the numbers in the PR. Typical safe wins: avoid copying large messages (use shared pointers and intra-process communication in C++), lower logging in hot paths, move heavy work out of callbacks, correct QoS depth, avoid re-creating publishers, vectorise numpy code. Never trade correctness, timeouts or safety margins for speed; changes to control loop rates are tier C.
