# 🔧 Shrink Git Repository - Remove Models from History

## Problem
Your repo is still 3.2 GB because model files are in **git history** (old commits), even though they're now in `.gitignore`.

## Solution: Remove from History

### Option 1: Using BFG Repo Cleaner (Recommended - Easiest)

**Step 1: Download BFG**
- Download: https://rtyley.github.io/bfg-repo-cleaner/
- Save `bfg.jar` to your Whisper4Windows folder

**Step 2: Run BFG**
```powershell
# Remove all files larger than 100MB from all commits
java -jar bfg.jar --strip-blobs-bigger-than 100M

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**Step 3: Check size**
```powershell
git count-objects -vH
# Should now show ~10-50 MB
```

**Step 4: Force push** (⚠️ Only if you haven't shared the repo yet!)
```powershell
git push --force
```

---

### Option 2: Using git filter-repo (More modern)

**Step 1: Install git-filter-repo**
```powershell
pip install git-filter-repo
```

**Step 2: Remove the models folder from all history**
```powershell
git filter-repo --path backend/models --invert-paths
```

**Step 3: Force push**
```powershell
git push --force --all
```

---

### Option 3: Nuclear Option - Start Fresh

If you haven't pushed to GitHub yet, the easiest is to start with a fresh git repo:

```powershell
# Backup your work
cd ..
Copy-Item -Recurse Whisper4Windows Whisper4Windows-backup

# Delete .git folder
cd Whisper4Windows
Remove-Item -Recurse -Force .git

# Start fresh
git init
git add .
git commit -m "Initial commit - without model files"

# Check size
git count-objects -vH
# Should show ~10-50 MB ✅
```

---

## Quick Commands

### If you want the BFG method (easiest):
```powershell
# Download bfg.jar first, then:
java -jar bfg.jar --strip-blobs-bigger-than 100M
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git count-objects -vH
```

### If starting fresh:
```powershell
Remove-Item -Recurse -Force .git
git init
git add .
git commit -m "Initial commit"
```

---

## What These Commands Do

- **BFG**: Removes large files from all commits (fast and safe)
- **git gc --aggressive**: Garbage collects and compresses
- **git reflog expire**: Clears the reflog so old objects can be deleted
- **--force push**: Overwrites GitHub history (only if you're the only user)

---

## After Running

Check the size:
```powershell
git count-objects -vH
```

**Expected:**
- size: ~10-50 MB ✅
- in-pack: ~10-50 MB ✅

**vs Current:**
- size: 3.2 GB ❌

---

## Warning ⚠️

These commands **rewrite git history**. Only do this if:
- ✅ You haven't shared the repo yet, OR
- ✅ You're the only person using it, OR
- ✅ You've coordinated with collaborators

If others have cloned your repo, they'll need to re-clone after you force push.

---

## Recommended: Fresh Start

Since you're just setting up the repo, I recommend the "Nuclear Option":
```powershell
Remove-Item -Recurse -Force .git
git init
git add .
git commit -m "Initial commit without model files"
git remote add origin https://github.com/YOUR_USERNAME/Whisper4Windows.git
git push -u origin main
```

This gives you a clean 10-50 MB repo from the start! ✨

