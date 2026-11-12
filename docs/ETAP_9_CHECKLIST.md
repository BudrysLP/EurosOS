# Euros OS — ETAP 9: główna lista kontrolna

Data aktualizacji: 2026-11-12. Właściciel prac: BudrysLP. Status: 9.1 ZAKOŃCZONY; 9.2 W TOKU (6/8; TLS P1); 9.3 W TOKU (8/9); 9.4 ZAKOŃCZONY (8/8); 9.5 W TOKU (2/8; zabezpieczenia i dokumentacja).

## Zasady

- Odhaczamy dopiero po sprawdzeniu wyniku; źródłem prawdy jest ten dokument w repozytorium.
- Najpierw testy i dokumentacja, potem końcowy PR. Nie otwieramy nowego PR przed 9.8.
- Na tym etapie nie modyfikujemy instalacji produkcyjnej Home Assistant ani upstream/main.
- P0/P1 blokują publikację, o ile nie zostały naprawione albo obiektywnie wyjaśnione.
- Każda zmiana mająca wpływ na istniejące encje wymaga kontroli 73 identyfikatorów.

## Odnośniki i punkt odniesienia

- Ostatni przetestowany kod: `feature/stage8-ha-preflight` @ `12d2502091d2364e7cb1803eef3bd523a31618de`.
- Gałąź dokumentacji ETAPU 9: `feature/stage9-audit`.
- Audyt i rejestr usterek: [ETAP_9_1_AUDYT_TECHNICZNY.md](ETAP_9_1_AUDYT_TECHNICZNY.md).
- Raport zmian i otwartego ryzyka TLS: [ETAP_9_2_NIEZAWODNOSC_BEZPIECZENSTWO.md](ETAP_9_2_NIEZAWODNOSC_BEZPIECZENSTWO.md).
- Audyt zgodności i CI Python 3.14: [ETAP_9_3_KOMPATYBILNOSC.md](ETAP_9_3_KOMPATYBILNOSC.md).
- Preflight HACS / Marketplace i procedura aktualizacji: [ETAP_9_3_MARKETPLACE.md](ETAP_9_3_MARKETPLACE.md).
- Rzeczywiste klasy HA 2026.11 i test rejestru 73 encji: [ETAP_9_3_TESTY_HA_CORE.md](ETAP_9_3_TESTY_HA_CORE.md).
- Rozbudowa testów 9.4, macierz CI i 0 pominięć: [ETAP_9_4_TESTY_AUTOMATYCZNE.md](ETAP_9_4_TESTY_AUTOMATYCZNE.md).
- Procedura ETAPU 9.5, bramki bezpieczeństwa i prywatne porównanie rejestrów: [ETAP_9_5_PLAN_TESTOW_HA.md](ETAP_9_5_PLAN_TESTOW_HA.md).
- Narzędzie prywatnego odczytu i porównania 73 encji: [ha_registry_snapshot.py](../scripts/ha_registry_snapshot.py); testy syntetyczne [test_ha_registry_snapshot.py](../tests/test_ha_registry_snapshot.py).
- Diagnostyka certyfikatu i plan rozwiązań: [ETAP_9_2_TLS_DIAGNOSTYKA.md](ETAP_9_2_TLS_DIAGNOSTYKA.md).
- Wynik CI 94/94 Python 3.12 + 94/94 Python 3.13: https://github.com/BudrysLP/EurosOS/actions/runs/42687735935 .
- PR #3: https://github.com/McKoPcIu/EurosOS/pull/3 (otwarty); PR #4: https://github.com/McKoPcIu/EurosOS/pull/4 (zamknięty).

## Postęp

- Ukończono: **32/69** zadań (46.4%).
- Ukończony podetap: **9.1 (8/8)** — audyt statyczny, nie naprawa usterek.
- Aktywne podetapy: **9.2 (6/8)** — otwarty TLS/P1 i regresja po zmianach; **9.3 (8/9)** — do kontroli rzeczywista aktualizacja Marketplace; **9.4 (8/8)** — komplet CI; **9.5 (2/8)** — zabezpieczenia 9.5.1 potwierdzone przez operatora (pełna kopia poza HA, klucz odzyskiwania, archiwum integracji), a 9.5.7 dokumentacja ograniczeń sprzętowych zamknięta. Otwarty zakres/okno testowe 9.5.2 oraz wdrożenie i testy produkcyjne.

