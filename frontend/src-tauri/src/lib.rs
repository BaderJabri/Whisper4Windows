use std::sync::Arc;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, AppHandle, State, Emitter,
};
// Global shortcut imports for future use
// use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut};
use windows::Win32::{
    UI::Input::KeyboardAndMouse::{
        SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_UNICODE, VIRTUAL_KEY,
        KEYEVENTF_KEYUP,
    },
};
use tokio::sync::Mutex;
use anyhow::Result;

// Application state
#[derive(Debug, Clone)]
pub struct AppState {
    pub is_recording: Arc<Mutex<bool>>,
    pub demo_text: Arc<Mutex<String>>,
    pub backend_url: Arc<Mutex<String>>,
    pub hotkey_mode: Arc<Mutex<bool>>, // Track if push-to-talk hotkey is active
    pub selected_model: Arc<Mutex<String>>,
    pub selected_device: Arc<Mutex<String>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            is_recording: Arc::new(Mutex::new(false)),
            demo_text: Arc::new(Mutex::new(
                "Hello from Whisper4Windows! This is a working text injection demo.".to_string()
            )),
            backend_url: Arc::new(Mutex::new("http://127.0.0.1:8000".to_string())),
            hotkey_mode: Arc::new(Mutex::new(false)),
            selected_model: Arc::new(Mutex::new("small".to_string())),
            selected_device: Arc::new(Mutex::new("auto".to_string())),
        }
    }
}

