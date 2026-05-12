# OpenAMRobot Release Policy

## Purpose

This document defines general release and versioning expectations across the OpenAMRobot ecosystem.

Because repositories vary in maturity, release practices may differ between projects.

---

# Release Philosophy

OpenAMRobot encourages:

- transparent development
- incremental improvement
- reproducibility
- documentation-driven releases
- open collaboration

Repositories may evolve rapidly during research and development phases.

---

# Versioning

Repositories are encouraged to follow semantic versioning when practical:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
1.4.2
```

Where:

- MAJOR = breaking changes
- MINOR = new features
- PATCH = fixes and small improvements

Experimental repositories may use pre-release versions such as:

```text
0.x.x
```

---

# Release Notes

Releases should ideally include:

- major changes
- bug fixes
- breaking changes
- migration notes
- known limitations

---

# Stability Expectations

Not all repositories are production-ready.

Repositories may be:

- experimental
- research-oriented
- prototype-stage
- educational
- partially complete

Users should evaluate repository maturity before deployment.

---

# Hardware Releases

Hardware-related repositories should document:

- BOM versions
- PCB revisions
- CAD revisions
- manufacturing notes
- compatibility notes

---

# Compatibility

Repositories should document compatibility where practical, including:

- ROS versions
- operating systems
- firmware compatibility
- hardware dependencies

---

# Security and Safety

Releases do not guarantee:

- safety certification
- industrial certification
- cybersecurity compliance
- regulatory approval

Users are responsible for validation and compliance.

---

# Long-Term Support

Long-term support policies may vary by repository maturity and maintainer availability.

Repositories should document support expectations when applicable.

---

# Policy Updates

This document may evolve as the ecosystem grows.