## 9.1 — Audyt kodu źródłowego (8/8)

- [x] **9.1.1** Zamrozić i zapisać punkt odniesienia: commit, gałąź, manifest, workflow oraz wynik CI.
- [x] **9.1.2** Porównać aktualny kod z oryginalnym main autora i ustalić pełną listę zmian.
- [x] **9.1.3** Sprawdzić __init__.py: inicjalizacja, rejestr urządzeń, reload, unload i sprzątanie zasobów.
- [x] **9.1.4** Sprawdzić coordinator.py: MQTT, współbieżność, reconnect, timeouty, błędy i publikowanie poleceń.
- [x] **9.1.5** Sprawdzić discovery.py, geo.py i ems.py: rozpoznawanie i parsowanie danych.
- [x] **9.1.6** Sprawdzić sensor.py, number.py, select.py, switch.py oraz binary_sensor.py.
- [x] **9.1.7** Sprawdzić config_flow.py, const.py, manifest.json i tłumaczenia.
- [x] **9.1.8** Przygotować rejestr usterek z priorytetami P0/P1/P2 i planem poprawek.

## 9.2 — Niezawodność i bezpieczeństwo (6/8)

- [x] **9.2.1** Zweryfikować zachowanie HA po przekroczeniu MQTT_TIMEOUT bez nowych wiadomości.
- [x] **9.2.2** Zweryfikować reconnect, wielokrotne reload/unload i brak pozostawionych wątków MQTT.
- [x] **9.2.3** Sprawdzić współbieżny dostęp do danych i bezpieczne przekazywanie aktualizacji do pętli HA.
- [x] **9.2.4** Zweryfikować obsługę błędnych JSON, NaN, braków pomiarów i duplikatów urządzeń.
- [ ] **9.2.5** Zbadać TLS, weryfikację certyfikatu oraz sposób obsługi danych uwierzytelniających. **Testy na prawdziwej pompie wykonane: ‘checkip’ wykazał niedopasowanie IP, a ‘verify_return_error’ wykazał niezaufany certyfikat wystawcy (depth=1, num=19). Test `-showcerts` potwierdził **2 przesłane certyfikaty**. Odczyt drugiego certyfikatu potwierdził samopodpisany Root CA z `CA:TRUE` (OwnTracks.org). Nadal brakuje niezależnego potwierdzenia autentyczności CA oraz bezpiecznego modelu weryfikacji nazwy/IP; punkt pozostaje otwarty (P1).**
- [x] **9.2.6** Sprawdzić, czy logi nie ujawniają kluczy, haseł ani poufnych payloadów.
- [x] **9.2.7** Potwierdzić blokowanie niezweryfikowanych komend EMS i brak niezamierzonego sterowania.
- [ ] **9.2.8** Każdą potrzebną poprawkę opatrzyć testem regresyjnym.

## 9.3 — Kompatybilność urządzeń i Home Assistant (8/9)

- [x] **9.3.1** Sprawdzić rozpoznawanie FriskoGEO, FriskoATMO i FriskoALLINONE.
- [x] **9.3.2** Zweryfikować wybór pompy niezależnie od kolejności Devices oraz bezpieczeństwo przy wielu pompach.
- [x] **9.3.3** Sprawdzić istniejące i nowe unique_id, entity_id i identyfikatory urządzeń.
- [x] **9.3.4** Sprawdzić natywne API SensorEntity, NumberEntity, SelectEntity i pozostałych encji. **Przeprowadzono testy na rzeczywistych klasach HA Core 2026.11.0 oraz test rejestracji; MQTT bez fizycznej pompy.**
- [x] **9.3.5** Zweryfikować device_class, state_class, jednostki pomiarowe i zgodność z panelem Energia. **Zakończono audyt metadanych i poprawiono szacowanie energii ZM_AC_IN_ENERGY z bezpiecznym RestoreSensor oraz testami; deklaracje HA Energy są zgodne. Uwaga: widok panelu Energia i ciągłość historii na prawdziwym HA pozostają do weryfikacji w ETAPIE 9.5.**
- [x] **9.3.6** Sprawdzić zachowanie METER_1 i dodatkowych METER_N, bez fikcyjnych liczników.
- [x] **9.3.7** Sprawdzić odtwarzanie liczników dziennych, północ, zmianę dnia i przerwy w danych.
- [x] **9.3.8** Zweryfikować kompatybilność z Pythonem 3.14 i Home Assistant Core 2026.11. **137/137 testów na Pythonie 3.12/3.13/3.14 oraz 5 testów rzeczywistego API + 1 test setup/unload na Core 2026.11.0/Python 3.14.10; dwa urządzenia i 73 encje zarejestrowane, test fizycznego HA pozostaje w 9.5.**
- [ ] **9.3.9** Zweryfikować manifest, metadane HACS, instalację oraz ścieżkę aktualizacji bez utraty encji. **Preflight ZIP zakończony: utworzono generator, 3 testy pakowania, a CI 137/137 ×3 poprawnie buduje płaski euros_os.zip (15 plików). Nadal otwarte: rzeczywista aktualizacja w Marketplace i zgodność minimum HA (hacs.json 2021.12 vs README 2023.3) oraz decyzja autora o wersji wydania.**

