# CLI Interface Contract

Version: 1.0  
Feature: 001-context-engine

---

## Command: `repo-map generate`

Enhanced version of the existing `generate` command with new flags for Flight Plan support.

### Synopsis

```
repo-map generate [OPTIONS] [PATH]
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | directory | `.` | Root directory to map |

### New Options (this feature)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config`, `-C` | file path | None | Path to Flight Plan YAML configuration |
| `--strict` | flag | false | Reject if output exceeds token budget |
| `--show-costs` | flag | false | Include inline cost annotations in output |
| `--verbosity`, `-v` | pattern:level | None | Quick verbosity override (repeatable) |
| `--focus` | pattern | None | Quick focus boost (repeatable) |

### Existing Options (unchanged)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--include`, `-i` | glob | None | Glob patterns to include |
| `--exclude`, `-e` | glob | None | Glob patterns to exclude |
| `--ext` | extension | None | Specific file extensions |
| `--no-gitignore` | flag | false | Disable .gitignore |
| `--tokens`, `-t` | int | 20000 | Maximum token budget |
| `--copy`, `-c` | flag | false | Copy to clipboard |
| `--output`, `-o` | file path | None | Write to file |
| `--summary`, `-s` | flag | false | Output file list only |
| `--quiet`, `-q` | flag | false | Suppress logs |

### Precedence Rules

When multiple sources specify the same setting:

1. CLI flags (highest priority)
2. Flight Plan YAML
3. Built-in defaults (lowest priority)

**Example**: `--tokens 5000` overrides `budget: 20000` in YAML.

### Usage Examples

#### Basic with Flight Plan

```bash
repo-map generate ./myproject --config flight-plan.yaml
```

#### Strict Mode for Final Output

```bash
repo-map generate . -C plan.yaml --strict
```

#### With Cost Annotations (for Navigator exploration)

```bash
repo-map generate . -C plan.yaml --show-costs
```

#### Quick Verbosity Override

```bash
# Format: pattern:level
repo-map generate . -v "src/**:3" -v "tests/**:1"
```

#### Quick Focus Boost

```bash
repo-map generate . --focus "src/core/**" --focus "src/auth/**"
```

#### Combined CLI + YAML

```bash
repo-map generate . \
  -C base-plan.yaml \
  --tokens 10000 \
  -v "src/critical.py:4" \
  --strict
```

---

## Output Format

### Standard Output (stdout)

Rendered repository map in deterministic format.

#### File Header (when `--show-costs` enabled)

```
# src/core/auth.py [L1:12 L2:89 L3:245 L4:1024]
```

Format: `# <path> [L1:<tokens> L2:<tokens> L3:<tokens> L4:<tokens>]`

#### File Content

Depends on verbosity level:

**Level 1** (path only):
```
src/core/auth.py
```

**Level 2** (structure):
```
# src/core/auth.py
class UserAuth
  def authenticate
  def validate_token
  def refresh_session
```

**Level 3** (interface):
```
# src/core/auth.py
class UserAuth:
    """Handles user authentication and session management."""
    
    def authenticate(self, username: str, password: str) -> Token:
        """Authenticate user and return session token."""
    
    def validate_token(self, token: Token) -> bool:
        """Validate an existing token."""
```

**Level 4** (implementation):
```
# src/core/auth.py
class UserAuth:
    """Handles user authentication and session management."""
    
    def authenticate(self, username: str, password: str) -> Token:
        """Authenticate user and return session token."""
        user = self.db.find_user(username)
        if not user or not user.check_password(password):
            raise AuthError("Invalid credentials")
        return self._create_token(user)
    # ... full implementation
```

### Budget Warning (appended to output)

When output exceeds budget (without `--strict`):

```
# ⚠️ BUDGET EXCEEDED: 25340 tokens used (budget: 20000, overrun: +5340)
```

### Error Output (stderr)

#### Strict Mode Rejection

```
Error: Budget exceeded
  Budget: 20000 tokens
  Actual: 25340 tokens
  Overrun: +5340 tokens (26.7%)

Top contributors:
  src/core/large_module.py: 8500 tokens (L4)
  docs/api_reference.md: 6200 tokens (L4)
  src/utils/helpers.py: 4100 tokens (L3)

Suggestions:
  - Reduce verbosity for large files
  - Add more patterns to Level 1 or 0
  - Increase budget with --tokens flag
```

#### YAML Validation Error

```
Error: Invalid flight plan configuration
  File: flight-plan.yaml
  
  Errors:
    - verbosity.0: Either 'level' or 'sections' must be specified
    - focus.paths.2.weight: Input should be greater than 0
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Budget exceeded (with `--strict`) |
| 2 | Invalid configuration |
| 3 | File/directory not found |
| 4 | Internal error |
