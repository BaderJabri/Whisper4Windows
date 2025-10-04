management

# 🚀 Whisper4Windows Development Mode Guide

## Overview

Tauri provides excellent hot reload development capabilities, similar to Canva's live editing. This means you can see changes to your frontend HTML/CSS/JS **instantly** without rebuilding the Rust code every time.

## 🔥 Quick Start - Hot Reload Development

### **Method 1: Pure Tauri Dev Mode (Recommended)**

```bash
# Terminal 1: Start Backend (Python)
cd Whisper4Windows/backend
venv\Scripts\activate
python main.py

# Terminal 2: Start Frontend with Hot Reload
cd Whisper4Windows/frontend/src-tauri
cargo tauri dev
```

### **What This Gives You:**

1. **⚡ Frontend Hot Reload**: Changes to `frontend/dist/*.html`, `*.css`, `*.js` files appear instantly
2. **🔄 Rust Auto-Rebuild**: Rust code changes trigger automatic rebuild
3. **🎯 Fast Iteration**: No need to run START_APP.bat every time
4. **🔧 Dev Tools**: Built-in debugging and console access
5. **📱 Live Window**: Main window stays open for testing

---

## 🛠️ Development Workflow

### **Frontend Changes (Instant)**
- Edit `frontend/dist/recording.html` → **BANG!** Visible immediately
- Edit `frontend/dist/index.html` → **BANG!** Visible immediately  
- Change CSS styles → **BANG!** Visible immediately
- Modify JavaScript functions → **BANG!** Visible immediately

### **Rust Changes (Auto-rebuild)**
- Edit `frontend/src-tauri/src/lib.rs` → Automatically compiles and restarts
- Modify `Cargo.toml` → Automatically detects dependency changes
- Change Tauri commands → Automatically regenerates bindings

### **Backend Changes**
- Edit Python files (`main.py`, `audio_capture.py`, etc.) → Restart backend manually
- Backend changes require restart (Python doesn't have hot reload built-in)

---

## 📝 Development Commands Reference

### **Backend Development**
```bash
# Start backend once
cd backend
venv\Scripts\activate
python main.py

# Keep this running throughout development
```

### **Frontend Development**
```bash
# Terminal 1: Hot reload frontend (stays running)
cd frontend/src-tauri
cargo tauri dev

# This starts:
# - Tauri app in hot reload mode
# - Watches for file changes
# - Auto-rebuilds on Rust changes
# - Shows logs in terminal
```

### **Production Build**
```bash
# When ready for release
cd frontend/src-tauri
cargo tauri build --no-bundle
```

---

## 🎯 Testing Your Hardcoded Visualizer

Now that you have hot reload set up, you can easily test and iterate on the visualizer:

1. **Start Development Mode**:
   ```bash
   # Terminal 1
   cd backend && venv\Scripts\activate && python main.py
   
   # Terminal 2  
   cd frontend/src-tauri && cargo tauri dev
   ```

2. **Test Visualizer**:
   - Press F9 to open recording window
   - Should see the hardcoded visualizer animation
   - Open browser dev tools (F12) for console access

3. **Iterate Instantly**:
   - Edit `frontend/dist/recording.html`
   - Save file
   - **BANG!** Changes visible immediately
   - Test `testHardcodedVisualizer()` in console

---

## 🔧 Development Tips

### **Frontend Hot Reload Tips**
- **File watching**: Saves automatically trigger refresh
- **Console debugging**: F12 opens browser dev tools
- **Multiple windows**: Can have recording AND settings open
- **State persistence**: App state maintained across hot reloads

### **Rust Development Tips**
- **Compile errors**: Show in terminal with helpful messages
- **Log watching**: Use `log::info!()` for debugging
- **Dependency updates**: `cargo update` when needed
- **Clean builds**: `cargo clean` if things get stuck

### **Backend Development Tips**
- **Manual restart**: Python backend needs manual restart after changes
- **Log watching**: Python logs show in terminal
- **API testing**: Use browser dev tools or curl to test endpoints

---

## 🆚 Development vs Production Mode

### **Development Mode (`cargo tauri dev`)**
- ✅ Hot reload enabled
- ✅ Debug symbols included
- ✅ Fast compilation
- ✅ Detailed error messages
- ❌ Slower startup
- ❌ Larger binary size

### **Production Mode (`cargo tauri build`)**
- ✅ Optimized binary
- ✅ Smaller file size
- ✅ Faster startup
- ❌ No hot reload
- ❌ Manual rebuild required

---

## 🚨 Troubleshooting

### **File Lock Errors**
```bash
# If you get "Access denied" errors:
.\STOP_APP.bat  # Kill all processes first
cargo clean     # Clean build artifacts
cargo tauri dev # Try again
```

### **Hot Reload Not Working**
- Check file paths are correct
- Ensure backend is running on port 8000
- Try refreshing browser (F5)
- Check console for errors

### **Backend Connection Issues**
- Verify backend starts without errors
- Check `http://127.0.0.1:8000/health` in browser
- Ensure Python venv is activated

---

## 🎉 Benefits vs START_APP.bat

| Feature | START_APP.bat | Dev Mode |
|---------|---------------|----------|
| Frontend hot reload | ❌ | ✅ |
| Auto-rebuild on Rust changes | ❌ | ✅ |
| Development debugging | ❌ | ✅ |
| Fast iteration | ❌ | ✅ |
| Production-ready binary | ✅ | ❌ |

**Recommendation**: Use dev mode for day-to-day development, START_APP.bat only for testing final builds.

---

## 🔍 Next Steps

1. **Try it now**: `cargo tauri dev`
2. **Edit the visualizer**: Modify `frontend/dist/recording.html`
3. **See instant changes**: Watch the animation update live
4. **Debug easily**: Use browser dev tools for testing
5. **Iterate quickly**: Perfect your hardcoded visualizer

Happy developing! 🚀

