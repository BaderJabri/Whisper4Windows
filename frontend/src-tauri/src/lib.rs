use std::sync::Arc;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, AppHandle, State,
};
use windows::Win32::{
    UI::Input::KeyboardAndMouse::{
        SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP,
        VK_CONTROL, VK_V, KEYEVENTF_EXTENDEDKEY,
    },
    System::DataExchange::{
        OpenClipboard, CloseClipboard, EmptyClipboard, SetClipboardData, GetClipboardData,
    },
    System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GlobalSize, GMEM_MOVEABLE},
    Foundation::{HWND, HANDLE, HGLOBAL},
};
use tokio::sync::Mutex;
use anyhow::Result;
use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, GlobalShortcutExt};

// Simple state - track model, device, and clipboard setting
#[derive(Debug, Clone)]
pub struct AppState {
    pub selected_model: Arc<Mutex<String>>,
    pub selected_device: Arc<Mutex<String>>,
    pub selected_microphone: Arc<Mutex<Option<i32>>>,  // Microphone device index (None = default)
    pub use_clipboard: Arc<Mutex<bool>>,  // New: whether to paste to clipboard
    pub selected_language: Arc<Mutex<String>>,  // Selected language code
    pub toggle_shortcut: Arc<Mutex<String>>,  // Toggle recording shortcut
    pub cancel_shortcut: Arc<Mutex<String>>,  // Cancel recording shortcut
    pub backend_child: Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>,  // Backend process handle
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            selected_model: Arc::new(Mutex::new("small".to_string())),
            selected_device: Arc::new(Mutex::new("auto".to_string())),
            selected_microphone: Arc::new(Mutex::new(None)),  // Default: None (use default device)
            use_clipboard: Arc::new(Mutex::new(true)),  // Default: enabled
            selected_language: Arc::new(Mutex::new("en".to_string())),  // Default: English
            toggle_shortcut: Arc::new(Mutex::new("F9".to_string())),  // Default: F9
            cancel_shortcut: Arc::new(Mutex::new("Escape".to_string())),  // Default: Escape
            backend_child: Arc::new(Mutex::new(None)),  // Will be set in setup
        }
    }
}

// Get current clipboard content (UTF-16 text)
fn get_clipboard_text() -> Option<Vec<u16>> {
    unsafe {
        const CF_UNICODETEXT: u32 = 13;
        
        if let Err(_) = OpenClipboard(HWND::default()) {
            return None;
        }

        let h_clipboard_data = match GetClipboardData(CF_UNICODETEXT) {
            Ok(handle) if !handle.is_invalid() => handle,
            _ => {
                let _ = CloseClipboard();
                return None;
            }
        };

        // Convert HANDLE to HGLOBAL
        let hglobal = HGLOBAL(h_clipboard_data.0 as _);
        
        let locked = GlobalLock(hglobal);
        if locked.is_null() {
            let _ = CloseClipboard();
            return None;
        }

        let size = GlobalSize(hglobal);
        if size == 0 {
            let _ = GlobalUnlock(hglobal);
            let _ = CloseClipboard();
            return None;
        }
        
        let mut data = vec![0u16; size / 2];
        std::ptr::copy_nonoverlapping(locked as *const u16, data.as_mut_ptr(), size / 2);

        let _ = GlobalUnlock(hglobal);
        let _ = CloseClipboard();

        Some(data)
    }
}

