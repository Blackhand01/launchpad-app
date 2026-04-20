# Launchpad Scrub

Piccola applicazione per l'elaborazione e la pulizia di dati (launchpad). Questo repository contiene il codice server-side e alcuni script SQL per creare/ripristinare lo schema del database.

## Panoramica

Questo progetto fornisce un'app Python che espone funzionalità di elaborazione dati tramite `app.py` (interfaccia web) e funzionalità AI tramite `ai_engine.py`. La persistenza e le utility DB sono gestite in `database.py` e gli script SQL si trovano in `schema.sql` e `reset_launchpad.sql`.

## Requisiti

- Python 3.10+ (consigliato)
- virtualenv o venv
- Dipendenze Python indicate in `requirements.txt`
- Un database compatibile (vedi `database.py` per la configurazione)

## Installazione

1. Creare e attivare un ambiente virtuale:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Installare le dipendenze:

```bash
pip install -r requirements.txt
```

## Configurazione

Controlla `database.py` per sapere quali variabili d'ambiente o stringhe di connessione sono richieste. Configura la variabile di ambiente appropriata (es. `DATABASE_URL`) prima di avviare l'app.

## Inizializzare il database

Se usi PostgreSQL:

```bash
# crea il db (esempio)
createdb launchpad_db
# applica lo schema
psql -d launchpad_db -f schema.sql
```

Se usi SQLite (solo come esempio rapido):

```bash
sqlite3 launchpad.db < schema.sql
```

Per ripristinare i dati di esempio usa `reset_launchpad.sql`:

```bash
psql -d launchpad_db -f reset_launchpad.sql
```

## Avvio dell'app

L'app principale può essere avviata con Streamlit (se il front-end è basato su Streamlit) oppure come server Python a seconda di `app.py`.

Esempio con Streamlit:

```bash
source .venv/bin/activate
streamlit run app.py
```

Esempio generico con Python:

```bash
python app.py
```

Dopo l'avvio, apri il browser su `http://localhost:8501` (Streamlit) o sulla porta mostrata dal server.

## File principali

- `app.py` : entry-point dell'applicazione (interfaccia web / server)
- `ai_engine.py` : logica AI / elaborazione avanzata
- `database.py` : helper e connessione al DB
- `requirements.txt` : dipendenze Python
- `schema.sql`, `reset_launchpad.sql` : script per il DB

## Sviluppo e debugging

- Per modifiche rapide, attiva l'ambiente e avvia l'app in modalità sviluppo.
- Controlla i log nella console per errori di connessione al DB o mancanza di dipendenze.

## Scoring (Dettaglio Formule)

Le formule di valutazione sono documentate qui (non mostrate in UI):

- `dependency_penalty = dependency_score * 0.30`
- `vision_bonus = max(0, (vision_score - 55) * 0.15)`
- `real_feasibility = clamp(feasibility_score - dependency_penalty + vision_bonus, 0, 100)`
- `final_score = clamp((real_feasibility * 0.60) + (vision_score * 0.40), 0, 100)`

Dove `clamp(x, 0, 100)` limita il valore tra 0 e 100.

## Contribuire

Apri una issue o invia una pull request con le modifiche proposte. Aggiungi test e aggiorna il README per nuovi comportamenti.

## Licenza

Specifica qui la licenza del progetto (es. MIT) se applicabile.

## Contatti

Per domande contatta il manutentore del repository.
