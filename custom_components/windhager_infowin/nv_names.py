"""Lesbare Anzeigenamen fuer ausgewaehlte NV-Variablen (LON-Netzwerk-
variablen). Diese werden ueber den technischen Namen (nv.name, z.B.
"PMX_eeBetrStd") aus dem rohen LON-Variablennamen abgeleitet.

Nicht gelistete NV-Variablen behalten ihren technischen Rohnamen als
Anzeigename (z.B. "M_nviTVsoll") - sie sind weiterhin sichtbar, nur
ohne lesbare Uebersetzung.

Die Zuordnung ist bewusst auf die fuer den Hausgebrauch interessanten
Werte beschraenkt (Pelletverbrauch, Betriebsstunden, Drehzahlen etc.)
und kann nach Bedarf erweitert werden.
"""

READABLE_NV_NAMES = {
    # --- BioWIN Pelletkessel: Brenner/Betrieb ---
    "PMX_eeBetrStd": "Brenner Betriebsstunden",
    "PMX_eeNbrAnhz": "Brenner Anzahl Anheizvorgänge",
    "PMX_Status": "Brenner Status",
    "PMX_state": "Brenner Zustand",
    "PMX_nviLstg": "Brenner Leistungsvorgabe",
    "PMX_nvoLstg": "Brenner Leistung Istwert",
    "PMX_PwrAvg": "Brenner Leistung Mittelwert",
    "PMX_avgTb_Tk": "Brenner Kesseltemperatur Mittelwert",
    "PMX_CntShort": "Brenner Kurzzeitstörungen Anzahl",
    "PMX_CntLong": "Brenner Langzeitstörungen Anzahl",
    "PMX_InModTmr": "Brenner Einschaltverzögerung",

    # --- BioWIN Pelletkessel: Förderung/Vorrat ---
    "FS_nviMfoerder": "Pellet Fördermenge",
    "FS_nviMsoll": "Pellet Sollmenge",
    "FS_ioMsum": "Pellet Fördermenge Summe",
    "PZS_Restmenge": "Pellet Lager Restmenge",
    "PZS_status": "Pellet Zellenradschleuse Status",

    # --- BioWIN Pelletkessel: Gebläse ---
    "GB_nviNsoll": "Gebläse Drehzahl Soll",
    "GB_nvoNist": "Gebläse Drehzahl Ist",
    "GB_nvoNsoll": "Gebläse Drehzahl Soll (Rückmeldung)",

    # --- BioWIN Pelletkessel: Temperaturen ---
    "RG_nvoTemp": "Rauchgastemperatur",
    "RG_nviSetP": "Rauchgastemperatur Sollwert",
    "TK_nvoTemp": "Kesseltemperatur",
    "TK_nviSetP": "Kesseltemperatur Sollwert",
    "TK_nviExtSetP": "Kesseltemperatur externe Vorgabe",
    "NIC_nvoValue": "Zündungstemperatur",
    "NIC_nvoAvgVal": "Zündungstemperatur Mittelwert",

    # --- BioWIN Pelletkessel: Störungen/Reinigung ---
    "RUE_cntError": "Rückbrandsicherung Fehleranzahl",
    "RUE_cntEntaZue": "Rückbrandsicherung Entaschungszyklen",
    "FWN_nviRunTm2Cln": "Laufzeit bis nächste Reinigung",
    "FA_nvoError": "Feuerungsautomat Fehlercode",

    # --- Heizkreis-Module: Mischer/Pumpen ---
    "M_nvoPump": "Heizkreispumpe Leistung",
    "M_nvoValve": "Mischer Stellung",
    "M_nviTVsoll": "Vorlauftemperatur Sollwert (Mischerkreis)",
    "M_nviTVist": "Vorlauftemperatur Istwert (Mischerkreis)",
    "LX_nvoPump": "Heizkreispumpe Leistung",
    "LX_nvoValve": "Mischer Stellung",
}


def readable_nv_name(raw_name: str) -> str:
    """Lesbaren Anzeigenamen fuer eine NV-Variable liefern.

    Fallback ist der unveraenderte technische Rohname, falls kein
    Eintrag in der Whitelist existiert. Array-Suffixe wie "[0]"
    werden vor dem Lookup entfernt, damit z.B. "LX_nvoPump[0]" auch
    den Eintrag fuer "LX_nvoPump" findet.
    """

    base_name = raw_name.split("[")[0]

    return READABLE_NV_NAMES.get(
        base_name,
        raw_name,
    )