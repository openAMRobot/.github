---
name: harness-impact-analysis
description: How to find what a change affects across packages, repositories, topics and register values, and which tests must run. Use in every review, in the impact audit, and before a build mission finishes.
---

# Impact analysis

## Layers of "what affects what"
1. Build graph: `colcon graph --dot` and `colcon list --topological-order` inside the workspace from openamrobot-manifest. A changed package affects `colcon list --packages-above <pkg>`.
2. Runtime graph: the contract graph (harness-ros2-contracts). A changed topic, type, QoS or frame affects every endpoint on it.
3. Configuration graph: which launch files include which, which YAML files feed which nodes, which parameters override others.
4. Register graph: each decisions.yaml entry's `applies_to` and the files that state its value. A value change affects every consumer listed.
5. Release graph: the rc.1 manifest pins; a change on main does not reach rc.1 until the manifest is updated.

## In a build mission
Before the PR: list the affected packages and repositories in the Integration Gate section, run the tests of every affected package in this repository (`colcon test --packages-above <pkg>`), and name cross-repository consumers you could not test under Not verified.

## In a review
State the blast radius in one line: packages, topics, repositories, register entries. If it crosses a repository boundary and the PR does not say so, that is the first finding.

## Impact audit (weekly)
Produce `.harness-out/impact.md`: the build graph of the manifest workspace, packages with no tests ranked by in-degree (most depended-on first), cycles, packages built from two paths, and the ten files whose change would affect the most other packages. These rankings feed triage priorities: untested, highly depended-on code gets tests first.
