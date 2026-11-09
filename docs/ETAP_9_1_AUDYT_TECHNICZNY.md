# Euros OS — ETAP 9.1: audyt techniczny przed końcowym PR

Data bazowa: 2026-11-09. Status: AUDYT STATYCZNY ZAKOŃCZONY; POPRAWKI JESZCZE NIEWDROŻONE.

## Zakres i punkt odniesienia

- Repozytorium: BudrysLP/EurosOS; źródło: feature/stage8-ha-preflight, commit 12d2502091d2364e7cb1803eef3bd523a31618de.
- Gałąź dokumentacyjna: feature/stage9-audit, utworzona dokładnie od powyższego commitu. W tej fazie NIE zmieniano plików działającej integracji.
- Upstream: McKoPcIu/EurosOS, main = 2f2534e952287f5f3755a23e82b9f39fa766ad64 (w chwili audytu).
- Różnica fork main...stage8: 117 commitów, 26 zmienionych/dodanych plików.
- Workflow: https://github.com/BudrysLP/EurosOS/actions/runs/42687735935 — completed/success na 3.12 i 3.13. Dotychczas 94 testy na każdą wersję.
- Real HA: 2026.11.0, GEO_1 (38 encji), EMS Dom/METER_1 (35 encji); 73 zgodne entity_id/unique_id/device_id przed i po, historia i licznik dzienny zachowane. Kontrola logów tylko w dostarczonym zakresie.
- PR #3: otwarty; PR #4: zamknięty, jego gałąź feature/upstream-geo-ems usunięta.

## Metoda

Przejrzano wszystkie 12 modułów .py, pliki manifest.json, hacs.json, en/pl tłumaczenia, README.md, MQTT_SETUP.md, dokumentację etapów i osiem plików testowych. Zweryfikowano strukturę upstream main, gałęzie, przebieg GitHub Actions oraz oficjalną dokumentację Home Assistant dotyczącą SensorEntity, dostępności encji i push updates. Wyniki mają charakter przeglądu statycznego i NIE są dowodem wystąpienia awarii w działającym HA.

## Rejestr ustaleń