// Set clipboard text (UTF-16)
fn set_clipboard_text(text_utf16: &[u16]) -> Result<()> {
    unsafe {
        if let Err(e) = OpenClipboard(HWND::default()) {
            return Err(anyhow::anyhow!("Failed to open clipboard: {}", e));
        }

        if let Err(e) = EmptyClipboard() {
            let _ = CloseClipboard();
            return Err(anyhow::anyhow!("Failed to empty clipboard: {}", e));
        }

        let len = text_utf16.len() * std::mem::size_of::<u16>();
        let hmem = GlobalAlloc(GMEM_MOVEABLE, len)
            .map_err(|e| anyhow::anyhow!("Failed to allocate memory: {}", e))?;

        let locked = GlobalLock(hmem);
        if locked.is_null() {
            let _ = CloseClipboard();
            return Err(anyhow::anyhow!("Failed to lock memory"));
        }

        std::ptr::copy_nonoverlapping(text_utf16.as_ptr(), locked as *mut u16, text_utf16.len());
        let _ = GlobalUnlock(hmem);

        const CF_UNICODETEXT: u32 = 13;
        let result = SetClipboardData(CF_UNICODETEXT, HANDLE(hmem.0 as _));
        if let Err(e) = result {
            let _ = CloseClipboard();
            return Err(anyhow::anyhow!("Failed to set clipboard data: {}", e));
        }

        let _ = CloseClipboard();
        Ok(())
    }
}

// Text injection via clipboard with optional clipboard preservation
pub fn inject_text(text: &str, save_to_clipboard: bool) -> Result<()> {
    unsafe {
        // Save old clipboard content if we need to restore it
        let old_clipboard = if !save_to_clipboard {
            get_clipboard_text()
        } else {
            None
        };

        // Prepare text as UTF-16
        let mut text_utf16: Vec<u16> = text.encode_utf16().collect();
        text_utf16.push(0);

        // Set clipboard with new text
        set_clipboard_text(&text_utf16)?;

        // Wait for clipboard to update
        std::thread::sleep(std::time::Duration::from_millis(10));

        // Simulate Ctrl+V
        let inputs = vec![
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYEVENTF_EXTENDEDKEY, time: 0, dwExtraInfo: 0 },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT { wVk: VK_V, wScan: 0, dwFlags: KEYEVENTF_EXTENDEDKEY, time: 0, dwExtraInfo: 0 },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT { wVk: VK_V, wScan: 0, dwFlags: KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                    ki: KEYBDINPUT { wVk: VK_CONTROL, wScan: 0, dwFlags: KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, time: 0, dwExtraInfo: 0 },
                },
            },
        ];

        SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);

        // Restore old clipboard if needed
        if !save_to_clipboard {
            if let Some(old_text) = old_clipboard {
                std::thread::sleep(std::time::Duration::from_millis(50));
                let _ = set_clipboard_text(&old_text);
                log::info!("📋 Restored previous clipboard content");
            }
        } else {
            log::info!("📋 Text saved to clipboard");
        }
    }

    Ok(())
}

// Simple command: Inject text (always injects, optionally saves to clipboard)
#[tauri::command]
async fn inject_text_directly(text: String, save_to_clipboard: bool) -> Result<(), String> {
    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
    inject_text(&text, save_to_clipboard).map_err(|e| e.to_string())?;
    log::info!("✅ Injected: {} (clipboard: {})", text, if save_to_clipboard { "saved" } else { "not saved" });
    Ok(())
}

// Simple command: Start recording
#[tauri::command]
async fn cmd_start_recording(app: AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    log::info!("═══════════════════════════════════════════════");
    log::info!("🎬 START RECORDING");
    log::info!("═══════════════════════════════════════════════");

    let model = state.selected_model.lock().await.clone();
    let device = state.selected_device.lock().await.clone();
    let microphone = state.selected_microphone.lock().await.clone();
    let language = state.selected_language.lock().await.clone();

    // Position window at top center and show
    if let Some(win) = app.get_webview_window("recording") {
        // Get primary monitor to calculate center position
        if let Some(monitor) = win.current_monitor().map_err(|e| e.to_string())? {
            let screen_size = monitor.size();
            let window_size = win.outer_size().map_err(|e| e.to_string())?;

            // Calculate centered X position, top Y position (50px from top)
            let x = (screen_size.width as i32 - window_size.width as i32) / 2;
            let y = 50;

            win.set_position(tauri::PhysicalPosition::new(x, y)).map_err(|e| e.to_string())?;
        }

        win.show().map_err(|e| e.to_string())?;

        // Play start sound
        let _ = win.eval("playStartSound()");

        log::info!("✅ Window shown at top center");
    }

    // Call backend /start
    let client = reqwest::Client::new();
    tokio::spawn(async move {
        // Use None for auto-detect, otherwise use the selected language
        let lang_value = if language == "auto" {
            serde_json::Value::Null
        } else {
            serde_json::json!(language)
        };

        let mut request_body = serde_json::json!({
            "model_size": model,
            "language": lang_value,
            "device": device
        });

        // Add device_index if a specific microphone is selected
        if let Some(device_index) = microphone {
            request_body["device_index"] = serde_json::json!(device_index);
        }

        match client.post("http://127.0.0.1:8000/start")
            .json(&request_body)
            .send()
            .await
        {
            Ok(resp) if resp.status().is_success() => log::info!("✅ Backend started"),
            Ok(resp) => log::error!("❌ Backend error: {}", resp.status()),
            Err(e) => log::error!("❌ Request failed: {}", e),
        }
    });

    Ok(())
}

