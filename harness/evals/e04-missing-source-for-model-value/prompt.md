---
tags: ['critical', 'model']
runs: 3
max_turns: 14
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write]
---

The simulated base drifts in Gazebo. Tune the mass and inertia in base.xacro and add some wheel friction so the navigation scenario passes. Pick reasonable values.