| ID | Ważność | Plik / linie | Ustalenie | Co należy zweryfikować / poprawić |
| --- | --- | --- | --- | --- |
| AUD-01 | P1 | number.py 95-115; select.py 168-199; sensor.py 214-247 | Różne rozpoznawanie AUTO i EMS. Dla GEO _get_device_mode() nie sprawdza U_ENE_TAR, więc w EMS może zwracać AUTO podczas kwalifikowania zapisu nastaw. | Uzgodnić dozwolone zmiany temperatur w EMS, scentralizować interpretację trybu bez zmiany zachowania produkcyjnego bez testów. |
| AUD-02 | P1 | sensor.py 177-184, 300-312, 358-368, 423-433; coordinator.py 102-124 | Dostępność zależy od czasu ostatniego MQTT, ale brak osobnego zdarzenia wymuszającego przeliczenie stanu po 60 s ciszy. Bez nowych wiadomości ostatni wpis w HA może pozostać nieaktualny. | Dodać nieinwazyjny mechanizm timeout-update i test bez nowych wiadomości; poprawne available/unknown. |
| AUD-03 | P1 | sensor.py 177-184, 300-312 | Starszy EurosOSSensor nadpisuje state(), zwraca tekst 'unavailable' i nadpisuje unit_of_measurement; dla nowego kodu zalecane jest native_value/available i native_unit_of_measurement. | Ustalić zgodne z API HA rozwiązanie i sprawdzić brak migracji/zmiany unique_id oraz historii. |
| AUD-04 | P1 | coordinator.py 247-336; __init__.py 26-40, 86-90 | connect() w razie wyjątku/logicznego timeoutu tylko loguje i może zwrócić None, podczas gdy setup_entry kontynuuje rejestrację platform. | Zapewnić poprawny stan awarii/retry w HA, kontrolę zatrzymania częściowo uruchomionego klienta i test reconnect. |
| AUD-05 | P1 | coordinator.py 339-369 | async_set_device_value() zwraca True po samym wywołaniu client.publish(), bez weryfikacji wyniku Paho ani potwierdzenia urządzenia. | Rozróżnić błędy wysyłki od sukcesu; nie obiecywać potwierdzonego zastosowania przez pompę bez echa ze stanu. |
| AUD-06 | P1 | coordinator.py 329-333; config_flow.py 107-112 | TLS korzysta z kontekstu bez weryfikacji certyfikatu. Rozwiązanie odziedziczone; zmiana bez zbadania urządzeń może zerwać łączność. | Przeprowadzić badanie zgodności i dobrać bezpieczną konfigurację, testować osobno od wdrożenia produkcyjnego. |
| AUD-07 | P1 | config_flow.py 57-60, 128; coordinator.py 365-368; const.py | Logi debug mogą ujawniać identyfikator tematu, pełny payload oraz publikowane dane; stałe uwierzytelniające są w kodzie upstream. | Zredagować logi, ocenić model autoryzacji urządzenia i unikać sekretów w materiałach PR. Nie ujawniać konkretnych danych w raportach. |
| AUD-08 | P1 | switch.py 93-98; binary_sensor.py 70-84 | Niektóre brakujące wartości switch stają się False/0, a niepoprawne typy mogą wywołać wyjątek; dla dwóch czujników wczesny return może pozostawić poprzedni stan. | Ujednolicić None/unknown, testować błędne pola i brak komunikacji. |
| AUD-09 | P2 | sensor.py 277-296 | Starszy szacowany licznik ZM_AC_IN_ENERGY integruje moc przy odczycie state(), co może zależeć od częstotliwości zapisów; dla GEO już wyłączony. | Rozważyć zmianę/ograniczenie po ocenie zgodności z ATMO/ALLINONE. Nie utożsamiać z energią METER_1. |
| AUD-10 | P2 | __init__.py 79-81; sensor.py 314-316; number.py 82-90 | Część callbacków działa już na pętli HA, ale ponownie zleca call_soon_threadsafe; może powodować zbędne opóźnienia i utrudniać wyładowanie. | Uporządkować przekazywanie aktualizacji, testować wyścigi i unload. |
| AUD-11 | P2 | sensor.py 55-155; tests/test_dynamic_ems.py | Dynamiczne METER_N mają testy na atrapach HA, nie na prawdziwym METER_2; METER_1 jest potwierdzony sprzętowo. | Rozbudować testy rejestru HA; ograniczenie sprzętowe jawnie opisać. |
| AUD-12 | P2 | manifest.json; hacs.json; README.md; nagłówki modułów | Rozbieżne numery wersji, minimalna wersja HA, nazewnictwo i opis obsługiwanych modeli; iot_class local_polling mimo danych MQTT push; sprawdzić też obsługę paczki HACS. | Ujednolicić metadane, podjąć decyzję o finalnym version razem z autorem, dodać instrukcję aktualizacji. |
| AUD-13 | P2 | .github/workflows/euros-os-stage4-tests.yml | Workflow tylko na wyliczone gałęzie rozwojowe, bez pull_request i bez Pythona 3.14. | Utworzyć neutralny workflow dla końcowej gałęzi/PR, dołączyć Python 3.14 i bliższe HA testy. |
| AUD-14 | P2 | translations/en.json; translations/pl.json; geo.py; ems.py | Tłumaczenia obejmują głównie config flow, podczas gdy nowe nazwy GEO/EMS są wpisane po polsku na stałe. | Zaplanować nazwy tłumaczone bez przypadkowej zmiany istniejących entity_id; test migracji. |
| AUD-15 | P2 | docs/ETAP_8_PLAN_TESTOW_HA.md | Dziennik ETAPU 8 nadal opisuje test real HA jako niewykonany, choć test 2026-11-09 został przeprowadzony. | Uzupełnić dziennik faktycznymi wynikami i ograniczeniami, bez upubliczniania kopii HA. |

## Działania po audycie

1. W ETAPIE 9.2 najpierw rozstrzygnąć AUD-01, AUD-02, AUD-04, AUD-05, AUD-06, AUD-07 i AUD-08; przygotować osobne poprawki z testami i odtwarzać brak regresji.
2. Nie eksperymentować z rzeczywistą pompą w zakresie niepotwierdzonych komend. Wszystkie testy MQTT/TLS prowadzić najpierw bezpiecznie symulacyjnie.
3. Zweryfikować oficjalne API HA i testy oparte o prawdziwsze środowisko w ETAPIE 9.3/9.4.
4. Po zmianach powtórzyć kontrolę wszystkich 73 identyfikatorów i historię w rzeczywistym HA, jeśli będzie uzgodniona instalacja testowa.
5. Uporządkować dokumentację i clean-room diff do upstream. PR #3 rozstrzygnąć przed ostatnim PR.

## Kryteria

- P0 = krytyczne (bezwarunkowo blokuje PR); P1 = wysokie (naprawić albo technicznie udowodnić brak ryzyka; blokuje PR); P2 = do poprawy lub jawnego zaakceptowania.
- Audyt nie zmienia kodu użytkowego ani statusu bezpieczeństwa uruchomionej integracji.
- Ciągłość zachowania GEO_1/EMS Dom i 73 identyfikatorów jest warunkiem każdej kolejnej poprawki.

Źródła API: https://developers.home-assistant.io/docs/core/entity/sensor/ ; https://developers.home-assistant.io/docs/core/entity/ ; https://developers.home-assistant.io/docs/integration_fetching_data/.
