"""
Important/special files detection.

Identifies commonly important files in codebases like README, LICENSE,
configuration files, etc.
"""

import os

ROOT_IMPORTANT_FILES = [
  # Version Control
  ".gitignore",
  ".gitattributes",
  # Documentation
  "README",
  "README.md",
  "README.txt",
  "README.rst",
  "CONTRIBUTING",
  "CONTRIBUTING.md",
  "CONTRIBUTING.txt",
  "CONTRIBUTING.rst",
  "LICENSE",
  "LICENSE.md",
  "LICENSE.txt",
  "CHANGELOG",
  "CHANGELOG.md",
  "CHANGELOG.txt",
  "CHANGELOG.rst",
  "SECURITY",
  "SECURITY.md",
  "SECURITY.txt",
  "CODEOWNERS",
  # Package Management and Dependencies
  "requirements.txt",
  "Pipfile",
  "pyproject.toml",
  "setup.py",
  "setup.cfg",
  "package.json",
  "Gemfile",
  "composer.json",
  "pom.xml",
  "build.gradle",
  "build.gradle.kts",
  "build.sbt",
  "go.mod",
  "Cargo.toml",
  "mix.exs",
  "rebar.config",
  "project.clj",
  "Podfile",
  "Cartfile",
  "dub.json",
  "dub.sdl",
  # Configuration and Settings
  ".env.example",
  ".editorconfig",
  "tsconfig.json",
  "jsconfig.json",
  ".babelrc",
  "babel.config.js",
  ".eslintrc",
  ".prettierrc",
  ".stylelintrc",
  "tslint.json",
  ".pylintrc",
  ".flake8",
  ".rubocop.yml",
  ".scalafmt.conf",
  ".dockerignore",
  ".gitpod.yml",
  "sonar-project.properties",
  "renovate.json",
  "dependabot.yml",
  ".pre-commit-config.yaml",
  "mypy.ini",
  "tox.ini",
  ".yamllint",
  "pyrightconfig.json",
  # Build and Compilation
  "Makefile",
  "CMakeLists.txt",
  "webpack.config.js",
  "rollup.config.js",
  "parcel.config.js",
  "gulpfile.js",
  "Gruntfile.js",
  "build.xml",
  "build.boot",
  "project.json",
  "build.cake",
  "MANIFEST.in",
  # Testing
  "pytest.ini",
  "phpunit.xml",
  "karma.conf.js",
  "jest.config.js",
  "cypress.json",
  # Containerization and Deployment
  "Dockerfile",
  "docker-compose.yml",
  "docker-compose.yaml",
  "Vagrantfile",
  "Procfile",
  "app.yaml",
  "serverless.yml",
  "netlify.toml",
  "vercel.json",
  ".travis.yml",
  "azure-pipelines.yml",
  "Jenkinsfile",
  # Quality and metrics
  ".codeclimate.yml",
  "codecov.yml",
  # Documentation
  "mkdocs.yml",
  "_config.yml",
  "book.toml",
  "readthedocs.yml",
  ".readthedocs.yaml",
  # Package registries
  ".npmrc",
  ".yarnrc",
  # Linting and formatting
  ".isort.cfg",
  ".markdownlint.json",
  ".markdownlint.yaml",
  "ruff.toml",
  # Security
  ".bandit",
  ".secrets.baseline",
]

# Normalize the list once at module load
_NORMALIZED_ROOT_IMPORTANT_FILES = frozenset(
  os.path.normpath(path) for path in ROOT_IMPORTANT_FILES
)


def is_important(file_path: str) -> bool:
  """Check if a file path represents an important/special file."""
  file_name = os.path.basename(file_path)
  dir_name = os.path.normpath(os.path.dirname(file_path))
  normalized_path = os.path.normpath(file_path)

  # Check for GitHub Actions workflow files
  if dir_name == os.path.normpath(".github/workflows") and file_name.endswith(".yml"):
    return True

  return normalized_path in _NORMALIZED_ROOT_IMPORTANT_FILES


def filter_important_files(file_paths: list[str]) -> list[str]:
  """
  Filter a list of file paths to return only those that are commonly
  important in codebases.

  Args:
      file_paths: List of file paths to check

  Returns:
      List of file paths that match important file patterns
  """
  return [fp for fp in file_paths if is_important(fp)]
