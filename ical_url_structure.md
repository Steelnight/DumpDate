# API-Dokumentation: Prozess zum Abrufen von Abfallkalendern für Dresden

Dieser Bericht dokumentiert den vollständigen Prozess, um für eine gegebene Adresse in Dresden eine iCal-Kalenderdatei mit den Abfuhrterminen zu generieren.

Der Prozess ist zweistufig:
1.  **Ermittlung der Standort-ID:** Zuerst muss die eindeutige ID des Standorts (Adresse) über eine OGC-API (Adress-API) ermittelt werden.
2.  **Generierung der iCal-URL:** Anschließend wird die ermittelte Standort-ID verwendet, um die URL für den iCal-Download zusammenzusetzen.

---

## Schritt 1: Ermittlung der Standort-ID (`STANDORT`)

Die Standort-ID (`STANDORT` in der iCal-URL) entspricht der Adressnummer (`adr_nr` oder `id`) aus der öffentlichen Adress-API der Stadt Dresden.

### Adress-API Endpunkt

```
https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items
```

### Methode

`GET`

### Adressabfrage

Um die ID für eine bestimmte Adresse zu finden, muss eine Anfrage an den Endpunkt gesendet werden. Die API unterstützt anscheinend keine serverseitige Filterung über URL-Parameter. Daher muss die vollständige Liste aller Adressen abgerufen und clientseitig durchsucht werden.

**Beispiel:** Um die ID für "Chemnitzer Straße 42" zu finden, kann die gesamte GeoJSON-Antwort durchsucht werden.

```bash
# Lädt alle Adressen herunter und filtert sie mit grep nach der gewünschten Adresse.
# Das Ergebnis ist der JSON-Block für die spezifische Adresse.
curl -s "https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items?limit=100000" | grep -A 5 "Chemnitzer Straße 42"
```

### Ergebnis der Abfrage

Die Abfrage liefert ein GeoJSON `Feature`-Objekt. Die benötigte ID befindet sich im `id`-Feld des Objekts.

**Beispiel-Antwort für "Chemnitzer Straße 42":**
```json
{
  "type": "Feature",
  "geometry": { ... },
  "id": 54367,
  "properties": {
    "adresse": "Chemnitzer Straße 42",
    "str_id": "01201",
    "strasse": "Chemnitzer Straße",
    ...
  }
}
```
Die `STANDORT`-ID für "Chemnitzer Straße 42" ist also **`54367`**.

---

## Schritt 2: Generierung der iCal-URL

Sobald die `STANDORT`-ID bekannt ist, kann die URL für den iCal-Download zusammengesetzt werden.

### iCal-Endpunkt-URL

```
https://stadtplan.dresden.de/project/cardo3Apps/IDU_DDStadtplan/abfall/ical.ashx
```

### Methode

`GET`

### Parameter

| Parameter   | Typ      | Beschreibung                                                                     | Beispielwert      | Erforderlich |
|-------------|----------|----------------------------------------------------------------------------------|-------------------|--------------|
| `STANDORT`  | Integer  | Die eindeutige Standort-ID, die in Schritt 1 ermittelt wurde.                    | `54367`           | Ja           |
| `DATUM_VON` | String   | Das Startdatum für den Export im Format `TT.MM.JJJJ`.                            | `01.01.2026`      | Ja           |
| `DATUM_BIS` | String   | Das Enddatum für den Export im Format `TT.MM.JJJJ`.                              | `31.12.2026`      | Ja           |
| `DUMMY`     | Integer  | Ein optionaler Cache-Buster-Parameter. Kann weggelassen werden.                  | `638966468141001060` | Nein         |

### Vollständiges Beispiel

1.  **Adresse:** `Chemnitzer Straße 42`
2.  **Gewünschter Zeitraum:** `01.01.2026` bis `31.12.2026`

**Prozess:**
1.  Durch Abfrage der Adress-API wird die `STANDORT`-ID `54367` ermittelt.
2.  Die iCal-URL wird zusammengesetzt:
    ```
    https://stadtplan.dresden.de/project/cardo3Apps/IDU_DDStadtplan/abfall/ical.ashx?STANDORT=54367&DATUM_VON=01.01.2026&DATUM_BIS=31.12.2026
    ```
Diese URL liefert die gewünschte iCal-Datei mit den Abfuhrterminen für den angegebenen Standort und Zeitraum.
