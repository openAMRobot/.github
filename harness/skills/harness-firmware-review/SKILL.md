---
name: harness-firmware-review
description: Review checklist and host-test approach for the OpenAMRobot STM32H723 base controller and upper-body firmware (micro-ROS over UDP). Agents review and write host tests only; firmware is tier C. Use when reviewing a firmware PR or auditing firmware repositories.
---

# Firmware review (tier C: review and host tests only)

## Checklist
- Command timeout: no new command within the configured window drives outputs to the safe state; the window is a register value.
- Independent watchdog (IWDG) fed only from the main loop health, never from an interrupt or a timer that runs while the loop is stuck.
- micro-ROS agent loss and reconnect: outputs go safe on loss; reconnection does not replay old commands.
- STM32H7 data cache and DMA: Ethernet and other DMA buffers in a non-cacheable MPU region or with explicit clean and invalidate; a classic source of corrupted frames on H723.
- ISR work bounded; no blocking calls, no heap use, no printf in interrupts. Shared data between ISR and tasks is volatile and accessed atomically or under a critical section.
- Stack sizes measured (watermark) for every RTOS task; priorities documented.
- Integer overflow on encoder counters and time stamps (wrap-around handled); units explicit in names.
- Limits (current, speed, acceleration) come from one configuration header that mirrors the register, with a test that compares them.
- Gate A Teensy/MPU6500 and Gate B STM32/ICM-42688-P material stays distinct (register).

## Host tests
The portable C core (agreed direction) builds on the host with CMake and runs with Unity or GoogleTest: kinematics, protocol encoding and decoding, timeout state machine, limit clamping. Agents may add these tests in new files under `test/`. HIL and bench tests are V5 and need a person.

## Output
Findings in `.harness-out/findings.csv` with file and line, risk, and a proposed test. Anything that needs a change is needs-human:safety for the electrical owner.
