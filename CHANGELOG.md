# Changelog

All notable changes to **ContainerCraft** are documented here.

---

## [Unreleased]

### ✨ Added
- Product page (`landing/`) on Vercel

---

## [0.1.0] — 2026-10-29

### ✨ Added
- `craft` CLI: `list` (with `--stats`, `--label`, `-a`), `inspect`, `start`/`stop`/`restart`, `logs` (`--tail`, `-f`), `health`, `monitor`
- Health monitor with CPU/memory thresholds, consecutive-breach detection, cooldown, and a give-up limit per 10-minute window
- REST API for the same operations plus monitor status/start/stop; read-only without `CRAFT_API_KEY`
- CPU and memory maths matching `docker stats`, excluding page cache

### 🧪 Tests
- Unit tests with a fake Docker client and a fake clock
- Integration tests against a real daemon (skipped when Docker isn't available)

---

[Unreleased]: https://github.com/akshatgcodes/ContainerCraft/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/akshatgcodes/ContainerCraft/releases/tag/v0.1.0

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
