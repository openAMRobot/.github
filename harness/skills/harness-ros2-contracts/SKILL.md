---
name: harness-ros2-contracts
description: How to check message, service, action, topic, QoS, parameter and launch-argument consistency across all OpenAMRobot repositories. Use for the contracts audit, for reviewing any PR that publishes, subscribes or calls an interface, and before proposing any interface change.
---

# Contracts across repositories

The robot works only if every repository agrees on names, types, QoS and units. openamrobot-interfaces owns the shared message packages.

## Build the contract graph (contracts audit)
For every enrolled repository at its default branch:
1. Interface definitions: every `.msg`, `.srv`, `.action` with its package. Flag duplicates (the same package name defined twice, as in manifest issue #8) and definitions outside openamrobot-interfaces that other repositories use.
2. Endpoints from code: `create_publisher`, `create_subscription`, `create_service`, `create_client`, `ActionServer`, `ActionClient` (Python and C++), with topic or service name, type, QoS. From launch files: remappings, namespaces, `ros_gz_bridge` configs. From YAML: topic parameters. From the UI: rosbridge topic names in JavaScript.
3. Resolve names after remapping and namespaces.
4. Write `.harness-out/contracts.json`: nodes, endpoints, types, QoS, source file and line.

## Findings to report
- A subscribed topic with no publisher anywhere, or a publisher nobody reads (dead topic).
- The same topic with different types or incompatible QoS.
- A type used by a consumer that the interfaces package no longer defines, or a field the consumer reads that does not exist.
- More than one publisher on a command topic (/cmd_vel above all: tier C, needs-human:safety).
- Units or frames in a message comment that contradict REP 103, REP 105 or the register.
- Launch arguments and parameter names that differ between a launch file and its callers.
Record each in `.harness-out/findings.csv` with columns: id, severity (Blocker, Major, Minor), area, repository, file_to_change, value_a, value_b, decision_of_record, fix. IDs are SW-1000 to SW-1999 (the contracts audit range; the software lead owns them).

## Changing a contract
Never in a build mission. A contract change needs a contract change request issue and one PR updating the interface package and every consumer together (AGENTS.md "Contracts"). Agents prepare the hand-over: the consumers list from the graph, the compatibility impact, and tests that would catch a break. Label needs-human:contract.

## Jazzy specifics
Interface type hashes (RIHS01) are visible in `ros2 topic info -v`; a type changed in one repository but not rebuilt in another shows a hash mismatch and the endpoints will not match. Check with a launch test that brings up both sides.