// Simple command: Cancel recording
#[tauri::command]
async fn cmd_cancel_recording(app: AppHandle) -> Result<(), String> {
    log::info!("═══════════════════════════════════════════════");
    log::info!("❌ CANCEL RECORDING");
    log::info!("═══════════════════════════════════════════════");

    // Call backend /cancel
    let client = reqwest::Client::new();
    tokio::spawn(async move {
        match client.post("http://127.0.0.1:8000/cancel")
            .send()
            .await
        {
            Ok(resp) if resp.status().is_success() => log::info!("✅ Backend cancelled"),
            Ok(resp) => log::error!("❌ Backend error: {}", resp.status()),
            Err(e) => log::error!("❌ Request failed: {}", e),
        }
    });

    // Hide window
    if let Some(win) = app.get_webview_window("recording") {
        win.hide().map_err(|e| e.to_string())?;
        log::info!("✅ Window hidden");
    }

    Ok(())
}

// Simple command: Stop recording (called by F9 when window visible)
#[tauri::command]
async fn cmd_stop_recording(app: AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    log::info!("═══════════════════════════════════════════════");
    log::info!("🛑 STOP RECORDING");
    log::info!("═══════════════════════════════════════════════");

    // Call showProcessing() in the recording window via eval
    if let Some(win) = app.get_webview_window("recording") {
        let _ = win.eval("showProcessing()");
        let _ = win.eval("playStopSound()");
        log::info!("📢 Called showProcessing() in frontend");
    }

    // Small delay to let frontend update UI
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    // Call backend /stop to get transcription
    let client = reqwest::Client::new();
    let text_to_inject = match client.post("http://127.0.0.1:8000/stop")
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            log::info!("✅ Backend stopped");

            // Get transcription text
            if let Ok(data) = resp.json::<serde_json::Value>().await {
                if let Some(text) = data.get("text").and_then(|t| t.as_str()) {
                    log::info!("📝 Transcription: {}", text);
                    Some(text.to_string())
                } else {
                    None
                }
            } else {
                None
            }
        }
        Ok(resp) => {
            log::error!("❌ Backend error: {}", resp.status());
            None
        }
        Err(e) => {
            log::error!("❌ Request failed: {}", e);
            None
        }
    };

    // Hide window FIRST (to restore focus to text field)
    if let Some(win) = app.get_webview_window("recording") {
        win.hide().map_err(|e| e.to_string())?;
        log::info!("✅ Window hidden");
    }

    // Wait for focus to return to the text field
    tokio::time::sleep(tokio::time::Duration::from_millis(150)).await;

    // THEN inject text (always inject, clipboard setting controls if we save to clipboard)
    if let Some(text) = text_to_inject {
        let save_to_clipboard = *state.use_clipboard.lock().await;
        log::info!("🔧 Clipboard save setting: {}", save_to_clipboard);
        
        if let Err(e) = inject_text(&text, save_to_clipboard) {
            log::error!("❌ Injection failed: {}", e);
        } else {
            log::info!("✅ Text injected (clipboard: {})", if save_to_clipboard { "saved" } else { "restored" });
        }
    }

    Ok(())
}

