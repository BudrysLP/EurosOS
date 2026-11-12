# Euros OS — ETAP 9.2: niezawodność i bezpieczeństwo

**Stan na 2026-11-09.** Kod i symulacje: **6 z 8 punktów ukończonych**. 
**UWAGA: nie zakończono audytu sprzętowego TLS ani ostatecznej bramki regresyjnej po potencjalnej zmianie TLS.**
Brak wdrożenia zmian ETAPU 9.2 na działającym Home Assistant.

## Punkt odniesienia

- Repozytorium: `BudrysLP/EurosOS`.
- Baza (ETAP 8): `feature/stage8-ha-preflight`, commit `12d2502091d2364e7cb1803eef3bd523a31618de`.
- Audyt: `feature/stage9-audit` (dokumenty 9.1).
- Zmiany techniczne: `feature/stage9-reliability`, utworzona z audytu.
- Ostatnia zweryfikowana seria testów na kodzie przed zapisem dokumentacji: [GitHub Actions run 42715633143](https://github.com/BudrysLP/EurosOS/actions/runs/42715633143) — **120/120** Python 3.12 i **120/120** Python 3.13 (kolejne drobne zmiany logowania i dokumentacji wymagają osobnego zielonego przebiegu).
- Upstream `main`, fork `main`, PR #3 i produkcyjny HA — bez zmian.

## Lista 9.2

| ID | Stan | Wykonane / ograniczenia |
| --- | --- | --- |
| 9.2.1 | ✅ testy symulacyjne | Watchdog `async_track_time_interval` co 10 s; po `MQTT_TIMEOUT=60` odświeża `available` pompy i liczników bez nowych pakietów; brak usuwania danych; kontrolki pompy także sprawdzają świeżość. Test w prawdziwym HA jest częścią 9.5. |
| 9.2.2 | ✅ testy symulacyjne | Błąd pierwszego połączenia / brak CONNACK zatrzymuje klienta, zgłasza `ConnectionError`, a `async_setup_entry` przekazuje `ConfigEntryNotReady` do automatycznych ponowień HA; idempotentny unload i reconnect przetestowane na atrapach. |
| 9.2.3 | ✅ testy symulacyjne | MQTT nie wywołuje metod HA bezpośrednio z wątku Paho; event loop dispatch, testy zamknięcia pętli, unload i wyścigów pozostały zielone. Kontrola prawdziwego HA osobno. |
| 9.2.4 | ✅ testy symulacyjne | Błędny JSON, nieprawidłowe Devices, duplikaty METER_N, NaN, błędne i brakujące wartości są obsługiwane ostrożnie; przełączniki nie interpretują brakującego pola jako OFF i błędnych flag CWU Turbo jako prawidłowych. |
| 9.2.5 | ⏳ otwarte / P1 | TLS nadal używa `ssl._create_unverified_context()` w koordynatorze i config flow. To **brak weryfikacji tożsamości brokera**. Bez informacji o certyfikacie faktycznego urządzenia nie przełączamy tego na ślepo, by nie zerwać działającego połączenia. |
| 9.2.6 | ✅ analiza i CI | Usunięto logowanie pełnego payloadu discovery, wartości wszystkich liczników, szczegółów wysyłanych komend oraz części danych sieciowych. Dodatkowo odrzucane błędne pakiety logowane są na poziomie DEBUG, aby nie zalewać dzienników. |
| 9.2.7 | ✅ testy symulacyjne | Oddzielono rozpoznanie AUTO i EMS dla GEO w NumberEntity. Zachowano dotychczasową możliwość korekty temperatury w EMS; brakująca/niepoprawna flaga taryfy blokuje nastawę. Niezweryfikowane przełączenia do EMS i EMS→AUTO nadal blokowane. `publish().rc` i świeżość pompy są sprawdzane; przyjęcie przez klienta MQTT nie oznacza wykonania przez urządzenie. |
| 9.2.8 | ⏳ otwarte | Wszystkie dotychczasowe poprawki otrzymały testy automatyczne; **ostateczne** odhaczenie dopiero po rozstrzygnięciu TLS i ostatnim zielonym przebiegu CI. |

## Zmiany kodu

1. `custom_components/euros_os/__init__.py` — watchdog i wyrejestrowanie timera podczas unload; zgłaszanie `ConfigEntryNotReady` przy braku połączenia.
2. `coordinator.py` — kontrola przeterminowania GEO i każdego METER_N, odbudowa po odświeżeniu, cleanup klienta MQTT po błędnym connect, sprawdzanie `publish().rc`, blokada poleceń z nieaktualnym odczytem pompy, zredukowane logi i usunięcie nieużywanej funkcji szczegółowych próbek.
3. `sensor.py` — natywna dostępność pomp zamiast tekstu `"unavailable"`; tożsamość i `unique_id` bez zmian.
4. `number.py` — dostępność po świeżości pompy, GEO EMS / AUTO rozróżnione z `U_ENE_TAR` przy zachowaniu temperatur CWU w EMS.
5. `select.py`, `switch.py`, `binary_sensor.py` — dostępność kontrolek zależna od świeżości pompy; przełącznik nie przyjmuje błędnych flag jako poprawnych.
6. `config_flow.py` — ograniczenie informacji z odkrywania MQTT w dziennikach.
7. `tests/test_coordinator_discovery.py`, `tests/test_dynamic_ems.py`, `tests/test_mqtt_to_ha_integration.py`, `tests/test_stage9_reliability.py`, `tests/test_stage9_mode_safety.py` — nowe testy braku MQTT, stale/unknown, reconnect, publish, EMS oraz logowania.
8. `.github/workflows/euros-os-stage4-tests.yml` — dopisano gałąź roboczą do wyzwalaczy CI.

## Nierozstrzygnięte ryzyka i kryteria dalszych prac

**TLS / P1:** zarówno `coordinator.py`, jak i `config_flow.py` odziedziczyły brak weryfikacji certyfikatu TLS. Dokumentacja Paho zaleca używanie zweryfikowanego kontekstu TLS, a wyłączenie weryfikacji nie zapewnia uwierzytelnienia serwera.
Przed zmianą trzeba bezpiecznie ustalić wystawcę i nazwę certyfikatu brokera urządzenia, czy jest podpisany przez zaufane CA i jak zmiana zachowa się przy IP zamiast DNS. Nie umieszczać prywatnych kluczy, danych uwierzytelniających ani certyfikatów z kluczem prywatnym w GitHub.
Źródło: https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html

**Dane uwierzytelniające / P1:** `const.py` ma odziedziczone po upstream stałe dostępu do brokera. Samo ukrycie ich w logach nie rozwiązuje modelu uwierzytelniania. Z autorem należy ustalić, czy urządzenie umożliwia indywidualne poświadczenia i bezpieczne ich przechowywanie w HA; bez danych o firmware nie usuwać domyślnego sposobu dostępu.

**Granice testów:** testy były wykonywane z atrapami HA i klienta Paho, bez prawdziwego brokera oraz urządzenia; brak gwarancji działania przy wszystkich wariantach firmware. Wdrożenie i test utraty MQTT w działającym HA przewidziano w 9.5, po kopii bezpieczeństwa i odrębnej zgodzie użytkownika.

**Aktualizacja źródłowych API:** `ConfigEntryNotReady` jest zgodny z wytycznymi HA dotyczącymi urządzeń chwilowo offline: https://contributors.home-assistant.io/core/integrations/setup-failures/ ;
`available` i zapisy stanów po push: https://contributors.home-assistant.io/core/entities/state-updates/ .

## Uzupełnienie 2026-11-12 — odczyt certyfikatu serwera MQTT (zadanie 9.2.5)

Użytkownik przeprowadził **wyłącznie odczytowy** test `openssl s_client` do lokalnego adresu używanego przez jego pompę na porcie 8883. Połączenie TLS przekazało certyfikat X.509:

- Subject CN: `ee-agent`; organizacja `OwnTracks.org` (dane deklarowane przez certyfikat).
- Issuer CN: `An MQTT broker`; organizacja `OwnTracks.org` (sam issuer nie dowodzi poprawności łańcucha zaufania).
- `notBefore`: 2020-05-12 17:43:38 UTC.
- `notAfter`: 2032-05-09 17:43:38 UTC; ważny czasowo w dniu 2026-11-12.
- SAN: nazwy `ee-agent`, `localhost`; adres IPv4 w SAN jest **inny** od aktualnego adresu IP, pod którym użytkownik łączy się z pompą. Są też adresy lokalne / IPv6.
- Wniosek: certyfikat **nie odpowiada nazwie docelowej weryfikowanej jako bieżący adres IP**. Włączenie `ssl.create_default_context()` i łączenie po tym adresie IP prawdopodobnie spowoduje błąd hostname/IP mismatch; dodatkowo nie mamy jeszcze dowodu zaufania do wystawcy.
- Pozostaje **P1 otwarte**, a test odczytu certyfikatu nie zmienia kodu ani parametrów sterowania urządzeniem.
- Kolejny **bezpieczny, read-only** test z terminala HA:
  ```sh
  openssl s_client -connect 192.168.1.17:8883 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -checkip 192.168.1.17
  ```
  Polecenie pokazuje wynik weryfikacji dopasowania IP osobno od sprawdzenia zaufania łańcucha. **Nie zmieniać adresu IP pompy i nie importować niezaufanego certyfikatu CA.**
- Następnie ocenić, czy broker przedstawia pełny łańcuch, czy możliwy jest bezpieczny trust anchor / poprawny hostname, lub czy konieczna byłaby kontrolowana zmiana certyfikatu po stronie urządzenia (wyłącznie z dokumentacją producenta i zgodą użytkownika). Nie włączać `tls_insecure_set(True)` jako pozornego rozwiązania.
- Niezależnie należy zbadać odziedziczony model uwierzytelniania MQTT w `const.py` bez publikowania poświadczeń w logach lub PR.

Źródła techniczne: https://docs.openssl.org/3.0/man1/openssl-x509/ ; https://docs.openssl.org/3.0/man1/openssl-s_client/ ; https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html

## Uzupełnienie 2026-11-12 — plan bezpiecznego zamknięcia TLS

Przygotowano osobny, publicznie bezpieczny dokument z poleceniami do odczytu dopasowania IP certyfikatu, próby walidacji łańcucha oraz z wariantami naprawy:
[ETAP_9_2_TLS_DIAGNOSTYKA.md](ETAP_9_2_TLS_DIAGNOSTYKA.md).

Weryfikacja zaufania wystawcy i dopasowania adresu to **dwa odrębne warunki**. Sam CAfile lub DNS alias nie rozwiązuje automatycznie obu problemów. Konfiguracja oparta na certyfikacie CA wymaga również sprawdzenia poprawności SAN/hostname. Funkcja `ssl._create_unverified_context()` pozostaje na razie w obu punktach połączenia ze względów kompatybilności, ale blokada P1 nadal obowiązuje.

Plan pozostaje wyłącznie diagnostyczny, bez zmian w Home Assistant i bez MQTT PUBLISH.

## Potwierdzone wyniki testów fizycznego TLS — 12 listopada 2026

Użytkownik wykonał oba bezpieczne polecenia diagnostyczne. Pierwsze zwróciło `IP 192.168.1.17 does NOT match certificate`, a drugie `verify error:num=19:self-signed certificate in certificate chain` na poziomie `depth=1`. Wyniki wskazują **niezależnie** na niezgodność IP z SAN certyfikatu serwera oraz brak zaufanego łańcucha certyfikatów wystawcy. Certyfikat nie jest czasowo przeterminowany.

Nie jest to dowód włamania ani awarii urządzenia. Samodzielny import CA bez niezależnej weryfikacji pochodzenia i dopasowania nazwy nie wystarczy. W szczególności nie wolno bez dodatkowego zaufanego źródła traktować odcisku certyfikatu odczytanego przez dotychczas nieuwierzytelnione połączenie jako pełnego dowodu tożsamości.

**9.2.5 pozostaje otwarte jako P1.** Następny krok: opcjonalna liczba certyfikatów przesłanych przez broker i ustalenie z producentem pochodzenia CA / sposobu zapewnienia weryfikowalnej nazwy serwera. Rozwiązanie musi zachowywać zgodność z innymi sterownikami; nie wprowadzano zmian w produkcyjnym HA ani domyślnym TLS.

Szczegóły w [ETAP_9_2_TLS_DIAGNOSTYKA.md](ETAP_9_2_TLS_DIAGNOSTYKA.md).

## Uzupełnienie — liczba certyfikatów w odpowiedzi brokera

Odczyt wykonany 12 listopada 2026 r. wskazał **2** certyfikaty PEM wysłane przez broker przy `-showcerts`. Jest to zgodne z hipotezą certyfikatu końcowego i certyfikatu wystawcy, ale wymaga potwierdzenia metadanych `subject`, `issuer` i `basicConstraints` drugiego certyfikatu. Sama liczba nie świadczy o zaufaniu do CA ani nie naprawia niedopasowania IP. Odczyt publicznych pól zaplanowano jako kolejny test read-only, opisany w [procedurze TLS](ETAP_9_2_TLS_DIAGNOSTYKA.md). 9.2.5 jest nadal otwarte (P1).

## Co dalej

- Rozstrzygnąć 9.2.5: model certyfikatu TLS, bezpieczne warianty konfiguracji i kompatybilność.
- Po każdej dodatkowej poprawce dodać regresję i ponownie uruchomić CI, następnie zakończyć 9.2.8.
- Nie otwierać upstream PR, nie scalać main, nie wdrażać tej gałęzi na produkcyjnym HA bez nowej kontroli 9.5.
