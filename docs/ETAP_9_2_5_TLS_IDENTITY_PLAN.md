# Euros OS — ETAP 9.2.5: plan poprawy weryfikacji tożsamości MQTT/TLS

Data: 2026-11-13. Status: **projekt, bez zmian produkcyjnych i bez aktywacji nowego sposobu połączenia**.

## Problem
W aktywnym Euros OS `coordinator.py` wykorzystywany jest `ssl._create_unverified_context()`, co daje szyfrowanie transmisji bez weryfikacji tożsamości brokera. Broker korzysta z TLS 1.3 na porcie 8883 i serwuje certyfikat końcowy oraz certyfikat CA. Historyczny certyfikat nie obejmuje obecnego adresu IP Home Assistant w SAN, ale zawiera jednoczłonową nazwę DNS, dla której walidacja nazwy i łańcucha względem certyfikatu CA **działa w odizolowanym teście OpenSSL**. Certyfikat CA został pobrany z tego samego nieweryfikowanego połączenia, dlatego **jego autentyczność nie została niezależnie potwierdzona**. Brak wiarygodnego dowodu, że producent udostępnia oficjalne uniwersalne CA.

Pełne wyniki produkcyjne i prywatne odciski certyfikatów są prowadzone w **prywatnej** centralnej dokumentacji projektu na Google Drive; nie przenosić ich ani host/IP, nazw SAN czy konfiguracji urządzenia do publicznego repozytorium.

## Bramki wymagane przed wdrożeniem
1. Pozyskać niezależnie od producenta/administratora sterownika potwierdzenie autentyczności CA lub bezpieczną procedurę weryfikacji przypiętego klucza publicznego; nie uznawać CA przesłanego przez serwer za wiarygodne tylko dlatego, że walidacja `openssl verify -CAfile` zwraca PASS.
2. Uzgodnić stabilną nazwę z certyfikatu SAN rozwiązywaną na właściwy IP brokera na poziomie sieci widocznej dla HA. Zweryfikować, że konfiguracja i biblioteka MQTT rzeczywiście stosują tę samą nazwę jako `server_hostname` w TLS. Nie wykorzystywać `localhost` jako zdalnego adresu pompy.
3. Dopiero po 1–2 przygotować kod za przełącznikiem trybu ścisłej weryfikacji, bez cichego przechodzenia do `CERT_NONE` po błędzie certyfikatu. Rozważyć `ssl.create_default_context(cafile=...)` z `CERT_REQUIRED` i `check_hostname=True`. Nie wyłączać TLS.
4. Przygotować testy bez fizycznej pompy: poprawny certyfikat/nazwa/CA, błędny CA, błędna nazwa, wygasły certyfikat, odnowienie CA, przerwane połączenie, niedostępność brokera, brak zapisów sterujących przy niepowodzeniu TLS. Nie używać danych uwierzytelniających produkcji.
5. Ocenić procedurę migracji bez utraty rejestru 73 encji, historii 32 serii statystycznych EMS, danych GEO oraz innych komponentów; rollback do świeżej kopii, okno testowe i osobna zgoda operatora przed jakąkolwiek zmianą HA.
6. Nie publikować końcowego PR do upstream ani nie scalać gałęzi przed ukończeniem i zatwierdzeniem prac; autor integracji oczekuje jednego skonsolidowanego PR.

## Reguły bezpieczeństwa
- Na tej gałęzi wolno opracowywać dokumentację, testy i projekt implementacji; żaden commit nie instaluje niczego na Home Assistant.
- Nie zapisywać tokenów, haseł, certyfikatów CA z niezaufanego kanału, prywatnych kluczy, nazw hostów urządzeń ani danych osobowych w GitHub.
- Nie podejmować na produkcji prób zmiany DNS, certyfikatów, brokera, zapory, MQTT i nastaw GEO bez zgody operatora.
- Do czasu niezależnej weryfikacji CA NIE oznaczać TLS P1 jako naprawiony.

## Kontakt w sprawie oryginalnego CA
Oficjalne wsparcie techniczne Euros Energy: https://www.eurosenergy.com/kontakt/ . W zapytaniu poprosić o bezpieczną procedurę weryfikacji CA lub klucza publicznego serwera MQTT; o możliwość ustawienia SAN (IP/DNS), rotacji certyfikatu, zgodność sterownika z lokalną nazwą DNS i wpływ na gwarancję. Nie wysyłać danych dostępu lub prywatnych kluczy.

## Status pracy
- [x] Utworzono gałąź projektową `feature/tls-identity-verification`.
- [x] Wyjaśniono wstępny model i ograniczenia istniejących certyfikatów.
- [ ] Niezależnie potwierdzono CA / klucz serwera.
- [ ] Uzgodniono weryfikowalną nazwę brokera.
- [ ] Przygotowano i przetestowano poprawkę implementacyjną.
- [ ] Uzyskano zgodę na wdrożenie i wykonano test produkcyjny.