// F9 shortcut handler
#[tauri::command]
async fn cmd_toggle_recording(app: AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    log::info!("⌨️ F9 PRESSED");

    if let Some(win) = app.get_webview_window("recording") {
        let is_visible = win.is_visible().unwrap_or(false);
        log::info!("   Window visible: {}", is_visible);

        if is_visible {
            // Stop - call backend /stop, transcribe, and inject
            cmd_stop_recording(app, state).await?;
        } else {
            // Start
            cmd_start_recording(app, state).await?;
        }
    }

    Ok(())
}

// Settings command
#[tauri::command]
async fn set_model_and_device(
    model: String,
    device: String,
    state: State<'_, AppState>
) -> Result<(), String> {
    *state.selected_model.lock().await = model.clone();
    *state.selected_device.lock().await = device.clone();
    log::info!("⚙️ Settings: model={}, device={}", model, device);
    Ok(())
}

// Set microphone device
#[tauri::command]
async fn set_microphone_device(
    device_index: Option<i32>,
    state: State<'_, AppState>
) -> Result<(), String> {
    *state.selected_microphone.lock().await = device_index;
    log::info!("🎤 Microphone device set to: {:?}", device_index);
    Ok(())
}

// Get microphone device
#[tauri::command]
async fn get_microphone_device(state: State<'_, AppState>) -> Result<Option<i32>, String> {
    Ok(*state.selected_microphone.lock().await)
}

// New: Set clipboard paste setting
#[tauri::command]
async fn set_clipboard_paste(
    enabled: bool,
    state: State<'_, AppState>
) -> Result<(), String> {
    *state.use_clipboard.lock().await = enabled;
    log::info!("⚙️ Clipboard paste setting: {}", enabled);
    Ok(())
}

// New: Get clipboard paste setting
#[tauri::command]
async fn get_clipboard_paste(state: State<'_, AppState>) -> Result<bool, String> {
    let enabled = *state.use_clipboard.lock().await;
    Ok(enabled)
}

// Language commands
#[tauri::command]
async fn set_language(language: String, state: State<'_, AppState>) -> Result<(), String> {
    *state.selected_language.lock().await = language.clone();
    log::info!("🌐 Language set to: {}", language);
    Ok(())
}

#[tauri::command]
async fn get_language(state: State<'_, AppState>) -> Result<String, String> {
    Ok(state.selected_language.lock().await.clone())
}

