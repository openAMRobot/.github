---
name: harness-robot-description-fidelity
description: How to keep the OpenAMRobot Xacro/URDF, ros2_control and simulation models traceable to the register, CAD, supplier data and measurements. Use when touching robot descriptions, sensor frames, joint limits, inertias, ros2_control tags or Gazebo models, or when reviewing such a change.
---

# Robot description fidelity

The goal is a model that represents the real robot as closely as the evidence allows, with every value traceable. Accuracy is shown by comparison with the real platform, not by visual detail.

## Traceability chain
register entry or requirement ID -> source revision -> model element and parameter -> test or scenario -> measured result and tolerance -> evidence artifact -> remaining physical validation.

## Rules
- Every frame origin, joint axis, limit, mass, inertia and sensor pose names its provenance in a comment next to it: `<!-- source: NEAR-FIELD-FRAMES (register) -->`, `<!-- source: M-01 rev19.6 drawing MMP.00.00.00.005 -->`, `<!-- source: supplier datasheet <part>, rev -->`, `<!-- source: measured 2026-11-24, bench sheet <id> -->` or `<!-- provisional: <why>, owner <role> -->`.
- Values held in the register are read from it by a test (harness-register-and-baseline), never copied by hand without that test.
- Frames follow REP 105 and the FRAMES-REP105 entry; units SI (REP 103); angles in radians in the model, degrees allowed in comments.
- Collision geometry is conservative (never smaller than the real envelope); visual meshes never replace collision shapes.
- Inertia tensors must be physically valid (positive definite, triangle inequality); add a test that checks every link.
- ros2_control joint limits and the URDF limits agree; a test parses both. Limit files are tier C: the test is yours, the values are a person's.
- `check_urdf` (urdfdom) and `xacro` expansion of every configuration ID in the register (CONFIG-IDS) run in CI.
- The same xacro drives simulation and the real robot; simulation-only differences live behind one documented argument.

## What you may do
Add provenance comments where the source is certain, add parsing and consistency tests, find values that disagree with the register or between URDF, SDF and configuration files, and report gaps. What you may not do: invent or estimate physical values, change limits, or present a model as validated without measurements.
