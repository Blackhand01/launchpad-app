Perfetto. Qui hai una **batteria di test seria (YC-style)**: 10 idee famose descritte **come se fossero al giorno 0**, senza spoiler di successo.

👉 L’obiettivo: vedere se il tuo validator distingue davvero tra

* idee **costruibili subito**
* idee **dipendenti da infrastrutture / accordi**
* idee **veloci da validare vs lente**

---

# 🧪 COME USARLE

* Prendi UNA idea alla volta
* Incollala come `raw input`
* Guarda:

  * feasibility_score
  * yc_verdict
* Confronta con il **“Expected Verdict”** sotto

---

# 🧠 BATTERIA DI TEST (10 IDEE)

---

## 1. Facebook (2004)

```text
Una piattaforma online per studenti universitari dove creare un profilo personale, aggiungere amici e vedere cosa fanno gli altri. Inizialmente limitata a una singola università, con espansione graduale ad altri campus.
```

**Expected:**

* Vision: medio-alta
* Feasibility: alta
* Verdict: BUILD

👉 Nessuna dipendenza esterna. Solo codice + utenti.

---

## 2. Airbnb (2008)

```text
Un sito dove persone possono affittare un letto o una stanza a sconosciuti per brevi periodi, inizialmente durante eventi quando gli hotel sono pieni.
```

([Charisol][1])

**Expected:**

* Vision: alta
* Feasibility: alta
* Verdict: BUILD

👉 Non serve infrastruttura → puoi iniziare subito.

---

## 3. Uber (2009)

```text
Un’app che permette di chiamare un’auto con autista tramite smartphone e pagare automaticamente senza contanti.
```

**Expected:**

* Vision: molto alta
* Feasibility: media-alta
* Verdict: BUILD

👉 Non serve accordo con città per partire (all’inizio illegale → ma costruibile).

---

## 4. Stripe (2010)

```text
Un sistema per accettare pagamenti online facilmente tramite API, eliminando la complessità delle banche e dei gateway tradizionali.
```

**Expected:**

* Vision: molto alta
* Feasibility: media
* Verdict: BUILD

👉 Hard tech, ma controllabile.

---

## 5. Dropbox (2007)

```text
Un software che sincronizza automaticamente file tra computer e cloud, rendendoli accessibili ovunque senza chiavette USB.
```

([Charisol][1])

**Expected:**

* Vision: alta
* Feasibility: alta
* Verdict: BUILD

👉 Perfetto esempio YC: demo semplice → valore immediato.

---

## 6. Reddit (2005)

```text
Un sito dove gli utenti possono condividere link e contenuti e votare quelli migliori, creando una homepage dinamica di internet.
```

([Wikipedia][2])

**Expected:**

* Vision: media
* Feasibility: altissima
* Verdict: BUILD

👉 Infatti inizialmente fake users.

---

## 7. Slack (prima del pivot)

```text
Un videogioco online multiplayer con mondo persistente e interazioni sociali tra utenti.
```

([Founder Playbooks][3])

**Expected:**

* Vision: media
* Feasibility: bassa
* Verdict: NOT NOW / ITERATE

👉 Giusto bocciarla → infatti pivot.

---

## 8. Figma (inizio)

```text
Uno strumento di design collaborativo completamente nel browser che permette a più persone di lavorare contemporaneamente sugli stessi file.
```

([Wikipedia][4])

**Expected:**

* Vision: alta
* Feasibility: media
* Verdict: BUILD

👉 Hard ma controllabile → corretto.

---

## 9. Skipass digitale universale (la tua idea)

```text
Un’app che sostituisce completamente lo skipass fisico permettendo di accedere agli impianti sciistici tramite smartphone senza tessere.
```

**Expected:**

* Vision: medio-alta
* Feasibility: bassa
* Verdict: NOT NOW

👉 Dipendenza totale da infrastruttura.

---

## 10. Mountain Truth Engine (la tua migliore idea)

```text
Un’app che aggrega dati da webcam, meteo e GPS per stimare probabilisticamente la qualità della giornata sugli sci (neve, code, sole) con un confidence score.
```

**Expected:**

* Vision: alta
* Feasibility: alta
* Verdict: BUILD

👉 Nessuna dipendenza → perfetto YC.

---

# 🔬 TEST BONUS (IMPORTANTISSIMO)

## 11. “Idea sbagliata ma affascinante”

```text
Un’app che usa satelliti e AI avanzata per prevedere esattamente quando e dove nevicherà in ogni pista con precisione al metro.
```

**Expected:**

* Vision: altissima
* Feasibility: molto bassa
* Verdict: NOT NOW

👉 Qui testi il “bullshit detector”

---

# 📊 COME VALIDARE IL TUO VALIDATOR

Dopo aver testato:

### Se funziona bene, vedrai:

| Tipo idea                 | Output corretto |
| ------------------------- | --------------- |
| Software puro             | BUILD           |
| Marketplace semplice      | BUILD           |
| Infra-heavy               | NOT NOW         |
| Deep tech non accessibile | NOT NOW         |
| Hard ma controllabile     | BUILD           |

---

# 🚨 RED FLAGS del tuo validator

Se succede questo → è ancora rotto:

* Skipass → BUILD ❌
* Satellite AI → BUILD ❌
* Facebook → NOT NOW ❌
* Slack (gioco) → BUILD ❌

---

# 🧠 Insight finale (il più importante)

Questa batteria testa una cosa sola:

> Il tuo sistema distingue tra
> **“idea che può diventare grande”**
> vs
> **“idea che puoi iniziare domani”**

YC investe solo nella seconda.

---

# Se vuoi il livello successivo

Posso:

* trasformare questi test in **suite automatica (pytest + scoring)**
* oppure farti una **classifica delle tue idee personali** con questo sistema

Questo è esattamente il tipo di strumento che separa chi pensa da chi costruisce.

---

# ⚙️ Esecuzione automatica (pytest)

Da root progetto:

```bash
pip install -r requirements.txt
pytest -s tests/test_validator_battery.py
```

Opzioni utili:

```bash
# Esegue solo i primi 3 casi
VALIDATOR_BATTERY_LIMIT=3 pytest -s tests/test_validator_battery.py

# Modalità strict: fallisce il test se expected != predicted
VALIDATOR_BATTERY_STRICT=1 pytest -s tests/test_validator_battery.py
```

Note:

* richiede `OPENAI_API_KEY` nel tuo `.env`
* usa il validator reale (`run_feasibility_validation`) e stampa tabella risultati

[1]: https://charisol.io/10-famous-companies-that-came-out-of-y-combinator/?utm_source=chatgpt.com "10 Famous Companies That Came Out of Y Combinator - Charisol | End to End Product Development Services"
[2]: https://en.wikipedia.org/wiki/Reddit?utm_source=chatgpt.com "Reddit"
[3]: https://www.startuptoscaleup.com/resources/famous-startup-pivots/?utm_source=chatgpt.com "Famous Startup Pivots: Non-Linear Paths to Billion-Dollar Companies"
[4]: https://en.wikipedia.org/wiki/Dylan_Field?utm_source=chatgpt.com "Dylan Field"
