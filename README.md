# IronGlass Research Desk

Lokale researchtool, zonder Python-dependencies. Start in deze map:

```sh
python3 app.py
```

Open http://127.0.0.1:8765. Stop met Ctrl+C.

- Doorzoekt geïndexeerde IMDb-titelpagina's met vijf zoekopdrachten, inclusief shorts en muziekvideo's.
- Gratis standaardprovider: DuckDuckGo HTML. Deze kan verzoeken blokkeren of onvolledige resultaten teruggeven. De interface toont fouten; geen resultaten is geen bewijs van afwezigheid.
- Optioneel: stel `BRAVE_SEARCH_API_KEY` in je omgeving in voor Brave Search. De sleutel blijft op de server. De Brave-dienst kan kosten hebben volgens je abonnement.
- Handmatig IMDb-bronmateriaal toevoegen, filteren en CSV exporteren.
- Resultaten blijven lokaal in `results.json`. Maak daarvan een kopie voor een back-up.

De vier startvermeldingen werden op 12 november 2026 aangetroffen in geïndexeerde technische specificaties van IMDb. Hun status betekent dat de IMDb-vermelding is bekeken, niet dat lensgebruik onafhankelijk bij de productie is geverifieerd. Nieuw gevonden zoekresultaten krijgen de status Kandidaat; geplakte tekst krijgt Handmatig aangeleverd. Productietypes uit zoekresultaten blijven Onbekend zolang die niet zijn vastgesteld.

Er is geen garantie op een volledige filmografie: IMDb bevat vrijwillig aangeleverde gegevens en zoekmachines indexeren niet elke titel. Helios/Mir/Jupiter zonder expliciete IronGlass-vermelding worden niet als merkbewijs opgeslagen. De tool omzeilt geen IMDb-blokkades en haalt geen hele IMDb-database op.

## Online versie (GitHub Pages)

https://tvlmedia.github.io/ironglass-tool/

De repository-root bevat de Pages-startpagina; `static/` bevat gedeelde assets.
De online versie toont de startgegevens, filters, zoeklinks en CSV-export.
Handmatige toevoegingen worden uitsluitend in de browser opgeslagen en niet gedeeld tussen bezoekers. Exporteer ze voor een back-up.
Automatisch zoeken blijft een functie van de lokale Python-server: GitHub Pages biedt geen Python-backend.