## 9.4 — Rozszerzenie testów automatycznych (8/8)

- [x] **9.4.1** Uporządkować nazwy oraz wyzwalacze workflow, w tym uruchamianie na pull_request.
- [x] **9.4.2** Uruchamiać zestaw testów na Pythonie 3.12, 3.13 i 3.14, z uwzględnieniem kompatybilności zależności.
- [x] **9.4.3** Rozbudować testy inicjalizacji i wyładowania integracji z API Home Assistant.
- [x] **9.4.4** Przetestować automatyczne wykrywanie wielu pomp i liczników.
- [x] **9.4.5** Przetestować stale dane MQTT, rozłączenie, ponowne połączenie i wyścigi wątków.
- [x] **9.4.6** Przetestować przywracanie dziennych liczników i obsługę niepoprawnych odczytów.
- [x] **9.4.7** Przetestować blokady komend i zachowanie dotychczasowych kontrolek.
- [x] **9.4.8** Uzyskać zielony wynik wszystkich wymaganych testów bez pominięć i udokumentować zakres.

## 9.5 — Ostateczna kontrola na rzeczywistym HA (2/8; zabezpieczenia gotowe)

- [x] **9.5.1** Zachować aktualne kopie bezpieczeństwa i aktualizować je przed kolejnym wdrożeniem. **Potwierdzone przez operatora 12.11.2026: pełna kopia HA 1,2 GB pobrana poza HA, obejmuje konfigurację i historię, klucz Emergency Kit dostępny; archiwum aktualnego katalogu Euros OS 66,5 KB sprawdzone odczytem `tar -tzf`, prawa 0600. Nie wykonywano próby pełnego odtworzenia — przed wdrożeniem ponownie potwierdzić aktualność kopii.**
- [ ] **9.5.2** Uzgodnić okno testowe i zakres ingerencji w działający HA. **Cztery kluczowe pliki obecnej integracji (`__init__.py`, `coordinator.py`, `sensor.py`, `manifest.json`) porównano SHA-256 z commitem ETAPU 8 `12d2502…` i są identyczne. Nadal wymagana kontrola pozostałych plików oraz zatwierdzenie zakresu i ewentualnego restartu.**
- [ ] **9.5.3** Sprawdzić GEO_1, EMS Dom i dotychczasowe 73 encje po ewentualnych poprawkach. **12.11.2026 zapisano prywatny `before.json`: 73 encje i 2 urządzenia. Odczyt bazowy zaliczony; właściwy test porównawczy po wdrożeniu i weryfikacja odczytów GEO/EMS pozostają otwarte.**
- [ ] **9.5.4** Sprawdzić bieżące aktualizacje oraz ciągłość historii energii przed i po restarcie.
- [ ] **9.5.5** Zweryfikować zachowanie stale/unavailable i powrotu połączenia w sposób bezpieczny dla pompy.
- [ ] **9.5.6** Przejrzeć logi po starcie oraz po okresie normalnej pracy.
- [x] **9.5.7** Udokumentować nieprzetestowane scenariusze sprzętowe, np. fizyczny METER_2. **Zestawienie sporządzone: ATMO, ALLINONE, METER_2/METER_3, MQTT, TLS, Marketplace i nieweryfikowane przełączenia GEO. Nie oznacza to fizycznego zaliczenia tych scenariuszy.**
- [ ] **9.5.8** Potwierdzić, że nie ma powodów do rollbacku i że wersja nadaje się do wydania.

