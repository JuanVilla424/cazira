# 📄 Cazira

![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)
![Build Status](https://github.com/JuanVilla424/cazira/actions/workflows/ci.yml/badge.svg?branch=main)
![Status](https://img.shields.io/badge/Status-Stable-green.svg)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

**Cazira** is a small CLI that compiles documentation by downloading the `README.md` of GitHub
repositories — but only when the source repository carries a **permissive license**. It is meant to
be driven from git-submodule routines that aggregate docs from several repos into a single folder.

Each repository is queried through the GitHub API, its license is checked against an allow-list, and
the `README.md` of its default branch is saved as `<output-dir>/<repo>.md`.

## 📚 Table of Contents

- [Features](#-features)
- [Getting Started](#-getting-started)
  - [Prerequisites](#-prerequisites)
  - [Installation](#-installation)
- [Usage](#-usage)
- [Allowed Licenses](#-allowed-licenses)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

## 🌟 Features

- **License-aware:** only downloads docs from repos with an allowed (permissive) license.
- **Configurable input:** target repos via `--repos` or a `--repos-file`.
- **Resilient HTTP:** request timeouts and simple backoff on GitHub API rate limiting.
- **Optional token:** pass a GitHub token to raise API rate limits.
- **Rotating logs:** console output plus a rotating file log in `logs/cazira.log`.

## 🚀 Getting Started

### 📋 Prerequisites

- **Python 3.12+**
- A **GitHub personal access token** (optional, only to raise API rate limits)

### 🔨 Installation

```bash
git clone https://github.com/JuanVilla424/cazira.git
cd cazira

# Create and activate a virtual environment (always .venv)
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate

pip install -r requirements.txt
```

## 🛠️ Usage

Provide the target repositories either inline or via a file:

```bash
# Inline list
python src/main.py --repos "ikatyang/emoji-cheat-sheet,psf/requests" --output-dir output

# From a file (one "owner/repo" per line; lines starting with "#" are ignored)
python src/main.py --repos-file repos.txt --output-dir output --token "$GITHUB_TOKEN"
```

| Flag           | Default  | Description                                     |
| -------------- | -------- | ----------------------------------------------- |
| `--repos`      | _(none)_ | Comma-separated `owner/repo` list.              |
| `--repos-file` | _(none)_ | Path to a file with one `owner/repo` per line.  |
| `--output-dir` | `output` | Folder where the `README.md` files are written. |
| `--token`      | _(none)_ | GitHub token to increase API rate limits.       |
| `--log-level`  | `INFO`   | `INFO` or `DEBUG`.                              |

If neither `--repos` nor `--repos-file` is given, the run exits with an error.

## 📜 Allowed Licenses

A repository is processed only if its license name matches the allow-list in `src/main.py`
(`ALLOWED_LICENSES`). Out of the box: **MIT**, **Apache License 2.0**, and **BSD**. Add more entries
there as needed. Repositories without a license, or with a disallowed one, are skipped.

## 🤝 Contributing

1. **Fork** the repository.
2. **Create a feature branch** — `git checkout -b feature/your-feature-name`.
3. **Commit** using Conventional Commits — `git commit -m "feat(<scope>): your message - lower case"`.
4. **Push** and **open a Pull Request into the** `dev` **branch**.

Pre-commit hooks (format, lint, version control, changelog) run automatically:

```bash
pre-commit install -t pre-commit -t pre-push
pre-commit run --all-files
```

## 📫 Contact

For any inquiries or support, please open an issue or contact
[r6ty5r296it6tl4eg5m.constant214@passinbox.com](mailto:r6ty5r296it6tl4eg5m.constant214@passinbox.com).

---

## 📜 License

2026 - This project is licensed under the
[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html). You are free to use,
modify, and distribute this software under the terms of the GPL-3.0 license. See the [LICENSE](LICENSE)
file for details.
