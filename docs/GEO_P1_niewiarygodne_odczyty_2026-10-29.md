# GEO_1 — P1: wiarygodność pomiarów i stanu pracy (29.10.2026)

## Zakres i źródła

Weryfikacja danych z 357 komunikatów MQTT `GEO_1` w logu `home-assistant_2026-10-27T14-21-38.081Z.log`, porównanych z `sensor.py`, `geo.py` i mapą sterownika `FriskoGEO`.

W tym krótkim fragmencie wszystkie 7 flag wyznaczających `STATE` występowało w 357/357 komunikatach. Pięć poniższych kluczy pomiarowych **nie występowało ani razu** (0/357).

Nie modyfikujemy sterownika pompy ani odczytów licznika całego domu `METER_1`.

## P1: pięć istniejących encji GEO niepotwierdzonych pomiarem

| Klucz / encja | Ustalenie | Efekt w HA |
|---|---|---|
| `ZM_AC_IN_VOL` — Napięcie wejściowe | Brak potwierdzonego pomiaru napięcia GEO | Niedostępny |
| `ZM_AC_IN_CUR` — Prąd wejściowy | Brak potwierdzonego pomiaru prądu GEO | Niedostępny |
| `ZM_AC_IN_PWR` — Aktualny pobór mocy | Poprzednio sztuczne `I × U` z domyślnymi 0 A i 230 V | Niedostępny, nie `0 W` |
| `ZM_AC_IN_ENERGY` — Energia całkowita | Poprzednio całkowanie wyliczonej mocy, resetowane po restarcie | Niedostępny, nie `0 kWh` |
| `ZM_SUCT_TEMP` — Temp. wyjściowa czynnika | Pole nieobecne; poprzednio domyślne `0°C` | Niedostępny, nie `0°C` |

Implementacja świadomie zachowuje obiekty i dotychczasowe `unique_id`, zamiast usuwać je z rejestru. Pięć wartości pozostaje niedostępnych dla raportowanego `Type=FriskoGEO`, ponieważ brak dokumentacji potwierdzającej rzeczywiste źródło pomiaru. Ewentualne wsparcie w przyszłym firmware wymaga ponownej weryfikacji źródeł danych.

Nie zastępujemy pomiarów pompy wartościami `METER_1` (ten mierzy cały dom).

## P1: istniejący sensor `STATE`

Wymagane flagi: `SBF_DHS`, `SBF_DHX`, `SBF_OOF`, `SBB_QHW`, `SXF_TOE`, `SBB_QHT`, `SBB_QHL`.

- Przy kompletnych, binarnych odczytach zachowujemy **poprzednie** priorytety i wyniki `CWU`, `CO`, `IDLE`.
- Gdy brakuje dowolnej flagi, jest pusta, `unknown` albo ma wartość różną od 0/1, `STATE` staje się niedostępny. Nie przypisujemy fałszywego `IDLE`.
- Zmiana dotyczy **wyłącznie prezentacji stanu**. Nie modyfikuje sterowania, automatyki ani poleceń MQTT.

## Modyfikowane pliki i testy

- `custom_components/euros_os/geo.py` — lista pięciu źródeł niepotwierdzonych i funkcja oceny kompletnych flag stanu.
- `custom_components/euros_os/sensor.py` — użycie funkcji i kontrola `available`.
- `tests/test_geo.py` — testy kompletnego i niepełnego zestawu flag, obsługi CWU/CO/IDLE oraz zachowania encji.
- `ems.py`, `coordinator.py`, `number.py`, `select.py`, `switch.py`, `binary_sensor.py`, `const.py` — bez zmian.

## Kontrola po ręcznej instalacji w HA

1. Z gałęzi `feature/geo-support` skopiować **dwa pliki**: `geo.py` i `sensor.py` do `/config/custom_components/euros_os/`.
2. Uruchomić ponownie Home Assistant Core.
3. Potwierdzić, że urządzenie `GEO_1` ma nadal 46 wpisów, `EMS – Dom` 35, a EurosOS ogółem 81.
4. Sprawdzić, że pięć encji GEO pokazuje **niedostępny**, zamiast `0 W`, `0 kWh` albo `0°C`.
5. Przy poprawnych danych flag `STATE` w dalszym ciągu pokazuje `IDLE`, `CWU` lub `CO` zgodnie z pracą pompy.
6. Zachować historię, nie usuwać i nie konfigurować ponownie integracji.

**Status:** wdrożone w kodzie, oczekuje na test po aktualizacji HA. Testy jednostkowe są dodane do repozytorium; nie zastępują testu w działającej instalacji.