## 9.6 — Dokumentacja i przygotowanie wydania (0/10)

- [ ] **9.6.1** Przepisać README: możliwości, obsługiwane modele, wymagania, instalacja i aktualizacja.
- [ ] **9.6.2** Opisać GEO: temperatury, stany, tryby i ograniczenia sterowania.
- [ ] **9.6.3** Opisać EMS Dom: 35 encji, jednostki, źródła danych i znaczenie pomiarów.
- [ ] **9.6.4** Opisać dynamiczne METER_N oraz brak gwarancji zgodności wszystkich liczników bez testów sprzętowych.
- [ ] **9.6.5** Zaktualizować dokumentację ETAPU 8 o faktyczne wyniki z Home Assistant.
- [ ] **9.6.6** Dodać instrukcję aktualizacji istniejącej instalacji bez kasowania urządzeń i historii.
- [ ] **9.6.7** Dodać instrukcję diagnostyki, ograniczenia bezpieczeństwa oraz scenariusz cofnięcia aktualizacji.
- [ ] **9.6.8** Sprawdzić polskie i angielskie nazwy oraz tłumaczenia.
- [ ] **9.6.9** Ujednolicić metadane wersji; decyzję o numerze wydania pozostawić autorowi.
- [ ] **9.6.10** Przygotować CHANGELOG i zwięzły raport testowy dla autora.

## 9.7 — Czysta gałąź do upstream (0/7)

- [ ] **9.7.1** Sprawdzić aktualny main autora przed przygotowaniem końcowej gałęzi.
- [ ] **9.7.2** Rozstrzygnąć los PR #3 i uniknąć nakładających się poprawek.
- [ ] **9.7.3** Utworzyć nową gałąź upstream od właściwego commitu main.
- [ ] **9.7.4** Przenieść wyłącznie gotowy, zweryfikowany kod i potrzebne materiały.
- [ ] **9.7.5** Ułożyć commity według obszarów: GEO, EMS, discovery, bezpieczeństwo, testy i dokumentacja.
- [ ] **9.7.6** Usunąć zbędne pliki robocze, dane diagnostyczne i historyczne komentarze.
- [ ] **9.7.7** Sprawdzić końcowy diff i ponownie uruchomić pełną CI na tej gałęzi.

## 9.8 — Bramka jakości przed PR (0/7)

- [ ] **9.8.1** Brak otwartych błędów P0 i P1; pozostałe ograniczenia świadomie zaakceptowane.
- [ ] **9.8.2** Wszystkie wymagane testy zielone na końcowym commicie.
- [ ] **9.8.3** Potwierdzona zgodność wsteczna i bezpieczeństwo sterowania.
- [ ] **9.8.4** Dokumentacja, CHANGELOG i instrukcja aktualizacji gotowe.
- [ ] **9.8.5** Sprawdzone, że PR nie obejmie przypadkowych plików ani sekretów.
- [ ] **9.8.6** Przygotowany pełny opis PR i lista znanych ograniczeń.
- [ ] **9.8.7** Uzyskać zgodę użytkownika na publikację końcowego PR.

## 9.9 — Wysłanie jednego końcowego PR (0/4)

- [ ] **9.9.1** Otworzyć PR z gotowej, przetestowanej gałęzi do repozytorium autora.
- [ ] **9.9.2** Dołączyć raport CI, testy rzeczywistej instalacji i zakres wspieranych modeli.
- [ ] **9.9.3** Udzielić odpowiedzi na ewentualne uwagi autora i wprowadzić poprawki z testami.
- [ ] **9.9.4** Po akceptacji autora zaktualizować dokumentację projektu i uporządkować gałęzie robocze, bez samodzielnego scalania do upstream main.

## Dziennik wykonania