// Helper function to parse shortcut string to Shortcut object
fn parse_shortcut(shortcut_str: &str) -> Option<Shortcut> {

    let parts: Vec<&str> = shortcut_str.split('+').collect();
    let mut modifiers = Modifiers::empty();
    let mut key_code: Option<Code> = None;

    for part in parts {
        let part = part.trim();
        match part {
            "Ctrl" | "Control" => modifiers |= Modifiers::CONTROL,
            "Alt" => modifiers |= Modifiers::ALT,
            "Shift" => modifiers |= Modifiers::SHIFT,
            "Super" | "Win" | "Meta" => modifiers |= Modifiers::SUPER,
            // Function keys
            "F1" => key_code = Some(Code::F1),
            "F2" => key_code = Some(Code::F2),
            "F3" => key_code = Some(Code::F3),
            "F4" => key_code = Some(Code::F4),
            "F5" => key_code = Some(Code::F5),
            "F6" => key_code = Some(Code::F6),
            "F7" => key_code = Some(Code::F7),
            "F8" => key_code = Some(Code::F8),
            "F9" => key_code = Some(Code::F9),
            "F10" => key_code = Some(Code::F10),
            "F11" => key_code = Some(Code::F11),
            "F12" => key_code = Some(Code::F12),
            // Special keys
            "Escape" | "Esc" => key_code = Some(Code::Escape),
            "Space" => key_code = Some(Code::Space),
            "Tab" => key_code = Some(Code::Tab),
            "Enter" | "Return" => key_code = Some(Code::Enter),
            "Backspace" => key_code = Some(Code::Backspace),
            "Delete" => key_code = Some(Code::Delete),
            "Insert" => key_code = Some(Code::Insert),
            "Home" => key_code = Some(Code::Home),
            "End" => key_code = Some(Code::End),
            "PageUp" => key_code = Some(Code::PageUp),
            "PageDown" => key_code = Some(Code::PageDown),
            // Arrow keys
            "ArrowUp" | "Up" => key_code = Some(Code::ArrowUp),
            "ArrowDown" | "Down" => key_code = Some(Code::ArrowDown),
            "ArrowLeft" | "Left" => key_code = Some(Code::ArrowLeft),
            "ArrowRight" | "Right" => key_code = Some(Code::ArrowRight),
            // Letter keys (single character)
            s if s.len() == 1 && s.chars().next().unwrap().is_alphabetic() => {
                let ch = s.chars().next().unwrap().to_ascii_uppercase();
                key_code = match ch {
                    'A' => Some(Code::KeyA),
                    'B' => Some(Code::KeyB),
                    'C' => Some(Code::KeyC),
                    'D' => Some(Code::KeyD),
                    'E' => Some(Code::KeyE),
                    'F' => Some(Code::KeyF),
                    'G' => Some(Code::KeyG),
                    'H' => Some(Code::KeyH),
                    'I' => Some(Code::KeyI),
                    'J' => Some(Code::KeyJ),
                    'K' => Some(Code::KeyK),
                    'L' => Some(Code::KeyL),
                    'M' => Some(Code::KeyM),
                    'N' => Some(Code::KeyN),
                    'O' => Some(Code::KeyO),
                    'P' => Some(Code::KeyP),
                    'Q' => Some(Code::KeyQ),
                    'R' => Some(Code::KeyR),
                    'S' => Some(Code::KeyS),
                    'T' => Some(Code::KeyT),
                    'U' => Some(Code::KeyU),
                    'V' => Some(Code::KeyV),
                    'W' => Some(Code::KeyW),
                    'X' => Some(Code::KeyX),
                    'Y' => Some(Code::KeyY),
                    'Z' => Some(Code::KeyZ),
                    _ => None,
                };
            }
            // Number keys
            s if s.len() == 1 && s.chars().next().unwrap().is_numeric() => {
                let ch = s.chars().next().unwrap();
                key_code = match ch {
                    '0' => Some(Code::Digit0),
                    '1' => Some(Code::Digit1),
                    '2' => Some(Code::Digit2),
                    '3' => Some(Code::Digit3),
                    '4' => Some(Code::Digit4),
                    '5' => Some(Code::Digit5),
                    '6' => Some(Code::Digit6),
                    '7' => Some(Code::Digit7),
                    '8' => Some(Code::Digit8),
                    '9' => Some(Code::Digit9),
                    _ => None,
                };
            }
            // Special symbol keys
            "\\" | "Backslash" => key_code = Some(Code::Backslash),
            "/" | "Slash" => key_code = Some(Code::Slash),
            ";" | "Semicolon" => key_code = Some(Code::Semicolon),
            "'" | "Quote" => key_code = Some(Code::Quote),
            "[" | "BracketLeft" => key_code = Some(Code::BracketLeft),
            "]" | "BracketRight" => key_code = Some(Code::BracketRight),
            "," | "Comma" => key_code = Some(Code::Comma),
            "." | "Period" => key_code = Some(Code::Period),
            "`" | "Backquote" => key_code = Some(Code::Backquote),
            "-" | "Minus" => key_code = Some(Code::Minus),
            "=" | "Equal" => key_code = Some(Code::Equal),
            _ => {
                log::warn!("⚠️ Unknown key: {}", part);
            }
        }
    }

    if let Some(code) = key_code {
        Some(Shortcut::new(Some(modifiers), code))
    } else {
        None
    }
}

