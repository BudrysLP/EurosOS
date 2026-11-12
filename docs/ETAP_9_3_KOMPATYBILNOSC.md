# Euros OS — ETAP 9.3: kompatybilność urządzeń, API HA i instalacji

**Data aktualizacji:** 2026-11-12. **Etap:** częściowo zakończony — **5/9** zadań formalnie zaliczonych. Brak instalacji nowego kodu w produkcyjnym HA; nie ma PR do autora.

## Repozytorium i wynik testów

- Gałąź prac: `feature/stage9-compatibility`, powstała z `feature/stage9-reliability`.
- Wersja bazowa HA użytkownika w testach z 9 listopada: Core 2026.11.0, GEO_1 oraz EMS Dom / METER_1, łącznie 73 nienaruszone identyfikatory.
- [Przebieg CI](https://github.com/BudrysLP/EurosOS/actions/runs/43201747083) po migracji sensorów: **125/125** Python 3.12.16, **125/125** Python 3.13.18, **125/125** Python 3.14.10. Są to testy automatyczne i symulacyjne; to NIE jest pełna instalacja Home Assistant Core.
- Home Assistant 2026.11 wymaga **Python >=3.14.2**: https://pypi.org/project/homeassistant/ .
- Podczas pierwszego CI `3.14.2` instalacja na `ubuntu-latest` / Ubuntu 26.04 zakończyła się błędem dostępności dokładnego patcha w `actions/setup-python`, a nie błędem integracji. Ustalono `ubuntu-24.04`, `setup-python@v6` i najnowszy patch 3.14 spełniający >=3.14.2; wynik zielony.
- Oficjalna dokumentacja SensorEntity: https://contributors.home-assistant.io/core/entities/sensor/ .
- Oficjalne reguły klasy IoT (MQTT push): https://contributors.home-assistant.io/core/integrations/manifest/ .
- Marketplace i HACS `zip_release`: https://contributors.home-assistant.io/marketplace/guides/releases/ .

## Zrealizowane punkty

| ID | Wynik | Dowody/ograniczenia |
| --- | --- | --- |
| 9.3.1 | **Wykonane (symulacje)** | `discovery.find_pump()` rozpoznaje FriskoGEO, FriskoATMO i FriskoALLINONE po typie. Nie oznacza to testów fizycznych ATMO i ALLINONE. |
| 9.3.2 | **Wykonane (symulacje)** | Kolejność `Devices` nie zmienia wyboru pompy. Dwie pompy bez jednoznacznej tożsamości są odrzucane; skonfigurowana pompa nie jest podmieniana. |
| 9.3.3 | **Wykonane (analiza + wcześniejsze testy HA)** | Istniejące `unique_id`/identyfikatory urządzeń pozostają niezmienione w kodzie; 73 `entity_id`, `unique_id` i `device_id` zweryfikowano na fizycznym HA w ETAPIE 8. Ponowna kontrola najnowszej gałęzi w HA należy do 9.5. |
| 9.3.6 | **Wykonane (symulacje)** | `METER_1`: 33 sensory + 2 liczniki dzienne, stałe ID i nazwy. `METER_N`: tworzone dopiero po realnym polu MQTT; brak fantomowych liczników. Fizyczny METER_2 nadal nieprzetestowany. |
| 9.3.7 | **Wykonane (symulacje + wcześniejszy HA)** | Testy obrotu dnia, timera północy, restore po restarcie, niepoprawnych odczytów, drobnego spadku i resetu licznika; historia energii na rzeczywistym HA przeżyła restart ETAPU 8. |

## Zmiany w gałęzi 9.3

1. `sensor.py`: starszy EurosOSSensor przeniesiony z override `state` / `unit_of_measurement` / `state_class` na `native_value`, `_attr_native_unit_of_measurement` i `_attr_state_class`. Zasady HA: `None` = unknown, `available=False` = unavailable; nie wysyłać napisu `unknown` jako odczytu temperatury. `unique_id` pozostał bez zmian.
2. Dla wartości liczbowych z `state_class` odrzucane są `NaN`, `inf`, wartości logiczne i nienumeryczne; brak napięcia lub prądu w szacowanej mocy nie jest przedstawiany jako pomiar 0 W. Dodano regresje. **Uwaga:** nadal istnieje wcześniejszy algorytm szacowania `ZM_AC_IN_ENERGY` na podstawie czasu odczytu sensora; jego semantyka wymaga osobnej analizy przed uznaniem 9.3.5.
3. `manifest.json` oraz `hacs.json`: `iot_class` zmieniono z `local_polling` na `local_push`; faktyczna telemetria dociera z brokera MQTT i powiadamia HA. Nie zmieniano wersji wydania ani sposobu instalacji.
4. CI rozbudowano o Python 3.14 na kompatybilnym runnerze.
5. Testy `test_dynamic_ems.py`, `test_mqtt_to_ha_integration.py`, `test_ha08_compat.py`, `test_manifest_preflight.py` dostosowano/rozszerzono.

## Pozostałe zadania — nie odhaczać przedwcześnie

| ID | Ryzyko / stan | Następny bezpieczny krok |
| --- | --- | --- |
| 9.3.4 | **W toku:** kod odświeżony do natywnego API, ale pełnej kontroli z prawdziwym pakietem HA Core 2026.11 (w szczególności RestoreSensor i kontrolek) nie wykonano. | Test w realnym środowisku HA API i kontrola liczby/stanów encji bez zmian identyfikatorów. |
| 9.3.5 | **W toku:** EMS ma deklaracje mocy/energii i `total_increasing`, a jednak starszy szacowany `ZM_AC_IN_ENERGY` w niesprawdzonych modelach może być zależny od liczby odczytów. | Osobny audyt/statystyki energii; nie mylić szacowania pompy z realnym `METER_1` dla całego domu; testy liczb i HA Energy. |
| 9.3.8 | **Częściowo:** Python 3.14.10 i wszystkie symulacje zielone, ale nie instalowano nowej gałęzi w prawdziwym HA Core 2026.11. | Weryfikacja uruchomienia Core/encje, jeśli podejmiemy kontrolowaną aktualizację w ETAPIE 9.5. |
| 9.3.9 | **W toku:** istniejący upstream ma archiwa `euros_os.zip` w wydaniach `v0.1.0`, `v0.1.1`, `v0.1.1-hotfix`, `v0.1.2`. `hacs.json` ma `zip_release:true`, ale fork nie ma własnych wydań; `homeassistant:2021.12.0` i metadane wersji nie odzwierciedlają zweryfikowanego zakresu. | Uzgodnić minimalną wersję HA i wymagania Marketplace, nie zmieniać `zip_release` i nie oznaczać starszych HA jako wspieranych bez testów. Test instalacji/upgrade w 9.5/9.6. |

## Otwarte blokady poza ETAPEM 9.3

**9.2.5 TLS (P1)** nadal otwarte: lokalny broker posiada samopodpisany Root CA oraz certyfikat niedopasowany do bieżącego IP pompy. Nie wprowadzać niezweryfikowanej zmiany uwierzytelniania, która odetnie urządzenie. Szczegóły: [ETAP_9_2_TLS_DIAGNOSTYKA.md](ETAP_9_2_TLS_DIAGNOSTYKA.md).

## Zasady publikacji

- Nie wdrażano najnowszej gałęzi na HA produkcyjnym.
- Nie zmieniano upstream `main` ani PR #3.
- Nie otwieramy końcowego PR przed zamknięciem bramki 9.8.
