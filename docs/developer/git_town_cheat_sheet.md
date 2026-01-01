# Git Town Cheat Sheet

### Setup

Run once per repo to configure main branch and squash-merge settings.

```bash
git town config setup

```

### 1. Start New Feature (Base of Stack)

Creates a new branch off `main`.

```bash
git town hack <branch-name>

```

### 2. Stack a Branch (Child Branch)

Creates a new branch off your **current** branch.

```bash
git town append <branch-name>

```

### 3. Open Pull Request

Pushes the branch and opens the GitHub PR URL.

```bash
git town propose

```

### 4. Sync Current Branch

Runs `git pull`, pushes local changes, and **rebases** on top of parent.

```bash
git town sync

```

### 5. Propagate Changes to All Branches

If you modified a parent branch, run this to update **all** child branches in the correct order automatically.

```bash
git town sync --all

```

### 6. After Merging to Main

1. **GitHub UI:** "Squash and Merge" the PR.
2. **GitHub UI:** Click **"Delete Branch"**.
3. **Local Terminal:**
```bash
git town sync --all

```


*(Detects merged branches, deletes them locally, and rebases remaining children onto `main`)*.

### 7. Visualize Stack

See your local branch hierarchy.

```bash
git town tree

```