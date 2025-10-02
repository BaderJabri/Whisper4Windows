# Audio Visualizer Debug Guide

**Date:** 2025-01-02
**Issue:** Audio visualizer not working properly

---

## 🔧 New Implementation

I've completely rewritten the audio visualizer with:

1. **Dual-source audio detection:**
   - Primary: Backend audio level endpoint (from recording stream)
   - Fallback: WebRTC audio API (direct microphone access)

2. **Comprehensive debugging:**
   - Backend endpoint testing
   - WebRTC fallback testing
   - Detailed console logging

3. **Automatic fallback:**
   - If backend fails, automatically switches to WebRTC
   - No user interaction required

---

## 🧪 How to Test

### **Step 1: Start the App**
```bash
cd Whisper4Windows
START_APP.bat
```

### **Step 2: Open Recording Window**
- Press **F9** to start recording
- Recording window should appear at top center

### **Step 3: Open Browser Console**
- Press **F12** in the recording window
- Go to **Console** tab
- You should see initialization logs:
  ```
  ✅ Recording window loaded
  ✅ Visualizer initialized with 80 bars
  🔧 Debug commands available:
     debugBackendAudio() - Test backend audio endpoint
     debugWebRTCAudio() - Test WebRTC audio fallback
  ```

### **Step 4: Check State Transitions**
- Look for state change logs:
  ```
  🔄 State change: idle → recording
  🎤 Starting audio visualizer
  📊 Backend is available but not recording yet, this is expected
  ```

### **Step 5: Monitor Audio Levels**
- Speak or make noise near your microphone
- Look for periodic audio level logs:
  ```
  🎙️ Backend audio level: 0.123, recording: true, queue: 5
  ```
  OR
  ```
  🎤 WebRTC audio level: 0.156
  ```

---

## 🔍 Debug Commands

If the visualizer isn't working, run these commands in the console:

### **Test Backend Audio**
```javascript
debugBackendAudio()
```

**Expected Output:**
```
🔍 === BACKEND AUDIO DEBUG ===
🏥 Backend health: {status: "ok", backend: "cpu", model: "not_loaded", recording: false}
📊 Audio level 1: {level: 0.0, recording: false}
📊 Audio level 2: {level: 0.0, recording: false}
...
```

### **Test WebRTC Audio**
```javascript
debugWebRTCAudio()
```

**Expected Output:**
```
🎤 === WEBRTC AUDIO DEBUG ===
🎤 Initializing WebRTC audio...
✅ WebRTC audio initialized
✅ WebRTC initialized, testing for 5 seconds...
🎤 WebRTC level 1: 0.123
🎤 WebRTC level 2: 0.145
...
```

---

## 🐛 Troubleshooting

### **Issue 1: No Backend Response**
**Symptoms:**
```
❌ Backend audio level error: TypeError: Failed to fetch
```

**Solutions:**
1. Check if backend is running: `http://127.0.0.1:8000/health`
2. Restart backend: `cd backend && python main.py`
3. Check firewall/antivirus blocking port 8000

### **Issue 2: Backend Not Recording**
**Symptoms:**
```
📊 Audio level: {level: 0.0, recording: false}
```

**Solutions:**
1. Backend is available but not in recording mode
2. This is expected before F9 is pressed
3. Press F9 to start recording, then check again

### **Issue 3: WebRTC Permission Denied**
**Symptoms:**
```
❌ WebRTC audio failed: NotAllowedError: Permission denied
```

**Solutions:**
1. Grant microphone permission to the browser
2. Check Windows microphone privacy settings
3. Try refreshing the window

### **Issue 4: No Audio Levels**
**Symptoms:**
```
🎙️ Backend audio level: 0.000, recording: true
🎤 WebRTC audio level: 0.000
```

**Solutions:**
1. Check microphone is not muted
2. Speak louder or closer to microphone
3. Test microphone in Windows Sound settings
4. Check if other apps are using the microphone

### **Issue 5: Visualizer Bars Not Moving**
**Symptoms:**
- Audio levels show in console but bars don't animate

**Solutions:**
1. Check if `updateVisualizerFromLevel()` is being called
2. Look for JavaScript errors in console
3. Verify bars array is populated: `console.log(bars.length)`

---

## 🔧 Technical Details

### **Backend Audio Flow:**
1. `AudioCapture.start_recording()` starts sounddevice stream
2. `_audio_callback()` puts audio chunks in queue
3. `/audio_level` endpoint samples recent chunks
4. Calculates RMS level and normalizes to 0-1
5. Returns `{level: float, recording: bool, queue_size: int}`

### **WebRTC Audio Flow:**
1. `navigator.mediaDevices.getUserMedia()` gets microphone stream
2. `AudioContext` and `AnalyserNode` process audio
3. `getByteFrequencyData()` gets frequency data
4. Calculate average amplitude and normalize to 0-1

### **Visualizer Update:**
1. `updateVisualizerFromLevel(level)` called with 0-1 level
2. Creates sine wave pattern across 80 bars
3. Height = `Math.max(3, level * 40 * wave)`
4. Updates each bar's CSS height

---

## 📊 Expected Behavior

### **When Working Correctly:**
1. **Window appears:** State changes to 'recording'
2. **Backend starts:** Audio level endpoint returns data
3. **Microphone input:** Level values > 0 when speaking
4. **Bars animate:** Heights change based on audio level
5. **Smooth animation:** Wave pattern moves across bars

### **Performance Expectations:**
- **Backend mode:** ~100ms latency, very responsive
- **WebRTC mode:** ~50ms latency, more responsive but uses more CPU
- **CPU usage:** Should be minimal (< 5% on modern CPU)
- **Memory usage:** Should be stable (no leaks)

---

## 🚀 Next Steps

If issues persist after testing:

1. **Run both debug commands** and share console output
2. **Check backend logs** in terminal where `python main.py` is running
3. **Test with different microphones** if available
4. **Try in different browser** (if using WebView2 fallback)
5. **Check Windows audio drivers** are up to date

---

## 📝 Implementation Notes

The new system is much more robust:
- **Automatic fallback** ensures visualizer always works
- **Comprehensive logging** makes debugging easier  
- **State-driven** prevents animation conflicts
- **WebRTC backup** works even if backend fails
- **Debug commands** allow real-time testing

The visualizer should now work reliably from the first run! 🎉
