---
name: harness-embodied-ai-pipeline
description: How harness agents work on the OpenAMRobot demonstration-learning stack (teleoperation recording, datasets, policy training, evaluation, policy runner). Use for any task in openamrobot-embodied-ai, the data pipeline or policy evaluation.
---

# Embodied AI pipeline

## Parts and tiers
- Recording (teleoperation to dataset), dataset tools, training configuration, offline evaluation: tier B. Agents may build and test these.
- Policy runner (`openamrobot_policy_runner`) and anything that turns model output into joint or base commands: tier C. Generated command plans are safety-relevant (ENGINEERING_QUALITY_STANDARD.md section 7): a validation layer between the model and the robot is mandatory and a person writes it.

## Dataset rules
- Every episode records consent and licence for the people and places it shows (camera streams can contain faces and private spaces); an episode without them is excluded from training and never published.
- One documented format (LeRobot dataset layout is the reference ecosystem): episodes, timestamps, camera streams, joint states, actions, task text, robot and calibration metadata, commit SHA of the recording code.
- A validator script checks every episode: monotonic timestamps, synchronised streams within tolerance, no NaN, joint values inside limits from the robot model, action dimension matches the robot, frames per REP 105. Agents write and extend this validator and its tests.
- Small sample datasets for tests live in test fixtures, never full datasets in git.

## Evaluation
- Offline: replay held-out episodes, report action error per joint.
- Simulation: run the policy in the simulated upper body with fixed seeds, report success rate over at least 20 episodes with a confidence interval; never a single run.
- Always state the robot model revision, camera configuration and dataset version used. Simulation success is V4, not robot readiness.

## Runner checks to test (without changing the runner)
Action clipping to joint and velocity limits, rate limiting, timeout to hold on missing inference, rejection of NaN outputs, a stop input that overrides the policy. Write these as tests in new files; failures are needs-human:safety.