// Shortcut commands
#[tauri::command]
async fn save_shortcuts(
    shortcuts: std::collections::HashMap<String, String>,
    app: AppHandle,
    state: State<'_, AppState>
) -> Result<(), String> {
    // Handle toggle shortcut
    if let Some(toggle) = shortcuts.get("toggle") {
        let old_shortcut = state.toggle_shortcut.lock().await.clone();
        *state.toggle_shortcut.lock().await = toggle.clone();
        log::info!("⌨️ Toggle shortcut saved: {} (was: {})", toggle, old_shortcut);

        // Re-register the shortcut
        // First, unregister old shortcut
        if let Some(old_sc) = parse_shortcut(&old_shortcut) {
            if let Err(e) = app.global_shortcut().unregister(old_sc) {
                log::warn!("⚠️ Failed to unregister old toggle shortcut {}: {}", old_shortcut, e);
            } else {
                log::info!("✅ Unregistered old toggle shortcut: {}", old_shortcut);
            }
        }

        // Register new shortcut
        if let Some(new_sc) = parse_shortcut(toggle) {
            if let Err(e) = app.global_shortcut().register(new_sc) {
                log::error!("❌ Failed to register new toggle shortcut {}: {}", toggle, e);
                return Err(format!("Failed to register toggle shortcut: {}", e));
            } else {
                log::info!("✅ Registered new toggle shortcut: {}", toggle);
            }
        } else {
            log::error!("❌ Failed to parse toggle shortcut: {}", toggle);
            return Err(format!("Invalid toggle shortcut format: {}", toggle));
        }
    }

    // Handle cancel shortcut
    if let Some(cancel) = shortcuts.get("cancel") {
        let old_shortcut = state.cancel_shortcut.lock().await.clone();
        *state.cancel_shortcut.lock().await = cancel.clone();
        log::info!("⌨️ Cancel shortcut saved: {} (was: {})", cancel, old_shortcut);

        // Re-register the shortcut
        // First, unregister old shortcut
        if let Some(old_sc) = parse_shortcut(&old_shortcut) {
            if let Err(e) = app.global_shortcut().unregister(old_sc) {
                log::warn!("⚠️ Failed to unregister old cancel shortcut {}: {}", old_shortcut, e);
            } else {
                log::info!("✅ Unregistered old cancel shortcut: {}", old_shortcut);
            }
        }

        // Register new shortcut
        if let Some(new_sc) = parse_shortcut(cancel) {
            if let Err(e) = app.global_shortcut().register(new_sc) {
                log::error!("❌ Failed to register new cancel shortcut {}: {}", cancel, e);
                return Err(format!("Failed to register cancel shortcut: {}", e));
            } else {
                log::info!("✅ Registered new cancel shortcut: {}", cancel);
            }
        } else {
            log::error!("❌ Failed to parse cancel shortcut: {}", cancel);
            return Err(format!("Invalid cancel shortcut format: {}", cancel));
        }
    }

    Ok(())
}

#[tauri::command]
async fn get_toggle_shortcut(state: State<'_, AppState>) -> Result<String, String> {
    Ok(state.toggle_shortcut.lock().await.clone())
}

#[tauri::command]
async fn get_cancel_shortcut(state: State<'_, AppState>) -> Result<String, String> {
    Ok(state.cancel_shortcut.lock().await.clone())
}

// Stub commands for settings that don't need backend implementation yet
#[tauri::command]
async fn get_preferred_languages() -> Result<Vec<String>, String> {
    Ok(vec![])  // Not used anymore, but kept for compatibility
}

#[tauri::command]
async fn set_preferred_languages(_languages: Vec<String>) -> Result<(), String> {
    Ok(())  // Not used anymore, but kept for compatibility
}

#[tauri::command]
async fn get_launch_on_login() -> Result<bool, String> {
    Ok(false)  // TODO: Implement later
}

