#!/usr/bin/env python3
"""
Cariza is a doc compiler based on git submodule routines.
This script downloads README.md files from specified GitHub repositories,
considering their license types. It includes logging for tracking the process.
"""

import os
import requests
import argparse
import logging
import time
from logging.handlers import RotatingFileHandler
from typing import List, Optional

# Constants
GITHUB_API_URL = "https://api.github.com/repos/"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/"
GITHUB_TOKEN = None  # Replace with your GitHub token if needed

# Allowed licenses
ALLOWED_LICENSES = [
    "mit license",
    "apache license 2.0",
    "bsd license",
    # Add more licenses as needed
]

# Configure logger
logger = logging.getLogger("__main__")


def configure_logger(log_level: str = "INFO") -> None:
    """
    Configures the logger with rotating file handler and console handler.

    Args:
        log_level (str): Logging level (INFO, DEBUG, etc.).
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logger.setLevel(numeric_level)

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # File handler with rotation
    file_handler = RotatingFileHandler("logs/cazira.log", maxBytes=5 * 1024 * 1024, backupCount=5)
    # Console handler
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Cariza is a doc compiler based on git submodule routines."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save output files. Defaults to 'output' folder in current directory.",
    )
    parser.add_argument(
        "--log-level",
        choices=["INFO", "DEBUG"],
        default="INFO",
        help="Logging level. Defaults to INFO.",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub personal access token to increase API rate limits.",
    )
    return parser.parse_args()


def get_repo_info(owner: str, repo: str, token: Optional[str] = None) -> Optional[dict]:
    """
    Fetch repository information from GitHub API.

    Args:
        owner (str): Owner of the repository.
        repo (str): Repository name.
        token (Optional[str]): GitHub personal access token.

    Returns:
        Optional[dict]: Repository information if successful, else None.
    """
    url = f"{GITHUB_API_URL}{owner}/{repo}"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    logger.debug(f"Fetching data from URL: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logger.info(f"Successfully fetched data for repository: {owner}/{repo}")
        return response.json()
    else:
        logger.error(
            f"Failed to fetch data for repository: {owner}/{repo}. "
            f"Status Code: {response.status_code}. Response: {response.text}"
        )
        return None


def download_readme(
    owner: str, repo: str, default_branch: str, token: Optional[str] = None
) -> Optional[str]:
    """
    Download the README.md content from the repository.

    Args:
        owner (str): Owner of the repository.
        repo (str): Repository name.
        default_branch (str): Default branch of the repository.
        token (Optional[str]): GitHub personal access token.

    Returns:
        Optional[str]: Content of README.md if successful, else None.
    """
    url = f"{GITHUB_RAW_URL}{owner}/{repo}/{default_branch}/README.md"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    logger.debug(f"Downloading README.md from URL: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logger.info(f"Successfully downloaded README.md for repository: {owner}/{repo}")
        return response.text
    else:
        logger.error(
            f"Failed to download README.md for repository: {owner}/{repo}. "
            f"Status Code: {response.status_code}"
        )
        return None


def save_readme(content: str, filename: str, directory: str) -> None:
    """
    Save the README.md content to a file.

    Args:
        content (str): README.md content to save.
        filename (str): Name of the Markdown file.
        directory (str): Directory where the file will be saved.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug(f"Created directory: {directory}")
    # Sanitize filename to avoid issues
    sanitized_filename = filename.replace("/", "_")
    file_path = os.path.join(directory, f"{sanitized_filename}.md")
    try:
        with open(file_path, "w", encoding="utf-8") as md_file:
            md_file.write(content)
        logger.info(f"README.md saved: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save README.md file {file_path}. Error: {e}")


def process_repositories(repos: List[str], output_dir: str, token: Optional[str] = None) -> None:
    """
    Process a list of repositories to download README.md files.

    Args:
        repos (List[str]): List of repositories in 'owner/repo' format.
        output_dir (str): Directory to save the downloaded README.md files.
        token (Optional[str]): GitHub personal access token.
    """
    for full_repo in repos:
        full_repo = full_repo.strip()
        if not full_repo:
            logger.warning("Encountered empty repository entry. Skipping.")
            continue
        try:
            owner, repo = full_repo.split("/")
            logger.debug(f"Processing repository: Owner='{owner}', Repo='{repo}'")
        except ValueError:
            logger.error(
                f"Invalid repository format: '{full_repo}'. Expected 'owner/repo'. Skipping."
            )
            continue

        repo_data = get_repo_info(owner, repo, token)
        if not repo_data:
            logger.warning(f"Skipping repository '{full_repo}' due to failed data retrieval.")
            continue  # Skip to the next repository if fetching info failed

        # Check license
        license_info = repo_data.get("license")
        if not license_info:
            logger.warning(f"Repository '{full_repo}' does not have a license. Skipping.")
            continue

        license_name = license_info.get("name", "").lower()
        if license_name not in ALLOWED_LICENSES:
            logger.warning(
                f"Repository '{full_repo}' has a license '{license_name}' which is not allowed. Skipping."
            )
            continue

        # Get default branch to fetch README.md
        default_branch = repo_data.get("default_branch", "master")
        readme_content = download_readme(owner, repo, default_branch, token)

        if not readme_content:
            logger.warning(
                f"Repository '{full_repo}' does not have a README.md or it could not be downloaded."
            )
            continue

        save_readme(readme_content, repo, output_dir)


def main():
    """
    Main function to execute the script.
    """
    start_time = time.time()

    args = parse_arguments()
    configure_logger(args.log_level)

    # Directories
    output_dir = args.output_dir

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    logger.debug(f"Output directory is set to: {output_dir}")

    # Example list of target repositories
    target_repositories = [
        "ikatyang/emoji-cheat-sheet"
        # Add more repositories as needed
    ]

    # Optionally, you can read repositories from a file or another source
    # For example:
    # with open('repositories.txt', 'r') as file:
    #     target_repositories = [line.strip() for line in file if line.strip()]

    logger.info("Starting README.md download process.")
    process_repositories(target_repositories, output_dir, args.token)
    logger.info("README.md download process completed.")

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Total time taken: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
