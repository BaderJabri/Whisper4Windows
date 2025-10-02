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
        OpenClipboard, CloseClipboard, EmptyClipboard, SetClipboardData,
    },
    System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE},
    Foundation::HWND,
};
use tokio::sync::Mutex;
use anyhow::Result;

// Simple state - just track model and device
#[derive(Debug, Clone)]
pub struct AppState {
    pub selected_model: Arc<Mutex<String>>,
    pub selected_device: Arc<Mutex<String>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            selected_model: Arc::new(Mutex::new("small".to_string())),
            selected_device: Arc::new(Mutex::new("auto".to_string())),
        }
    }
}

// Text injection via clipboard
pub fn inject_text(text: &str) -> Result<()> {
    unsafe {
        let mut text_utf16: Vec<u16> = text.encode_utf16().collect();
        text_utf16.push(0);

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

        std::ptr::copy_nonoverlapping(
            text_utf16.as_ptr(),
            locked as *mut u16,
            text_utf16.len()
        );

        let _ = GlobalUnlock(hmem);

        const CF_UNICODETEXT: u32 = 13;
        let result = SetClipboardData(CF_UNICODETEXT, windows::Win32::Foundation::HANDLE(hmem.0 as _));
        if let Err(e) = result {
            let _ = CloseClipboard();
            return Err(anyhow::anyhow!("Failed to set clipboard data: {}", e));
        }

        let _ = CloseClipboard();

        std::thread::sleep(std::time::Duration::from_millis(10));

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
    }

    Ok(())
}

// Simple command: Inject text
#[tauri::command]
async fn inject_text_directly(text: String) -> Result<(), String> {
    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
    inject_text(&text).map_err(|e| e.to_string())?;
    log::info!("✅ Injected: {}", text);
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

    // Show window
    if let Some(win) = app.get_webview_window("recording") {
        win.show().map_err(|e| e.to_string())?;
        log::info!("✅ Window shown");
    }

    // Call backend /start
    let client = reqwest::Client::new();
    tokio::spawn(async move {
        match client.post("http://127.0.0.1:8000/start")
            .json(&serde_json::json!({
                "model_size": model,
                "language": "en",
                "device": device
            }))
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

// Simple command: Stop recording (called by F9 when window visible)
#[tauri::command]
async fn cmd_stop_recording(app: AppHandle) -> Result<(), String> {
    log::info!("═══════════════════════════════════════════════");
    log::info!("🛑 STOP RECORDING");
    log::info!("═══════════════════════════════════════════════");

    // Call backend /stop to get transcription
    let client = reqwest::Client::new();
    match client.post("http://127.0.0.1:8000/stop")
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            log::info!("✅ Backend stopped");

            // Get transcription text
            if let Ok(data) = resp.json::<serde_json::Value>().await {
                if let Some(text) = data.get("text").and_then(|t| t.as_str()) {
                    log::info!("📝 Transcription: {}", text);

                    // Inject text
                    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
                    if let Err(e) = inject_text(text) {
                        log::error!("❌ Injection failed: {}", e);
                    } else {
                        log::info!("✅ Text injected");
                    }
                }
            }
        }
        Ok(resp) => log::error!("❌ Backend error: {}", resp.status()),
        Err(e) => log::error!("❌ Request failed: {}", e),
    }

    // Hide window
    if let Some(win) = app.get_webview_window("recording") {
        win.hide().map_err(|e| e.to_string())?;
        log::info!("✅ Window hidden");
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
            cmd_stop_recording(app).await?;
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
        "quit" => app.exit(0),
        _ => {}
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            use tauri_plugin_global_shortcut::{Code, Shortcut, GlobalShortcutExt};
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

            // Create recording window
            WebviewWindowBuilder::new(app, "recording", tauri::WebviewUrl::App("recording.html".into()))
                .title("Recording")
                .inner_size(640.0, 200.0)
                .resizable(false)
                .center()
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

            // F9 shortcut
            let shortcut = Shortcut::new(None, Code::F9);
            let app_handle_hotkey = app.handle().clone();

            app.handle().plugin(
                tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |_app, _shortcut, event| {
                        use tauri_plugin_global_shortcut::ShortcutState;
                        // Only trigger on key press, not release
                        if event.state == ShortcutState::Pressed {
                            log::info!("🔥 F9 TRIGGERED");
                            let app_clone = app_handle_hotkey.clone();
                            tauri::async_runtime::spawn(async move {
                                let _ = cmd_toggle_recording(app_clone.clone(), app_clone.state()).await;
                            });
                        }
                    })
                    .build()
            )?;

            if let Err(e) = app.global_shortcut().register(shortcut) {
                log::error!("❌ Failed to register F9: {}", e);
            } else {
                log::info!("✅ F9 shortcut registered");
            }

            log::info!("💡 Press F9 to start/stop recording");
            Ok(())
        })
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![
            inject_text_directly,
            cmd_start_recording,
            cmd_stop_recording,
            cmd_toggle_recording,
            set_model_and_device
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