#[tauri::command]
async fn set_launch_on_login(_enabled: bool) -> Result<(), String> {
    Ok(())  // TODO: Implement later
}

#[tauri::command]
async fn check_for_updates() -> Result<String, String> {
    Ok("No updates available".to_string())  // TODO: Implement GitHub release check
}

// Tray menu
fn create_tray_menu(app: &AppHandle) -> Result<Menu<tauri::Wry>, tauri::Error> {
    let toggle = MenuItem::with_id(app, "toggle", "🎙️ Start/Stop Recording (F9)", true, None::<&str>)?;
    let settings = MenuItem::with_id(app, "settings", "⚙️ Settings", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "❌ Quit", true, None::<&str>)?;
    Menu::with_items(app, &[&toggle, &settings, &quit])
}

fn handle_tray_event(app: &AppHandle, event: TrayIconEvent) {
    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
        if let Some(win) = app.get_webview_window("main") {
            let _ = if win.is_visible().unwrap_or(false) { win.hide() } else { win.show().and_then(|_| win.set_focus()) };
        }
    }
}

fn handle_menu_event(app: &AppHandle, event: tauri::menu::MenuEvent) {
    log::info!("📋 Menu clicked: {}", event.id.as_ref());

    match event.id.as_ref() {
        "toggle" => {
            let app_clone = app.clone();
            tauri::async_runtime::spawn(async move {
                let _ = cmd_toggle_recording(app_clone.clone(), app_clone.state()).await;
            });
        }
        "settings" => {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show().and_then(|_| win.set_focus());
            }
        }
        "quit" => {
            let app_clone = app.clone();
            tauri::async_runtime::spawn(async move {
                let state: tauri::State<AppState> = app_clone.state();
                if let Some(child) = state.backend_child.lock().await.take() {
                    log::info!("🛑 Killing backend process...");
                    let _ = child.kill();
                    log::info!("✅ Backend process terminated");
                }
                app_clone.exit(0);
            });
        }
        _ => {}
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            log::info!("🔒 Single instance check - app already running, focusing existing window");
            // Bring main window to front if already running
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
            use tauri::WebviewWindowBuilder;

            // Logging
            app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .level(log::LevelFilter::Info)
                    .target(tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Stdout))
                    .target(tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::LogDir { file_name: Some("app".to_string()) }))
                    .build(),
            )?;

            log::info!("🚀 Whisper4Windows starting...");

            // Start backend sidecar
            log::info!("🔧 Starting backend server...");
            use tauri::Manager;
            use tauri_plugin_shell::ShellExt;

            let sidecar_command = app.app_handle()
                .shell()
                .sidecar("whisper-backend")
                .expect("Failed to create sidecar command");

            let (_rx, child) = sidecar_command
                .spawn()
                .expect("Failed to spawn backend sidecar");

            // Store the child process in state so we can kill it on app exit
            let state: tauri::State<AppState> = app.state();
            tauri::async_runtime::block_on(async {
                *state.backend_child.lock().await = Some(child);
            });

            // Wait a moment for backend to start
            std::thread::sleep(std::time::Duration::from_secs(2));
            log::info!("✅ Backend server started");

            // Create recording window
            WebviewWindowBuilder::new(app, "recording", tauri::WebviewUrl::App("recording.html".into()))
                .title("Recording")
                .inner_size(616.0, 140.0)
                .resizable(false)
                .position(0.0, 50.0)  // Will be centered horizontally when shown
                .always_on_top(true)
                .visible(false)
                .skip_taskbar(true)
                .decorations(false)
                .transparent(true)
                .focused(false)
                .build()?;

            log::info!("✅ Recording window created");

            // Tray
            let menu = create_tray_menu(app.handle())?;
            let tray = TrayIconBuilder::new()
                .menu(&menu)
                .icon(app.default_window_icon().unwrap().clone())
                .on_menu_event(|app, event| handle_menu_event(app, event))
                .build(app)?;

            let app_handle = app.handle().clone();
            tray.on_tray_icon_event(move |_tray, event| handle_tray_event(&app_handle, event));

            log::info!("✅ Tray icon created");

            // Global shortcuts handler
            let app_handle_hotkey = app.handle().clone();

            app.handle().plugin(
                tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |_app, shortcut, event| {
                        use tauri_plugin_global_shortcut::ShortcutState;
                        // Only trigger on key press, not release
                        if event.state == ShortcutState::Pressed {
                            let app_clone = app_handle_hotkey.clone();
                            let shortcut_str = format!("{:?}", shortcut); // Format outside async block

                            tauri::async_runtime::spawn(async move {
                                let state: tauri::State<AppState> = app_clone.state();
                                let toggle_sc = state.toggle_shortcut.lock().await.clone();
                                let cancel_sc = state.cancel_shortcut.lock().await.clone();

                                // Check if this is the cancel shortcut
                                if let Some(parsed_cancel) = parse_shortcut(&cancel_sc) {
                                    let cancel_str = format!("{:?}", parsed_cancel);
                                    if shortcut_str == cancel_str {
                                        log::info!("🔥 CANCEL SHORTCUT TRIGGERED ({})", cancel_sc);
                                        // Only cancel if recording window is visible
                                        if let Some(win) = app_clone.get_webview_window("recording") {
                                            if win.is_visible().unwrap_or(false) {
                                                let _ = cmd_cancel_recording(app_clone.clone()).await;
                                                return;
                                            }
                                        }
                                    }
                                }

                                // Check if this is the toggle shortcut
                                if let Some(parsed_toggle) = parse_shortcut(&toggle_sc) {
                                    let toggle_str = format!("{:?}", parsed_toggle);
                                    if shortcut_str == toggle_str {
                                        log::info!("🔥 TOGGLE SHORTCUT TRIGGERED ({})", toggle_sc);
                                        let _ = cmd_toggle_recording(app_clone.clone(), app_clone.state()).await;
                                    }
                                }
                            });
                        }
                    })
                    .build()
            )?;

            // Register initial shortcuts
            let state: tauri::State<AppState> = app.state();
            let (initial_toggle, initial_cancel) = tauri::async_runtime::block_on(async {
                (
                    state.toggle_shortcut.lock().await.clone(),
                    state.cancel_shortcut.lock().await.clone()
                )
            });

            // Register toggle shortcut
            if let Some(toggle_sc) = parse_shortcut(&initial_toggle) {
                if let Err(e) = app.global_shortcut().register(toggle_sc) {
                    log::error!("❌ Failed to register toggle shortcut {}: {}", initial_toggle, e);
                } else {
                    log::info!("✅ Toggle shortcut registered: {}", initial_toggle);
                }
            } else {
                log::error!("❌ Failed to parse initial toggle shortcut: {}", initial_toggle);
            }

            // Register cancel shortcut
            if let Some(cancel_sc) = parse_shortcut(&initial_cancel) {
                if let Err(e) = app.global_shortcut().register(cancel_sc) {
                    log::error!("❌ Failed to register cancel shortcut {}: {}", initial_cancel, e);
                } else {
                    log::info!("✅ Cancel shortcut registered: {}", initial_cancel);
                }
            } else {
                log::error!("❌ Failed to parse initial cancel shortcut: {}", initial_cancel);
            }

            log::info!("💡 Press F9 to start/stop recording");
            Ok(())
        })
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![
            inject_text_directly,
            cmd_start_recording,
            cmd_stop_recording,
            cmd_cancel_recording,
            cmd_toggle_recording,
            set_model_and_device,
            set_microphone_device,
            get_microphone_device,
            set_clipboard_paste,
            get_clipboard_paste,
            set_language,
            get_language,
            save_shortcuts,
            get_toggle_shortcut,
            get_cancel_shortcut,
            get_preferred_languages,
            set_preferred_languages,
            get_launch_on_login,
            set_launch_on_login,
            check_for_updates
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

