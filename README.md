# IronGlass Production Finder

[Open de website](https://tvlmedia.github.io/ironglass-tool/) · [Bekijk de scanner](https://github.com/tvlmedia/ironglass-tool/actions/workflows/discover.yml)

Automatische ontdekking van expliciete IronGlass-vermeldingen op **door zoekmachines geïndexeerde IMDb-titelpagina’s**. Dit is geen volledige IMDb-scan.

## Automatische zoekrondes

GitHub Actions draait elke 6 uur (UTC: 00:23, 06:23, 12:23 en 18:23; starttijd kan afwijken), na een push en op aanvraag via **Actions → Discover and publish → Run workflow**.

Elke ronde doorloopt 12 algemene zoekopdrachten en 8 wisselende opdrachten voor productietypes en jaartallen. De inventaris omvat IronGlass, Iron Glass en Iron-Glass, technische specificaties, bedrijfscredits, volledige credits, shorts, muziekvideo's, tv en jaren vanaf 1990 tot en met volgend jaar. De wisselende opdrachten worden met een opgeslagen cursor over opeenvolgende rondes verdeeld. Dit is een zoekstrategie, geen claim over volledige dekking.

Zonder sleutel probeert de scanner eerst openbare Brave-webresultaten, met DuckDuckGo HTML en Bing RSS als terugval wanneer geen merkvermeldingen worden gevonden. Deze openbare zoekinterfaces kunnen blokkeren, veranderen of ongerelateerde resultaten retourneren. De scanner omzeilt geen CAPTCHA's en bezoekt geen IMDb-pagina's automatisch. Bestaande records blijven behouden als zoekbronnen falen. `scan-status.json` bevat de echte uitkomst en fouten, ook als er geen nieuwe titels gevonden zijn.

Voor een ondersteunde zoek-API: voeg een repositorysecret **BRAVE_SEARCH_API_KEY** toe onder Settings → Secrets and variables → Actions. De scanner gebruikt dan de officiële Brave API in plaats van de gratis interfaces, met maximaal twee resultaatpagina's per zoekopdracht (40 requests per ronde). Controleer zelf je abonnement/quota. Zet geen sleutel in de broncode, browser of gepubliceerde JSON. Zonder secret gebruikt de tool geen betaald zoekabonnement.

Nieuwe resultaten krijgen **Kandidaat**. Een match vereist een IMDb-titellink en een expliciete IronGlass-vermelding in het zoekfragment. Dubbelen worden op IMDb-ID samengevoegd. Verwijzingen naar nieuws en lijsten worden niet automatisch aan een productie toegeschreven. Een bedrijfscredit bewijst geen lensgebruik; technische specificaties en credits worden apart aangeduid. Helios, Mir en Jupiter alleen gelden niet als merkbewijs.

De vier startrecords zijn op 12 november 2026 gevonden in geïndexeerde IMDb-technische specificaties. “Bron bekeken” betekent dat die vermelding is bekeken, niet dat de productie het lensgebruik onafhankelijk heeft bevestigd.

## Website en opslag

GitHub Pages wordt door dezelfde workflow gepubliceerd. Alleen `index.html`, `static/`, `results.json`, `scan-status.json` en `.nojekyll` worden in de website-artifact opgenomen. Automatisch gevonden titels en het scanrapport staan ook in Git. Een Actions-botcommit start geen nieuwe Actions-run; de huidige run publiceert zijn eigen resultaten.

De website biedt titel/type/statusfilters, bronlinks, de laatste zoeklog en CSV-export. Handmatige toevoegingen blijven uitsluitend in de eigen browser en worden niet gedeeld tussen bezoekers; exporteer CSV voor een back-up. “Scanner openen” opent GitHub Actions; een repositorybeheerder kan daar een ronde starten. Bezoekers krijgen geen schrijfrechten of toegang tot secrets.

## Lokaal starten

Python 3.11+, zonder Python-packages:

```sh
python3 app.py
```

Open http://127.0.0.1:8765. Stop met Ctrl+C. Lokale resultaten staan in `results.json`.

Dezelfde uitgebreide scanner los uitvoeren:

```sh
python3 scripts/discover.py
```

De lokale knop gebruikt de oorspronkelijke kleine zoekronde; de uitgebreide achtergrondscanner gebruikt `scripts/discover.py`. De online scannerstatus betreft uitsluitend GitHub Actions.

## Controle

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

Tests controleren bronvalidatie, merkdetectie, broncategorie, dubbelen en het behoud van resultaten bij blokkades. Een technisch geslaagde Actions-run kan een scan met geblokkeerde zoekbronnen publiceren: bekijk altijd de inhoudelijke scanstatus.
