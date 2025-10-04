# 🎙️ Whisper4Windows

**Your Voice, Transcribed Instantly - 100% Private, No Internet Required**

Transform your voice into text anywhere on Windows with a simple keyboard shortcut. Whether you're writing emails, taking notes, or coding - Whisper4Windows puts professional speech-to-text at your fingertips, completely free and private.

![Whisper4Windows in Action](images/demo-google-search.png)
![Whisper4Windows in Action](images/settings-window.png)
*Speak naturally, watch your words appear instantly in any application*

---

## Why Whisper4Windows?

### 🔒 **Completely Private**

Your voice never leaves your computer. No cloud, no API keys, no subscriptions. Everything runs locally using OpenAI's powerful Whisper model.

### ⚡ **Lightning Fast**

With GPU acceleration, transcribe 5 seconds of speech in under 2 seconds. No waiting, no buffering - just instant results.

### 🎯 **Works Everywhere**

Press F9 from any app - Word, Chrome, Slack, VSCode - speak your thoughts, and watch text appear exactly where you need it.

### 🌍 **Truly Multilingual**

Supports 99 languages with automatic detection. Switch between languages effortlessly or lock to your preferred ones for better accuracy.

---

## 🎬 See It In Action

### **Simple 3-Step Workflow**

1. **Press F9** - Minimal recording window appears at top of your screen
2. **Speak naturally** - Watch the live visualizer respond to your voice
3. **Press F9 again** - Text appears instantly where your cursor is

![Processing Wave Animation](images/processing-wave-animation.png)
*Beautiful wave animation shows processing in real-time - all happening locally on your device*

---

## ⚙️ Powerful Settings, Simple Interface

Customize Whisper4Windows to work exactly how you want:

![Configuration](images/Configuration-Panel.png)
*Fine-tune your keyboard shortcuts, model quality, and processing device*

![Speech-to-Text Settings](images/Configuration-Panel-2.png)
*Choose your preferred languages, enable GPU acceleration, and control clipboard behavior*

![Sound Configuration](images/Sound-Panel.png)
*Select your microphone, adjust sound effects, and customize the experience*

### **Key Settings:**

- **🎯 Model Quality** - Balance speed vs accuracy (Tiny → Large V3)
- **⚙️ Processing Device** - Auto-detect or force GPU/CPU
- **🌍 Languages** - Auto-detect all 99 languages or pick your favorites
- **🎤 Microphone** - Select from all available input devices
- **🔊 Sound Effects** - Customizable beeps with volume control
- **📋 Clipboard** - Keep text in clipboard or auto-restore previous content
- **🎨 Themes** - Light, dark, or system-matched appearance

---

## 🚀 Getting Started

### **Quick Setup**

1. **Download** - Clone this repo or download the release
2. **Run** - Double-click `START_APP.bat`
3. **Wait** - First launch downloads the Whisper model (~500MB, one-time only)
4. **Start Dictating!** - Press F9 anywhere and speak

That's it! No accounts, no configuration wizards, no complicated setup.

### **Try It Now**

Open Notepad (or any text app), press **F9**, and say:

> "Hello world, this is Whisper for Windows transcribing my voice in real-time, completely offline and private."

Watch it appear instantly! ✨

---

## 💪 What You Can Do

- **📝 Write Emails** - Dictate emails 3x faster than typing
- **📄 Take Notes** - Capture meeting notes without looking away
- **💬 Chat Messages** - Respond quickly in Slack, Teams, Discord
- **📚 Write Documents** - Draft reports and documentation hands-free
- **💻 Code Comments** - Dictate code comments and documentation
- **🌐 Browse Faster** - Search Google by voice
- **♿ Accessibility** - Perfect for users who prefer or need voice input

---

## 🔧 System Requirements

**Minimum:**

- Windows 10/11
- 8GB RAM
- Microphone (built-in or external)

**Recommended for GPU Acceleration:**

- NVIDIA GPU (GTX 1060 or better)
- 16GB RAM
- CUDA 12.6+ & cuDNN 9.x installed

**Performance:**

- **GPU Mode:** 5 seconds of speech → 0.5-2 seconds transcription
- **CPU Mode:** 5 seconds of speech → 5-15 seconds transcription

📖 **Need help with GPU setup? [See installation guide →](INSTALLATION.md)**

## ❓ FAQ

**Q: Is this really free?**
A: Yes! 100% free and open-source. No subscriptions, no API keys, no hidden costs.

**Q: Do I need an internet connection?**
A: Only for the first-time model download (~500MB). After that, everything works completely offline.

**Q: Which languages are supported?**
A: All 99 languages that Whisper supports - from Afrikaans to Zulu, including English, Spanish, French, German, Chinese, Japanese, Arabic, and many more.

**Q: How accurate is it?**
A: Very! Using the same AI model that powers many commercial services. Accuracy improves with better quality models (Medium/Large) and GPU acceleration.

**Q: Will this slow down my computer?**
A: No. The app only uses resources when actively recording and transcribing. It sits quietly in the system tray otherwise.

**Q: Can I use it for work?**
A: Absolutely! Perfect for emails, documentation, meeting notes, and more. Since everything is local, it's suitable for confidential work.

---

## 🛠️ Troubleshooting

**Backend not starting?**

```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**GPU not detected?**

- Run `TEST_GPU.bat` to diagnose
- See [INSTALLATION.md](INSTALLATION.md) for GPU setup

**Hotkey not working?**

- Check system tray - app must be running
- Try restarting the app
- Some apps may block global hotkeys

📖 **[Full troubleshooting guide →](INSTALLATION.md#-troubleshooting)**

---

## 📚 Learn More

- **[INSTALLATION.md](INSTALLATION.md)** - Detailed setup guide
- **[TECHNICAL.md](TECHNICAL.md)** - Technical documentation for developers
- **[DEVELOPMENT_MODE.md](DEVELOPMENT_MODE.md)** - Development workflow guide

---

## 🤝 Contributing

Found a bug? Have a feature request? Contributions are welcome!

1. Fork the repository
2. Create your feature branch
3. Submit a pull request

---

## 📝 License

MIT License - Free to use and modify for personal or commercial use.

---

## ❤️ Acknowledgments

Built with incredible open-source technology:

- **Whisper** by OpenAI
- **faster-whisper** by Systran
- **Tauri** framework
- **FastAPI** framework

Inspired by Superwhisper for Mac.

---

**Ready to transform your workflow? Download Whisper4Windows now and experience the future of voice input on Windows.** 🎤
