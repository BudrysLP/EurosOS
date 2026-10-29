# EurosOS — EMS – Dom: etap 2 (8 pozostałych pól METER_1)

Status: **wdrożone w kodzie, do sprawdzenia w Home Assistant**.
Zakres dotyczy tylko odczytów licznika `METER_1` całego domu, za licznikiem ENEA. Nie są to pomiary samej pompy `GEO_1`.

Przeanalizowane źródło: `home-assistant_2026-10-29T06-33-42.789Z.log`, 1659 komunikatów `[EMS_DIAG] METER_1`; każde z ośmiu pól występuje w 1659/1659 próbek.

## Nowe encje

| Nazwa encji | Klucz MQTT | Jednostka | Klasa HA | Typ | Interpretacja |
|---|---|---|---|---|---|
| EMS – Dom – Energia bierna dodatnia | `POS_REAC_POW_FL_1` | kvarh | `reactive_energy`, `total_increasing` | Zwykła | Narastający licznik w kierunku dodatnim, z licznika fizycznego. |
| EMS – Dom – Energia bierna ujemna | `REW_REAC_POW_FL_1` | kvarh | `reactive_energy`, `total_increasing` | Zwykła | Narastający licznik w kierunku ujemnym. |
| EMS – Dom – Moc L1 – odczyt techniczny | `A_ACT_POW_FL_1` | kW | `power`, `measurement` | Diagnostyczna | Dodatkowy sygnał A, **nie jest tym samym co** `A_PHA_ACT_POW_FL_1`. |
| EMS – Dom – Moc L2 – odczyt techniczny | `B_ACT_POW_FL_1` | kW | `power`, `measurement` | Diagnostyczna | Dodatkowy sygnał B, **nie jest tym samym co** `B_PHA_ACT_POW_FL_1`. |
| EMS – Dom – Moc L3 – odczyt techniczny | `C_ACT_POW_FL_1` | kW | `power`, `measurement` | Diagnostyczna | Dodatkowy sygnał C, **nie jest tym samym co** `C_PHA_ACT_POW_FL_1`. |
| EMS – Dom – Współczynnik POS – techniczny | `POS_ACT_POW_FACTOR` | brak | bez klasy i statystyk | Diagnostyczna | Surowy parametr techniczny; w przeanalizowanych logach **zawsze 1**. |
| EMS – Dom – Współczynnik REV – techniczny | `REV_ACT_POW_FACTOR` | brak | bez klasy i statystyk | Diagnostyczna | Surowy parametr techniczny; w przeanalizowanych logach **zawsze 1**. |
| EMS – Dom – Współczynnik TOTAL – techniczny | `TOTAL_ACT_POW_FACTOR` | brak | bez klasy i statystyk | Diagnostyczna | Surowy parametr techniczny; w przeanalizowanych logach **zawsze −1**. |

## Dowody z MQTT

Wszystkie osiem pól są liczbowe w 1659 próbkach:

| Klucz | Minimum | Maksimum |
|---|---:|---:|
| POS_REAC_POW_FL_1 | 165.92 | 167.13 |
| REW_REAC_POW_FL_1 | 1321.49 | 1326.47 |
| A_ACT_POW_FL_1 | -0.205 | 0.525 |
| B_ACT_POW_FL_1 | -0.280 | 0.221 |
| C_ACT_POW_FL_1 | -0.214 | 0.342 |
| POS_ACT_POW_FACTOR | 1 | 1 |
| REV_ACT_POW_FACTOR | 1 | 1 |
| TOTAL_ACT_POW_FACTOR | -1 | -1 |

Dwa liczniki energii biernej są monotonicznie rosnące w analizowanym okresie. Wartości są prezentowane w jednostce kvarh (do potwierdzenia ze specyfikacją konkretnego modelu licznika). Nie nazywamy kierunku dodatniego „indukcyjnym” ani ujemnego „pojemnościowym” bez dokumentacji urządzenia.

Dodatkowe moce A/B/C są liczbami **innymi niż odpowiednie moce fazowe** we wszystkich 1659 próbkach, więc nie wolno używać ich zamiennie z bilansami `A_PHA_ACT_POW_FL_1`, `B_PHA_ACT_POW_FL_1` i `C_PHA_ACT_POW_FL_1`.

**Trzy pola FACTOR nie są tym samym co współczynniki mocy PF:** mają ciągle 1/1/−1 i mogą być elementami wewnętrznego przeliczania lub konfiguracji. Ich dokładne znaczenie pozostaje niepotwierdzone.

## Zachowanie i bezpieczeństwo

- Wszystkie nowe encje są odczytowe; wykorzystują istniejący MQTT `/Dev` i `coordinator.ems_meters`.
- Dwa liczniki energii biernej są zwykłymi sensorami narastającymi; 6 pól pomocniczych ma kategorię `diagnostic`.
- Brak lub zła wartość skutkuje stanem niedostępnym, nigdy sztucznym zerem.
- Zachowane `unique_id` wszystkich 27 istniejących encji EMS, urządzenie `EMS – Dom` oraz 46 historycznych wpisów `GEO_1`.
- Docelowy wykaz po ponownym uruchomieniu integracji: **35 encji EMS – Dom** (33 bezpośrednie + 2 dzienne), **81 łącznie** (46 GEO + 35 EMS), **2 urządzenia**.
- Liczniki dzienne nadal wymagają końcowego testu przejścia przez północ i zachowania wartości po restarcie HA.
- Zielony status w inwentaryzacji dopiero po potwierdzeniu rzeczywistych wartości nowych encji na ekranie HA.

Porównanie klas sensorów z aktualnymi definicjami HA: https://developers.home-assistant.io/docs/core/entity/sensor/

Źródła implementacji: `custom_components/euros_os/ems.py`, `sensor.py`, `tests/test_ems.py` na gałęzi `feature/geo-support`.
