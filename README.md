# In Sala — Film stasera in TV (Sky + chiaro)

App mobile (pagina HTML statica) che mostra tutti i film in onda oggi su 44 canali italiani — pacchetti Sky Cinema e TV in chiaro — con filtri per fonte, fascia oraria, genere e ricerca testo su titolo/trama. Si aggiorna da sola ogni mattina.

## Come funziona

- `scrape.py` scarica i palinsesti del giorno da **guidatv.org** (una richiesta per canale) ed estrae orario, titolo, anno, durata, genere, voto, locandina e trama. Per i film, se è configurata una chiave **TMDB**, sostituisce la trama breve con la trama completa in italiano (con fallback alla trama breve se TMDB non trova corrispondenza).
- Il risultato finisce in `data/palinsesto.json`.
- `index.html` legge quel JSON e mostra l'interfaccia. Nessun backend: è tutto statico, adatto a GitHub Pages.
- Un workflow GitHub Actions (`.github/workflows/update.yml`) rilancia lo scraper ogni giorno alle 06:10 italiane e fa il commit del JSON aggiornato.

## Setup (una volta sola)

1. **Crea un repo nuovo** su GitHub (es. `in-sala`) e carica questi file.

2. **Chiave TMDB (per le trame complete)** — gratuita:
   - registrati su https://www.themoviedb.org e verifica la mail
   - vai in *Impostazioni → API* e richiedi una chiave **Developer** (uso personale, non commerciale)
   - copia la *API Key (v3 auth)*
   - nel repo: *Settings → Secrets and variables → Actions → New repository secret*
     - Name: `TMDB_API_KEY`
     - Secret: la chiave copiata
   - Senza questa chiave l'app funziona lo stesso, ma con le trame brevi (~100 caratteri) di guidatv.org.

3. **Attiva GitHub Pages**: *Settings → Pages → Source: Deploy from a branch → branch `main` / root*. L'app sarà su `https://<tuo-utente>.github.io/in-sala/`.

4. **Primo popolamento dati**: vai nel tab *Actions → Aggiorna palinsesto → Run workflow*. Genera subito `data/palinsesto.json`. Da lì in poi parte da solo ogni mattina.

## Cambiare i canali

La lista è in cima a `scrape.py` (`CHANNELS`): tuple `(etichetta, gruppo, slug)` dove `gruppo` è `"sky"` o `"chiaro"`. Gli slug sono quelli di guidatv.org (es. `cine-34`, `rai-1`). Per trovarne altri: la lista completa dei canali del sito è in `https://guidatv.org/channel-sitemap.xml`.

## Limiti e fragilità (da sapere)

- **Scraping = fragile per natura.** Se guidatv.org cambia struttura HTML, il parser va aggiornato. Lo scraper salta i canali che danno errore invece di bloccarsi, così un singolo canale rotto non ferma tutto.
- **Trame complete via TMDB**: il match è per titolo+anno. I titoli TV italiani non sempre coincidono con quelli TMDB, quindi una parte dei film resta con la trama breve. Non è un bug: è il limite del matching automatico.
- **Solo film**: l'app filtra per genere e mostra i Film di default. I canali per bambini (cartoni) e le serie restano disponibili tramite i filtri genere, ma non sono l'obiettivo.
- **Fuso orario**: la classificazione prima/seconda serata usa gli orari del sito (ora italiana).
- **Nessun dato sensibile**: l'app non raccoglie nulla, non ha login, non salva niente sul dispositivo. L'unico segreto è la chiave TMDB, che resta nei secret di GitHub e non finisce mai nel codice pubblico.

## File

```
index.html                      app (frontend)
scrape.py                       scraper + arricchimento TMDB
requirements.txt                dipendenze python
data/palinsesto.json            dati generati (commit automatico)
.github/workflows/update.yml    cron giornaliero
```
