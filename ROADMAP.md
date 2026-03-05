# Whisper4Windows — Roadmap: Backend Robusto e Auto-Recuperante

## Obiettivo
Rendere il backend Python (FastAPI/Uvicorn) solido, resistente ai crash e capace di auto-recuperarsi senza intervento manuale dell'utente.

## Stato attuale del problema
Il backend a volte va offline per crash del processo Python (OOM, errori CUDA, eccezioni non gestite). Quando succede, l'utente deve manualmente riavviarlo dalle impostazioni. Non esiste nessun meccanismo di auto-recovery.

---

## Blocco 1: Coda audio limitata e fix exception handling
**File:** `backend/audio_capture.py`, `backend/main.py`
**Branch:** `fix/bounded-audio-queue`

### Task
- [x] Aggiungere `maxsize=9600` alla `queue.Queue()` in `audio_capture.py` (~10 min di audio)
- [x] Modificare `_audio_callback` per gestire coda piena (buffer circolare: drop chunk piu' vecchio)
- [x] Fix bare `except:` in `main.py` (righe 108, 352) → `except Exception:`
- [x] Fix bare `except:` in `audio_capture.py` se presenti
- [x] Aggiungere campo `last_audio_level` aggiornato dal callback per evitare il peek/re-insert nella coda (`/audio_level`)

### Verifica
- Il backend si avvia normalmente
- La registrazione e trascrizione funzionano
- La coda non cresce oltre il limite (verificare nei log)
- L'endpoint `/audio_level` funziona senza toccare la coda principale

---

## Blocco 2: Unload modello e check VRAM
**File:** `backend/whisper_engine.py`, `backend/main.py`
**Branch:** `fix/model-memory-management`

### Task
- [ ] Aggiungere metodo `unload_model()` in `WhisperEngine` (del model, gc.collect)
- [ ] Chiamare `unload_model()` quando si cambia modello o device in `/start`
- [ ] Rimuovere il check `if self.is_loaded: return True` quando model_size/device diversi
- [ ] Aggiungere metodo `_check_vram_available()` che verifica VRAM prima del caricamento CUDA
- [ ] Se VRAM insufficiente, fallback automatico a CPU con warning nel log

### Verifica
- Cambio modello nelle impostazioni libera la memoria del precedente (verificare nei log)
- Modello grande su GPU piccola non crasha ma usa CPU
- Trascrizione funziona dopo cambio modello

---

## Blocco 3: Exception handler globale, lock stato, timeout trascrizione
**File:** `backend/main.py`
**Branch:** `fix/backend-resilience`

### Task
- [ ] Aggiungere `@app.exception_handler(Exception)` globale che logga e ritorna 500
- [ ] Aggiungere `asyncio.Lock()` per serializzare `/start`, `/stop`, `/cancel`
- [ ] Wrappare trascrizione in `asyncio.wait_for()` con timeout 300s
- [ ] Gestire `asyncio.TimeoutError` con messaggio appropriato

### Verifica
- Eccezioni non gestite non crashano il processo (ritornano 500)
- Chiamate concorrenti start/stop non corrompono lo stato
- Trascrizioni che durano troppo vengono interrotte con errore

---

## Blocco 4: Auto-restart watchdog lato Rust
**File:** `frontend/src-tauri/src/lib.rs`
**Branch:** `feat/backend-auto-restart`

### Task
- [ ] Aggiungere `is_shutting_down: Arc<Mutex<bool>>` all'`AppState`
- [ ] Creare funzione `spawn_backend_with_watchdog()` che:
  - Spawna il sidecar
  - Ascolta `_rx` per eventi `CommandEvent::Terminated`
  - Se non e' shutdown intenzionale, rilancia dopo 2s
  - Limita restart a max 5 in 60 secondi (anti-loop)
  - Logga stdout/stderr del backend
- [ ] Usare questa funzione nello startup e in `restart_backend`
- [ ] Settare `is_shutting_down = true` nel handler "quit" prima di killare

### Verifica
- Killare manualmente il processo backend (`taskkill /F /IM whisper-backend.exe`)
- Il watchdog lo rilancia automaticamente entro ~3 secondi
- Il frontend mostra brevemente "offline" poi torna "online"
- Dopo 5 crash rapidi consecutivi, il watchdog si ferma (anti-loop)
- Chiudere l'app dal tray NON triggera il restart

---

## Note
- Ogni blocco va sviluppato in una sessione separata
- Ogni sessione segue il protocollo definito in `CLAUDE.md`
- I blocchi vanno sviluppati in ordine (1 → 2 → 3 → 4)
