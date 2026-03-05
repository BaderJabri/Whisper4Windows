# Whisper4Windows — Istruzioni per Claude Code

## Progetto
Whisper4Windows e' un'app desktop per trascrizione vocale locale basata su OpenAI Whisper.
- **Frontend**: Tauri 2 (Rust) + WebView (HTML/JS compilato in `frontend/dist/`)
- **Backend**: Python FastAPI + Uvicorn, eseguito come sidecar (`whisper-backend.exe` via PyInstaller)
- **Motore**: faster-whisper (ctranslate2) per la trascrizione
- **Comunicazione**: HTTP REST su `127.0.0.1:8000`

## Architettura
```
Tauri App (Rust, lib.rs)
  ├── WebView principale (frontend/dist/index.html) — impostazioni
  ├── WebView recording (frontend/dist/recording.html) — UI registrazione
  ├── Tray Icon — menu contestuale
  └── whisper-backend.exe (processo figlio Python)
       └── FastAPI Server (:8000)
            ├── AudioCapture (sounddevice) — registrazione audio
            ├── WhisperEngine (faster-whisper) — trascrizione
            └── GPUManager — rilevamento GPU
```

## File principali
- `frontend/src-tauri/src/lib.rs` — logica Rust, gestione processo backend, comandi Tauri
- `frontend/src-tauri/src/main.rs` — entry point (chiama `lib.rs`)
- `backend/main.py` — server FastAPI, endpoint REST
- `backend/audio_capture.py` — cattura audio con sounddevice
- `backend/whisper_engine.py` — caricamento modelli e trascrizione
- `backend/gpu_manager.py` — rilevamento GPU NVIDIA
- `frontend/dist/index.html` — UI impostazioni (HTML/JS compilato)
- `frontend/dist/recording.html` — UI registrazione (HTML/JS compilato)

## Protocollo di lavoro a sessioni

Ogni sessione di lavoro DEVE seguire questo protocollo:

### 1. Identificazione
All'inizio della sessione, leggere `ROADMAP.md` per capire quale blocco sviluppare.

### 2. Sviluppo
Implementare tutti i task del blocco corrente. Lavorare in modo incrementale.

### 3. Test
Verificare che le modifiche funzionino:
- Controllo sintassi Python: `python -c "import py_compile; py_compile.compile('file.py', doraise=True)"`
- Controllo compilazione Rust: `cd frontend/src-tauri && cargo check`
- Test funzionale se possibile

### 4. Sintesi
Alla fine della sessione, fornire all'utente:
- Riassunto chiaro e comprensibile di cosa e' stato fatto
- Eventuali problemi riscontrati
- Stato della roadmap (cosa resta da fare)

### 5. Prompt per la sessione successiva
Scrivere un prompt pronto all'uso per avviare la sessione successiva, nel formato:

```
Whisper4Windows — ROADMAP Blocco N — [descrizione del task]

[Contesto e istruzioni specifiche per il blocco]
```

### 6. Chiusura sessione
Se i test hanno esito positivo:
- Aggiornare i checkbox del blocco completato in `ROADMAP.md` (da `[ ]` a `[x]`)
- Eseguire il commit delle modifiche

## Regole generali
- Non modificare file che non servono al blocco corrente
- Ogni blocco va su un branch separato (indicato nella roadmap)
- Scrivere in italiano quando si comunica con l'utente
- I commenti nel codice restano in inglese
