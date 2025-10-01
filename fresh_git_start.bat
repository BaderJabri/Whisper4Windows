@echo off
echo ========================================
echo Fresh Git Start (Removes Large Files)
echo ========================================
echo.
echo WARNING: This will DELETE your current git history!
echo Your files will be safe, but git commits will be reset.
echo.
echo This will:
echo 1. Delete .git folder
echo 2. Create new git repo
echo 3. Commit all files (except models in .gitignore)
echo 4. Result: ~10-50 MB repo instead of 3.2 GB
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo [1/5] Deleting old git history...
rmdir /s /q .git

echo.
echo [2/5] Creating fresh git repository...
git init

echo.
echo [3/5] Adding all files (models excluded by .gitignore)...
git add .

echo.
echo [4/5] Creating initial commit...
git commit -m "Initial commit - Whisper4Windows speech-to-text app"

echo.
echo [5/5] Checking repository size...
git count-objects -vH

echo.
echo ========================================
echo Done! Your repo is now clean and small!
echo ========================================
echo.
echo Next steps:
echo 1. Add GitHub remote: git remote add origin YOUR_GITHUB_URL
echo 2. Push to GitHub: git push -u origin main
echo.
echo Your repo should now be ~10-50 MB instead of 3.2 GB ✅
echo.
pause

