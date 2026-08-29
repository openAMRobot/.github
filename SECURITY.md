# Security Policy

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue, discussion, pull request, or chat.

Use either of these private channels:

1. In the **affected repository**, open **Security → Advisories → New draft security advisory**. GitHub’s repository URL has the form:
   https://github.com/openAMRobot/REPOSITORY/security/advisories/new
2. Email **info@botshare.ai** with the subject “OpenAMRobot security report”.

Include the affected repository and version or commit, impact, reproduction steps, proof of concept when safe, known mitigations, and a secure contact method. Remove credentials, personal data, third-party confidential information, and unnecessary operational secrets.

If private vulnerability reporting is not enabled for the affected repository, use email. Do not open a public report.

## Scope

Reports may concern:

- ROS 2 nodes, services, actions, topics, or launch configuration;
- remote control, networking, authentication, or authorization;
- unsafe firmware, bootloaders, update mechanisms, or device interfaces;
- secrets, credentials, dependency or supply-chain risks;
- robot motion, stored energy, charging, thermal, electrical, or mechanical safety;
- AI-related security and unsafe autonomous behavior; or
- release artifacts and build infrastructure.

## Response and disclosure

Botshare LTD aims to acknowledge, investigate, coordinate remediation, and publish fixes when practical. Do not assume a response or remediation deadline unless Botshare LTD confirms one in writing. Please allow coordinated disclosure before publication.

## Experimental nature and user responsibility

OpenAMRobot is experimental and research-oriented. Software and hardware must not be assumed safe for industrial, medical, safety-critical, or autonomous public operation without independent risk assessment, validation, testing, and certification.

Users remain responsible for regulatory compliance, deployment suitability, integration testing, physical safeguards, access control, and operational safety.

## Supported versions

Security support varies by component maturity. Unless a repository states otherwise, reports should target the latest public release or the current default branch.

Security contact: **info@botshare.ai**.