| Data | Zakres | Wynik | Dowód |
| --- | --- | --- | --- |
| 2026-11-09 | 9.1.1–9.1.8 | Ukończony audyt statyczny, 15 ustaleń (P1/P2), bez zmian w kodzie produkcyjnym | [Raport](ETAP_9_1_AUDYT_TECHNICZNY.md) |
| 2026-11-09 | 9.2.1–9.2.4, 9.2.6–9.2.7 | Zielone testy symulacyjne; 9.2.5 TLS i 9.2.8 końcowa regresja nadal otwarte | [Raport](ETAP_9_2_NIEZAWODNOSC_BEZPIECZENSTWO.md), [CI 120/120 na każdą wersję](https://github.com/BudrysLP/EurosOS/actions/runs/42715633143) |
| 2026-11-12 | 9.2.5 — diagnostyka certyfikatu | Potwierdzono poprawny odczyt X.509 i niedopasowanie adresu IP; pełna weryfikacja i strategia bezpiecznego TLS pozostają otwarte | [Raport](ETAP_9_2_NIEZAWODNOSC_BEZPIECZENSTWO.md) |
| 2026-11-12 | 9.2.5 — projekt diagnostyki | Opracowano polecenia do sprawdzenia IP, CA i liczby certyfikatów oraz bezpieczne opcje wdrożenia; nie zmieniano TLS w integracji | [Procedura TLS](ETAP_9_2_TLS_DIAGNOSTYKA.md) |
| 2026-11-12 | 9.2.5 — dwa testy certyfikatu na sprzęcie | ‘checkip’: mismatch; ‘verify_return_error’: self-signed chain certificate na depth=1 (num=19). To osobne blokady; nie zmieniano połączenia ani produkcyjnego HA | [Wyniki i decyzje](ETAP_9_2_TLS_DIAGNOSTYKA.md) |
| 2026-11-12 | 9.2.5 — liczba certyfikatów | Broker przesyła 2 certyfikaty PEM; zaplanowano odczyt publicznych danych drugiego oraz niezależne potwierdzenie CA. Zadanie pozostaje otwarte | [Procedura TLS](ETAP_9_2_TLS_DIAGNOSTYKA.md) |
| 2026-11-12 | 9.2.5 — weryfikacja drugiego certyfikatu | Subject=Issuer, `CA:TRUE`, nazwy zgodne z publicznym generatorem OwnTracks; to przesłanka metody wygenerowania, nie niezależne uwierzytelnienie CA. 9.2.5 pozostaje P1 | [Analiza](ETAP_9_2_TLS_DIAGNOSTYKA.md) |
| 2026-11-12 | 9.3.1–9.3.3, 9.3.6–9.3.7 | Rozpoznawanie pomp, porządek MQTT, stałość identyfikatorów, METER_N i restart/dobowe liczniki zaliczone w symulacjach. Python 3.14.10 CI zielony, natywne sensory poprawione, 4 punkty 9.3 nadal otwarte | [Raport](ETAP_9_3_KOMPATYBILNOSC.md), [CI 125/125 x3](https://github.com/BudrysLP/EurosOS/actions/runs/43201747083) |
| 2026-11-12 | 9.3.5 | Poprawiono szacowanie energii pompy: bez efektów ubocznych odczytu, RestoreSensor, obsługa luk MQTT i trwały unique_id. Skorygowano klasy RPM i PWM%. Potwierdzono metadane zgodne ze schematem Energy; test w rzeczywistym HA przeniesiony do 9.5. | [Raport](ETAP_9_3_KOMPATYBILNOSC.md), [CI 134/134 ×3](https://github.com/BudrysLP/EurosOS/actions/runs/43204946143) |
| 2026-11-12 | 9.3.9 — preflight pakowania | Zbudowano i zweryfikowano w CI ZIP z 15 plikami integracji oraz kompletność metadanych; wykryto rozbieżność minimalnej HA i wersji wydania. Rzeczywista instalacja Marketplace nie została wykonana; zadanie nadal otwarte | [Raport](ETAP_9_3_MARKETPLACE.md), [CI 137/137 ×3 + ZIP](https://github.com/BudrysLP/EurosOS/actions/runs/43209612693) |
| 2026-11-12 | 9.3.4 i 9.3.8 | 5 testów prawdziwych klas Home Assistant 2026.11 + 1 test setup/unload Core z atrapą MQTT: 2 urządzenia, 73 encje, 73 unikalne klucze rejestru, poprawne id i odczyty. Brak zmian w produkcyjnym HA | [Raport](ETAP_9_3_TESTY_HA_CORE.md), [CI 137×3 + 6 testów HA](https://github.com/BudrysLP/EurosOS/actions/runs/43212325942) |
| 2026-11-12 | 9.4.1–9.4.8 | Workflow PR/push, ścisły zakaz pomijania testów, wielopompowe MQTT/METER_N, reconnect/stale, sumowanie dzienne, blokady GEO/CWU i dwukrotny setup/unload HA. 154/154 testów na każdym Pythonie 3.12/3.13/3.14, 6/6 testów prawdziwego HA Core 2026.11, 0 skipped. Pull_request skonfigurowany, ale bez faktycznego PR | [Raport 9.4](ETAP_9_4_TESTY_AUTOMATYCZNE.md), [Zielone CI](https://github.com/BudrysLP/EurosOS/actions/runs/43215284763) |
| 2026-11-12 | 9.5 przygotowanie + 9.5.7 | Opracowano bramki backup/zgoda, scenariusze HA9-01–HA9-09 i rollback; narzędzie snapshotów sprawdzone w CI na sztucznych danych. Lista nieprzetestowanych urządzeń sporządzona. Brak odczytu aktualnego HA, brak instalacji i restartu | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md), [Snapshoty](../scripts/ha_registry_snapshot.py) |
| 2026-11-12 | 9.5.1 – weryfikacja backupów | Użytkownik pokazał 3 kopie automatyczne; najnowsza opisana jako 2026.11.1 (1,2 GB). Nie jest jeszcze potwierdzona kompletność, kopia poza HA ani osobne archiwum bieżącej integracji. Punkt 9.5.1 pozostaje otwarty | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md) |
| 2026-11-12 | 9.5.1 – potwierdzenie użytkownika | Operator potwierdził pobranie najnowszej kopii na komputer. Niezweryfikowane niezależnie: możliwość odtworzenia, klucz szyfrowania, odrębne bieżące archiwum euros_os. Bez instalacji, restartu i odczytu rejestrów | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md) |
| 2026-11-12 | 9.5 – nieudany odczyt bazowy i poprawka | Pierwszy odczyt core.entity_registry przerwany bez zapisu before.json; brak pola domain w storage HA 2026.11, urządzenia przypisane przez config_entry_id. Poprawiono prywatne narzędzie i testy. Nie zmieniano HA, pompy ani rejestrów | [Plan i analiza](ETAP_9_5_PLAN_TESTOW_HA.md), [Skrypt](../scripts/ha_registry_snapshot.py) |
| 2026-11-12 | 9.5 — udany prywatny snapshot | Operator potwierdził wynik `Private baseline saved: 73 entities, 2 devices.`; utworzono przedwdrożeniowy `before.json` w prywatnym folderze HA. Brak restartu, instalacji i testów powdrożeniowych; 9.5.3 pozostaje otwarty | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md) |
| 2026-11-12 | 9.5.1 – osobne archiwum integracji | Operator utworzył archiwum bieżącego `custom_components/euros_os` (66,5 KB), sprawdził `tar -tzf` i potwierdził uprawnienia `0600`; jeszcze nie zweryfikowano klucza odzyskiwania i kompletności pełnej kopii. Bez zmian HA | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md) |
| 2026-11-12 | 9.5.1 – zabezpieczenia potwierdzone | Operator potwierdził posiadanie Emergency Kit i pełnej kopii 1,2 GB obejmującej konfigurację oraz historię, pobranej na komputer. Archiwum integracji 66,5 KB i snapshot 73/2 już zapisane. 9.5.1 zamknięte na podstawie oświadczenia operatora, bez próby odtworzenia, restartu lub zmian w HA | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md) |
| 2026-11-12 | 9.5.2 — weryfikacja kodu | SHA-256 czterech plików zainstalowanych w HA zgodne z commitem ETAPU 8 `12d2502…`; do sprawdzenia pozostałe 11 plików i pliki dodatkowe. Bez wdrożenia i restartu; 9.5.2 nadal otwarte | [Plan 9.5](ETAP_9_5_PLAN_TESTOW_HA.md) |

## Kolejny ruch

9.5.1 zamknięte na podstawie potwierdzenia operatora; snapshot bazowy 73 encji i 2 urządzeń gotowy. Teraz uzgodnić **9.5.2: zakres testów, okno serwisowe i wyraźną zgodę na ewentualne wdrożenie i restart**; bez tego nie zmieniać produkcyjnego HA. Przed samą instalacją ponownie potwierdzić aktualność backupu i bazowego snapshotu. TLS 9.2.5/P1 i Marketplace 9.3.9 wciąż otwarte; regresję 9.2.8/9.8 wykonać po zmianach.
