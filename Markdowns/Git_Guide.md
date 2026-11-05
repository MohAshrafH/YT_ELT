# Git Commit and Push Guide

Use this workflow to save a meaningful version of your project locally and upload it to GitHub:

```text
Save files → Check → Stage → Review → Commit → Push → Confirm
```

**Saving** updates files on disk. **Committing** records a snapshot in local Git history. **Pushing** uploads local commits to the remote repository on GitHub.

## 1. Open the project terminal

Save your intended edits in VS Code, then open **Terminal → New Terminal**.

From PowerShell, move to the project folder if needed:

```powershell
Set-Location "F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT"
```

Virtual environment activation is not required for Git commands.

## 2. Check what changed

```powershell
git status
```

This shows your current branch and files that are new, modified, deleted, or already staged. Confirm that the listed changes belong in this commit.

To display just your branch name:

```powershell
git branch --show-current
```

The branch was `main` when this guide was prepared. Check the current value instead of assuming it will always be `main`.

## 3. Stage the intended changes

To include all applicable additions, edits, and deletions under the current folder:

```powershell
git add .
```

Staging selects the content for the next commit. It does not commit or upload anything.

If you only want specific files, use their names instead:

```powershell
git add 3_video_stats.py Markdowns/Git_Guide.md
```

Use quotation marks around paths containing spaces. If you edit a file after staging it, run `git add` again to include the newer edits.

The project's current `.gitignore` excludes `.env`, `venv/`, `.venv/`, and Python bytecode caches. Ignore rules do not automatically untrack a file that Git already tracks.

## 4. Review exactly what will be committed

```powershell
git diff --staged
```

Review the staged content, including deletions and renamed-file changes. Confirm that no real API keys or unrelated changes are included. If a scrolling viewer opens, press **Q** to leave it.

Then check the staged file list:

```powershell
git status
```

To remove a file from staging while keeping its edits on disk:

```powershell
git restore --staged Markdowns/Git_Guide.md
```

The path above is an example; substitute the file you want to unstage.

## 5. Commit locally

```powershell
git commit -m "Add video statistics extraction and explanatory guides"
```

`-m` supplies the commit message. Choose a short message that describes the actual completed change. This creates a local history checkpoint from the staged content; it does not upload it yet.

## 6. Push to GitHub

```powershell
git push
```

This sends local commits to the current branch's configured upstream remote branch.

If Git reports that no upstream is configured, and you intend to publish local `main` to `origin/main`, use:

```powershell
git push -u origin main
```

- `origin` is the conventional name of your configured remote.
- `main` is the branch being published; substitute the actual intended branch if different.
- `-u` establishes tracking so subsequent pushes can use `git push`.

If a push is rejected because the remote has additional commits, inspect and reconcile that history before retrying. Do not use force push as a routine fix.

## 7. Confirm completion

```powershell
git status
```

After a successful push, with no remaining edits, expect a clean working tree and the branch up to date with its upstream.

Optionally inspect the most recent commits:

```powershell
git log --oneline -5
```

## Everyday quick reference

Run one command at a time from the project folder. Review the output before proceeding:

```powershell
git status
git add .
git diff --staged
git commit -m "Describe the completed change"
git push
git status
```

For an existing repository, there is no need to repeat `git init`, add `origin` again, or recreate the GitHub repository for each commit.

## Undo a commit that was already pushed

A commit is a saved snapshot in Git history. `c47c62e` identifies the commit that added PostgreSQL helpers, DWH documentation, container commands, and revised comments. Choose **one** option below; they have different effects.

### Keep the files, but remove the latest commit from history

Use this when you want to undo the commit/push and keep the work locally for a later commit. First check the branch and latest commit:

```powershell
git status
git log --oneline -3
git fetch origin
git log --oneline -1 origin/main
```

For this example, proceed only if you are on `main` and both local and remote tips are `c47c62e`. If either tip differs, inspect the new commits before resetting. Run each command separately and check that it succeeds:

```powershell
git reset --mixed c47c62e~1
git push --force-with-lease=refs/heads/main:c47c62e origin main
git status
```

`~1` means the parent commit. `--mixed` moves the branch back and unstages changes while keeping working files, including edits made since the commit. Files first added by the removed commit become untracked. This guide's current edits also remain on disk. **Do not use `--hard` to keep your work.**

The push rewrites remote `main`, removing this commit from that branch's history. The explicit lease rejects the push if remote `main` no longer points to `c47c62e`; do not bypass a rejection. Coordinate if others use the branch. Protected branches may reject history rewriting. Removing a commit from a branch does not guarantee its object or GitHub URL is immediately erased.

### Undo the code changes while preserving shared history

Use a revert when you want the earlier file contents restored through a new commit, keeping the original commit visible. Start on `main` with a clean working tree; commit or stash pending work first. Since this guide has just been edited, the commands below stash it too:

```powershell
git stash push -u -m "Save local edits before reverting c47c62e"
git revert --no-edit c47c62e
git push origin main
git stash pop
```

Only pop the stash if the stash command actually saved one and the revert/push succeeded. Check each command's result before continuing. A revert removes the original commit's changes, including newly added files; it does not merely uncommit them. If conflicts occur, resolve them and follow `git status`, or cancel the revert with `git revert --abort`. A stash pop can also require conflict resolution.

These commands are documented for you to execute; editing this guide does not run them.

## Source notes

Adapted from your existing note:

[Creating and Connecting a GitHub Repository](<F:/Data Engineering/Training/Data Engineering Automation/Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy/My Notes/Creating and connecting a GitGub Repository/Creating_and_Connecting_a_GitHub_Repository.docx>)

This guide documents the workflow only. Creating it does not stage, commit, or push anything.
