# EurosOS / Euros GEO 06 SH — P1: stan pracy (STATE)

**Status kodu: WDROŻONY w `feature/geo-support` 29 października 2026.**  
**Status urządzenia HA: do potwierdzenia po wgraniu `sensor.py` i restarcie.**

## Problem

W starym `sensor.py` brakujące flagi `SBF_*`, `SBB_*` i `SXF_*` były zastępowane domyślną wartością `0`. Mogło to tworzyć fałszywy stan `IDLE`, mimo braku wiarygodnych danych.

W `geo.py` istniała już funkcja `calculate_geo_operating_state` i jej testy, lecz nie była wywoływana przez encję HA `STATE`.

## Rozwiązanie

- `sensor.py` przekazuje `device_type` do `EurosOSSensor`.
- Dla `FriskoGEO` encja `STATE` wywołuje `calculate_geo_operating_state(data)`.
- Dla innych urządzeń zachowana poprzednia analiza (bez zmian).
- Wymagane są **wszystkie siedem flag**: `SBF_DHS`, `SBF_DHX`, `SBF_OOF`, `SBB_QHW`, `SXF_TOE`, `SBB_QHT`, `SBB_QHL`.
- Za poprawne uznawane są wyłącznie rzeczywiste wartości `0` i `1` (liczby całkowite lub napisy); nie przyjmujemy wartości brakujących, pustych i błędnych.
- Wyniki: `CWU`, `CO`, `IDLE`, `OFF`, a przy braku wiarygodnych danych `None` / HA: `unknown`.
- Priorytet `CWU` przed `CO` pozostał zgodny z wcześniejszą implementacją.
- Jeśli `SBF_OOF=0` i komplet innych flag jest prawidłowy, stan to `OFF`, nie `IDLE`.
- `STATE` zachowuje `unique_id` `{unique_prefix}_state`; nie tworzymy nowej encji ani nie kasujemy historii.
- Brak zmian w MQTT, sterowaniu, 35 encjach EMS, pozostałych encjach GEO i ośmiu historycznie niedostępnych wpisach.

## Dowód z logów

W pliku `home-assistant_2026-10-27T14-21-38.081Z.log` znaleziono **357** zapisanych pakietów `Received MQTT payload` urządzenia `GEO_1`. W 357/357 obecne były wszystkie wymagane flagi, każdorazowo w układzie:
`SBF_DHS=1`, `SBF_DHX=1`, `SBF_OOF=1`, `SBB_QHW=0`, `SXF_TOE=1`, `SBB_QHT=0`, `SBB_QHL=0`; wynik `IDLE`.

**Ograniczenie dowodowe:** ten fragment logu nie obejmuje przełączeń do `CO`, `CWU` ani `OFF`. Poprawność tych stanów została sprawdzona testami jednostkowymi funkcji na reprezentatywnych flagach, lecz należy jeszcze potwierdzić ich zachowanie podczas rzeczywistej pracy pompy w HA.

## Kontrola P1

1. Pięć niewiarygodnych encji `ZM_AC_IN_VOL`, `ZM_AC_IN_CUR`, `ZM_AC_IN_PWR`, `ZM_AC_IN_ENERGY`, `ZM_SUCT_TEMP` — wyłączone tylko dla `FriskoGEO` i wcześniej potwierdzone jako historycznie niedostępne w HA.
2. `STATE` — kod poprawiony, zachowany ten sam `unique_id`, do sprawdzenia po aktualizacji jednego pliku `sensor.py`.
3. Testy `tests/test_geo.py` obejmują komplet flag, brakujące/błędne dane, wartości `OFF`, `CWU`, `CO`, `IDLE` oraz test powiązania funkcji z `sensor.py`.

**P1 — implementacja gotowa; zamknięcie w HA wymaga potwierdzenia zachowania stanu po aktualizacji.**