// Text injection using Windows SendInput API
pub fn inject_text(text: &str) -> Result<()> {
    let text_utf16: Vec<u16> = text.encode_utf16().collect();
    let mut inputs = Vec::new();

    for &ch in &text_utf16 {
        // Key down
        inputs.push(INPUT {
            r#type: INPUT_KEYBOARD,
            Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                ki: KEYBDINPUT {
                    wVk: VIRTUAL_KEY(0),
                    wScan: ch,
                    dwFlags: KEYEVENTF_UNICODE,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        });

        // Key up
        inputs.push(INPUT {
            r#type: INPUT_KEYBOARD,
            Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                ki: KEYBDINPUT {
                    wVk: VIRTUAL_KEY(0),
                    wScan: ch,
                    dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        });
    }

    unsafe {
        SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
    }

    Ok(())
}

// Tauri commands
#[tauri::command]
async fn toggle_recording(state: State<'_, AppState>) -> Result<bool, String> {
    let mut is_recording = state.is_recording.lock().await;
    *is_recording = !*is_recording;
    let status = *is_recording;
    log::info!("Recording status: {}", status);
    Ok(status)
}

#[tauri::command]
async fn get_demo_text(state: State<'_, AppState>) -> Result<String, String> {
    let demo_text = state.demo_text.lock().await;
    Ok(demo_text.clone())
}

#[tauri::command]
async fn set_demo_text(text: String, state: State<'_, AppState>) -> Result<(), String> {
    let mut demo_text = state.demo_text.lock().await;
    *demo_text = text.clone();
    log::info!("Demo text updated: {}", text);
    Ok(())
}

#[tauri::command]
async fn inject_demo_text(state: State<'_, AppState>) -> Result<(), String> {
    let demo_text = state.demo_text.lock().await;
    let text = demo_text.clone();
    drop(demo_text);

    // Wait for user to focus target window
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    inject_text(&text).map_err(|e| e.to_string())?;
    log::info!("✅ Injected text: {}", text);
    Ok(())
}

#[tauri::command]
async fn inject_text_directly(text: String) -> Result<(), String> {
    // Inject text directly without saving to state
    // Small delay to allow window focus if needed
    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

    inject_text(&text).map_err(|e| e.to_string())?;
    log::info!("✅ Live injected: {}", text);
    Ok(())
}

#[tauri::command]
async fn toggle_hotkey_recording(
    app: AppHandle,
    state: State<'_, AppState>
) -> Result<(), String> {
    let mut is_recording = state.is_recording.lock().await;
    
    log::info!("========================================");
    log::info!("🔍 HOTKEY PRESSED - Current state: {}", *is_recording);
    log::info!("========================================");
    
    if *is_recording {
        // FUNCTION 2: Stop recording and transcribe
        log::info!("📌 EXECUTING: Stop Recording Function");
        log::info!("🛑 Stopping recording and transcribing...");
        
        // Don't reset state here - let the frontend do it after cleanup
        
        // Emit event to recording window to stop
        if let Some(recording_window) = app.get_webview_window("recording") {
            recording_window.emit("hotkey-stop-recording", ()).map_err(|e| e.to_string())?;
            log::info!("✅ Emitted stop event to recording window");
        } else {
            log::error!("❌ Recording window not found");
            *is_recording = false; // Reset state if window is gone
        }
        
    } else {
        // FUNCTION 1: Start recording
        log::info!("📌 EXECUTING: Start Recording Function");
        log::info!("🎙️ Starting new recording...");
        
        let model = state.selected_model.lock().await.clone();
        let device = state.selected_device.lock().await.clone();
        
        // Show recording window - don't check visibility, just show it
        if let Some(recording_window) = app.get_webview_window("recording") {
            recording_window.show().map_err(|e| e.to_string())?;
            log::info!("📺 Recording window shown");
        } else {
            log::error!("❌ Recording window not found");
            return Err("Recording window not found".to_string());
        }
        
        // Set recording state IMMEDIATELY
        *is_recording = true;
        log::info!("✅ Recording state set to TRUE");
        
        // Start backend recording
        let backend_url = state.backend_url.lock().await.clone();
        let client = reqwest::Client::new();
        
        tokio::spawn(async move {
            let result = client.post(format!("{}/start", backend_url))
                .json(&serde_json::json!({
                    "model_size": model,
                    "language": "en",
                    "device": device
                }))
                .send()
                .await;
                
            match result {
                Ok(response) => {
                    if response.status().is_success() {
                        log::info!("✅ Backend recording started");
                    } else {
                        log::error!("❌ Backend start failed: {}", response.status());
                    }
                }
                Err(e) => log::error!("❌ Backend request error: {}", e)
            }
        });
    }
    
    log::info!("========================================");
    Ok(())
}

#[tauri::command]
async fn reset_recording_state(state: State<'_, AppState>) -> Result<(), String> {
    let mut is_recording = state.is_recording.lock().await;
    *is_recording = false;
    log::info!("🔄 Recording state reset to false");
    Ok(())
}

#[tauri::command]
async fn set_model_and_device(
    model: String,
    device: String,
    state: State<'_, AppState>
) -> Result<(), String> {
    let mut selected_model = state.selected_model.lock().await;
    let mut selected_device = state.selected_device.lock().await;
    *selected_model = model.clone();
    *selected_device = device.clone();
    log::info!("Settings updated: model={}, device={}", model, device);
    Ok(())
}

// Create tray menu
fn create_tray_menu(app: &AppHandle) -> Result<Menu<tauri::Wry>, tauri::Error> {
    let settings = MenuItem::with_id(app, "settings", "⚙️ Settings", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "❌ Quit", true, None::<&str>)?;
    Menu::with_items(app, &[&settings, &quit])
}

// Handle tray events
fn handle_tray_event(app: &AppHandle, event: TrayIconEvent) {
    match event {
        TrayIconEvent::Click {
            button: MouseButton::Left,
            button_state: MouseButtonState::Up,
            ..
        } => {
            // Show/hide settings window
            if let Some(window) = app.get_webview_window("main") {
                let _ = if window.is_visible().unwrap_or(false) {
                    window.hide()
                } else {
                    window.show().and_then(|_| window.set_focus())
                };
            }
        }
        TrayIconEvent::Click {
            button: MouseButton::Right,
            button_state: MouseButtonState::Up,
            ..
        } => {
            // Right-click shows the tray menu automatically
            log::info!("Right-click menu");
        }
        _ => {}
    }
}

// Handle menu item clicks
fn handle_menu_event(app: &AppHandle, event: tauri::menu::MenuEvent) {
    match event.id.as_ref() {
        "settings" => {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show().and_then(|_| window.set_focus());
            }
        }
        "quit" => {
            log::info!("Quitting application");
            app.exit(0);
        }
        _ => {}
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app_state = AppState::default();

    tauri::Builder::default()
        .setup(|app| {
            use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, GlobalShortcutExt};
            use tauri::WebviewWindowBuilder;
            
            // Setup logging
            app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .level(log::LevelFilter::Info)
                    .build(),
            )?;

            log::info!("🚀 Whisper4Windows starting...");

            // Create recording window (hidden initially)
            let recording_window = WebviewWindowBuilder::new(
                app,
                "recording",
                tauri::WebviewUrl::App("recording.html".into())
            )
            .title("Recording...")
            .inner_size(600.0, 180.0)
            .resizable(false)
            .center()
            .always_on_top(true)
            .visible(false)
            .skip_taskbar(false)
            .decorations(false)
            .transparent(true)
            .focused(false)
            .build()?;
            
            log::info!("✅ Recording window created");

            // Create and setup tray icon
            let menu = create_tray_menu(app.handle())?;
            let tray = TrayIconBuilder::new()
                .menu(&menu)
                .icon(app.default_window_icon().unwrap().clone())
                .on_menu_event(|app, event| handle_menu_event(app, event))
                .build(app)?;
            
            // Setup tray icon event handler
            let app_handle = app.handle().clone();
            tray.on_tray_icon_event(move |_tray, event| {
                handle_tray_event(&app_handle, event);
            });

            // Register global hotkey: Alt+X
            let shortcut = Shortcut::new(Some(Modifiers::ALT), Code::KeyX);
            
            let app_handle_hotkey = app.handle().clone();
            app.handle().plugin(
                tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |_app, shortcut, _event| {
                        log::info!("🔥 Global hotkey triggered: {:?}", shortcut);
                        let app_clone = app_handle_hotkey.clone();
                        tauri::async_runtime::spawn(async move {
                            if let Err(e) = toggle_hotkey_recording(app_clone.clone(), app_clone.state()).await {
                                log::error!("Hotkey error: {}", e);
                            }
                        });
                    })
                    .build()
            )?;

            app.global_shortcut().register(shortcut)?;
            
            log::info!("✅ System tray initialized");
            log::info!("✅ Global hotkey registered: Alt+X");
            log::info!("💡 Left-click tray icon to open settings");
            log::info!("💡 Press Alt+X to start/stop recording anywhere");

            Ok(())
        })
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            toggle_recording,
            get_demo_text,
            set_demo_text,
            inject_demo_text,
            inject_text_directly,
            toggle_hotkey_recording,
            reset_recording_state,
            set_model_and_device
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}