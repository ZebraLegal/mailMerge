from PIL import ImageDraw
import streamlit as st
st.set_page_config(layout="wide")
import pdfplumber
# NAVIGATIE-LOGICA: twee pagina’s
if 'page' not in st.session_state:
    st.session_state['page'] = 'upload'

def to_upload():
    st.session_state['page'] = 'upload'

def to_results():
    st.session_state['page'] = 'results'
import io
import re
import pandas as pd

def split_address_fallback(adres):
    if not adres:
        return None, None, None, None, None, None, None, None
    # Probeer NL, BE, UK, FR, DE, US; anders alles als onherkend_adres
    straat, huisnummer, postcode, postcode_cijfers, postcode_letters, plaats, adres_toevoeging, onherkend_adres = None, None, None, None, None, None, None, None
    import re

    # Nederlands (Singel 50 L, 6th floor, 1015AB Amsterdam)
    if adres and "," in adres:
        delen = [x.strip() for x in adres.split(",")]
        if len(delen) == 2:
            straat_huis, rest = delen
            toevoeging = ""
        elif len(delen) > 2:
            straat_huis = delen[0]
            toevoeging = ", ".join(delen[1:-1])  # alles tussen 1e en laatste komma
            rest = delen[-1]
        else:
            straat_huis = adres
            toevoeging = ""
            rest = ""
        # Vind huisnummer in straatdeel
        match = re.match(r"([^\d]+)\s*([\d]+[^\s,]*)", straat_huis)
        if match:
            straat = match.group(1).strip()
            huisnummer = match.group(2).strip()
        else:
            straat = straat_huis
            huisnummer = None

        adres_toevoeging = toevoeging if toevoeging else None

        # Zoek postcode in rest
        pc_match = re.search(r"(\d{4})\s?([A-Z]{2})\s+(.+)", rest)
        if pc_match:
            postcode_cijfers = pc_match.group(1)
            postcode_letters = pc_match.group(2)
            postcode = f"{postcode_cijfers} {postcode_letters}"
            plaats = pc_match.group(3).strip()
        else:
            postcode = None
            postcode_cijfers = None
            postcode_letters = None
            plaats = rest

        return straat, huisnummer, postcode, postcode_cijfers, postcode_letters, plaats, adres_toevoeging, None

    # Belgisch (Rue de la Loi 16, 1000 Brussels)
    be_match = re.match(r"(.+?)\s+(\d+),\s*(\d{4})\s+(.+)", adres)
    if be_match:
        straat = be_match.group(1).strip()
        huisnummer = be_match.group(2).strip()
        postcode = be_match.group(3).strip()
        plaats = be_match.group(4).strip()
        return straat, huisnummer, postcode, None, None, plaats, None, None

    # Engels (10 Downing St, SW1A 2AA London)
    uk_match = re.match(r"(.+?)\s*,\s*([A-Z0-9 ]{5,8})\s+(.+)", adres)
    if uk_match:
        straat_huis = uk_match.group(1).strip()
        postcode = uk_match.group(2).replace(" ", "")
        plaats = uk_match.group(3).strip()
        num_match = re.match(r"(.+?)\s+(\d+\w*)$", straat_huis)
        if num_match:
            straat = num_match.group(1).strip()
            huisnummer = num_match.group(2).strip()
        else:
            straat = straat_huis
            huisnummer = None
        return straat, huisnummer, postcode, None, None, plaats, None, None

    # Frans (16 Avenue des Champs-Élysées, 75008 Paris)
    fr_match = re.match(r"(.+?)\s+(\d+),\s*(\d{5})\s+(.+)", adres)
    if fr_match:
        straat = fr_match.group(1).strip()
        huisnummer = fr_match.group(2).strip()
        postcode = fr_match.group(3).strip()
        plaats = fr_match.group(4).strip()
        return straat, huisnummer, postcode, None, None, plaats, None, None

    # Duits (Unter den Linden 17, 10117 Berlin)
    de_match = re.match(r"(.+?)\s+(\d+[a-zA-Z]?),\s*(\d{5})\s+(.+)", adres)
    if de_match:
        straat = de_match.group(1).strip()
        huisnummer = de_match.group(2).strip()
        postcode = de_match.group(3).strip()
        plaats = de_match.group(4).strip()
        return straat, huisnummer, postcode, None, None, plaats, None, None

    # Amerikaans (1600 Pennsylvania Ave NW, Washington, DC 20500)
    us_match = re.match(r"(.+?),\s*(.+?),\s*([A-Z]{2})\s+(\d{5})(-\d{4})?$", adres)
    if us_match:
        straat_huis = us_match.group(1).strip()
        plaats = us_match.group(2).strip()
        num_match = re.match(r"(.+?)\s+(\d+\w*)$", straat_huis)
        if num_match:
            straat = num_match.group(1).strip()
            huisnummer = num_match.group(2).strip()
        else:
            straat = straat_huis
            huisnummer = None
        postcode = us_match.group(4).strip()
        plaats = f"{plaats}, {us_match.group(3)}"  # bv. "Washington, DC"
        return straat, huisnummer, postcode, None, None, plaats, None, None

    # Geen herkenning
    onherkend_adres = adres
    return None, None, None, None, None, None, None, onherkend_adres

# Definitie van gewenste volgorde en labels
import json
import pandas as pd

veldvolgorde = [
    ('statutaire_naam', 'Statutaire naam'),
    ('statutaire_zetel', 'Statutaire zetel'),
    ('straat', 'Straatnaam'),
    ('huisnummer', 'Huisnummer'),
    ('adres_toevoeging', 'Toevoeging'),
    ('postcode', 'Postcode'),
    ('plaats', 'Plaats'),
    ('kvk_nummer', 'KvK-nummer'),
    ('bestuurders', 'Bestuurders'),
    ('handelsnamen', 'Handelsnaam/namen'),
    ('sbi_code', 'SBI-code'),
]

def extract_kvk_data(pdf_path):
    # Open het PDF en lees de tekst
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    
    # Zoek de kerngegevens met RegEx
    data = {}
    patterns = {
        'kvk_nummer': r'KvK-nummer\s+(\d+)',
        'statutaire_naam': r'Statutaire naam\s+(.+)',
        'adres': r'Bezoekadres\s+([^\n]+)',
        'rsin': r'RSIN\s+(\d+)',
        'rechtsvorm': r'Rechtsvorm\s+(.+)',
        'statutaire_zetel': r'Statutaire zetel\s+(.+)',
        'oprichtingsdatum': r'Datum akte van oprichting\s+(\d{2}-\d{2}-\d{4})',
        'geplaatst_kapitaal': r'Geplaatst kapitaal\s+EUR\s+([\d\.,]+)',
        'handelsnamen': r'Handelsnamen\s+([^\n]+)',
        'sbi_code': r'SBI-code:\s+([^\n]+)',
    }
    for key, pat in patterns.items():
        match = re.search(pat, text)
        if match:
            data[key] = match.group(1).strip()
        else:
            data[key] = None  # Kan later eventueel loggen

    # Bestuurders apart zoeken (voorbeeld voor 1 natuurlijke persoon)
    bestuurders = []
    bestuurders_blocks = re.findall(r'Naam ([^\n]+)\nGeboortedatum ([^\n]+)\nDatum in functie ([^\n]+)\nBevoegdheid ([^\n]+)', text)
    for naam, gebdat, datum_func, bevoegd in bestuurders_blocks:
        bestuurders.append({
            'naam': naam.strip(),
            'geboortedatum': gebdat.strip(),
            'datum_in_functie': datum_func.strip(),
            'bevoegdheid': bevoegd.strip()
        })
    data['bestuurders'] = bestuurders

    return data


# Functie om data te extraheren uit tekst (voor Streamlit upload)
def extract_kvk_data_from_text(text):
    # Zoek de kerngegevens met RegEx
    data = {}
    patterns = {
        'kvk_nummer': r'KvK-nummer\s+(\d+)',
        'statutaire_naam': r'Statutaire naam\s+(.+)',
        'adres': r'Bezoekadres\s+([^\n]+)',
        'rsin': r'RSIN\s+(\d+)',
        'rechtsvorm': r'Rechtsvorm\s+(.+)',
        'statutaire_zetel': r'Statutaire zetel\s+(.+)',
        'oprichtingsdatum': r'Datum akte van oprichting\s+(\d{2}-\d{2}-\d{4})',
        'geplaatst_kapitaal': r'Geplaatst kapitaal\s+EUR\s+([\d\.,]+)',
        'handelsnamen': r'Handelsnamen\s+([^\n]+)',
        'sbi_code': r'SBI-code:\s+([^\n]+)',
    }
    for key, pat in patterns.items():
        match = re.search(pat, text)
        data[key] = match.group(1).strip() if match else None

    # Bestuurders zoeken (ook meerdere, flexibeler)
    bestuurders = []
    # Vind blok 'Bestuurder' of 'Bestuurders'
    bestuurders_start = text.find("Bestuurder")
    if bestuurders_start == -1:
        bestuurders_start = text.find("Bestuurders")
    if bestuurders_start != -1:
        # Neem alleen tekst vanaf de eerste bestuurder
        bestuurders_txt = text[bestuurders_start:]
        # Splits op elk volgend 'Naam ' (nieuw blok)
        raw_bestuurders = re.split(r"\nNaam ", bestuurders_txt)
        for i, raw in enumerate(raw_bestuurders):
            # De eerste split kan vóór het eerste 'Naam ' zitten
            if i == 0 and not raw.strip().startswith("Naam "):
                if not raw.strip().startswith("Naam"):
                    continue  # skip header
            else:
                raw = "Naam " + raw
            bestuurder = {}
            # Naam
            match = re.search(r"Naam ([^\n]+)", raw)
            if match:
                bestuurder['naam'] = match.group(1).strip()
            # Geboortedatum en -plaats
            match = re.search(r"Geboortedatum en -plaats ([^\n]+)", raw)
            if match:
                bestuurder['geboortedatum_en_plaats'] = match.group(1).strip()
            else:
                match = re.search(r"Geboortedatum ([^\n]+)", raw)
                if match:
                    bestuurder['geboortedatum'] = match.group(1).strip()
            # Bezoekadres
            match = re.search(r"Bezoekadres ([^\n]+)", raw)
            if match:
                bestuurder['bezoekadres'] = match.group(1).strip()
            # Ingeschreven onder KvK-nummer
            match = re.search(r"Ingeschreven onder KvK-nummer (\d+)", raw)
            if match:
                bestuurder['kvk_nummer'] = match.group(1).strip()
            # Datum in functie
            match = re.search(r"Datum in functie ([^\n]+)", raw)
            if match:
                bestuurder['datum_in_functie'] = match.group(1).strip()
            # Bevoegdheid
            match = re.search(r"Bevoegdheid ([^\n]+)", raw)
            if match:
                bestuurder['bevoegdheid'] = match.group(1).strip()
            if 'naam' in bestuurder:
                bestuurders.append(bestuurder)
    data['bestuurders'] = bestuurders

    # Voeg voor overzicht ook de eerste bestuurder als losse velden toe (optioneel)
    if bestuurders:
        eerste = bestuurders[0]
        data['bestuurder_naam'] = eerste.get('naam')
        data['bestuurder_geboortedatum'] = eerste.get('geboortedatum_en_plaats') or eerste.get('geboortedatum')
        data['bestuurder_datum_in_functie'] = eerste.get('datum_in_functie')
        data['bestuurder_bevoegdheid'] = eerste.get('bevoegdheid')
    else:
        data['bestuurder_naam'] = data['bestuurder_geboortedatum'] = None
        data['bestuurder_datum_in_functie'] = data['bestuurder_bevoegdheid'] = None

    return data


# --- PAGINA-NAVIGATIE EN UPLOAD ---
if st.session_state['page'] == 'upload':
    st.title("KvK Uittreksel Extractor - Upload")
    st.write("Upload één of meerdere KvK-uittreksels (PDF). Klik op **Verwerk** om door te gaan.")
    uploaded_files = st.file_uploader("Upload PDF-bestanden", type="pdf", accept_multiple_files=True)
    if st.button("Verwerk"):
        if uploaded_files:
            st.session_state['uploaded_files'] = uploaded_files
            to_results()
        else:
            st.warning("Upload eerst minimaal één PDF.")
    st.stop()
# Vanaf hier: pagina ‘results’
uploaded_files = st.session_state.get('uploaded_files', [])
col_back = st.button("← Terug naar Upload", on_click=to_upload)
st.title("KvK Uittreksel Extractor - Resultaten")

if uploaded_files:
    results = []
    for uploaded_file in uploaded_files:
        # Open PDF met pdfplumber en haal tekst uit alle pagina's
        pdf_file = uploaded_file
        pdf_file.seek(0)
        with pdfplumber.open(pdf_file) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        data = extract_kvk_data_from_text(text)
        data["bestand"] = uploaded_file.name
        # Splits adres in losse delen
        straat, huisnummer, postcode, postcode_cijfers, postcode_letters, plaats, adres_toevoeging, onherkend_adres = split_address_fallback(data.get('adres'))
        data['straat'] = straat
        data['huisnummer'] = huisnummer
        data['postcode'] = postcode
        data['postcode_cijfers'] = postcode_cijfers
        data['postcode_letters'] = postcode_letters
        data['plaats'] = plaats
        data['adres_toevoeging'] = adres_toevoeging
        data['onherkend_adres'] = onherkend_adres
        results.append(data)

    df = pd.DataFrame(results)

    # Bouw tabel met labels als rijen, bestandsnamen als kolommen
    table = {}
    for veld, label in veldvolgorde:
        table[label] = []

    for i, row in df.iterrows():
        for veld, label in veldvolgorde:
            val = row.get(veld)
            if veld == 'bestuurders' and val:
                # Toon bestuurders als nette lijst
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                if isinstance(val, list):
                    val_txt = ""
                    for idx, bestuurder in enumerate(val, 1):
                        naam = bestuurder.get('naam', '')
                        bevoegdheid = bestuurder.get('bevoegdheid', '')
                        val_txt += f"- {naam}" + (f" ({bevoegdheid})" if bevoegdheid else "") + "\n"
                    val = val_txt.strip()
            if veld == 'adres_toevoeging' and not val:
                val = ""  # Niet tonen als None
            table[label].append(val if val is not None else "")

    # Zet kolomlabels op basis van statutaire naam, fallback naar bestandsnaam
    statutaire_namen = df['statutaire_naam'].fillna(df['bestand']).tolist()
    table_df = pd.DataFrame(table)
    table_df = table_df.T
    table_df['Veld'] = [label for _, label in veldvolgorde]
    table_df = table_df.reset_index(drop=True)
    cols = list(table_df.columns)
    cols = [cols[-1]] + cols[:-1]
    table_df = table_df[cols]
    for i, naam in enumerate(statutaire_namen):
        table_df.columns.values[i+1] = naam

    # === PATCH: Dropdown bovenaan, knoppen, filter tabel ===
    colnames = table_df.columns[1:]
    st.divider()
    selected_col = st.selectbox(
        "Selecteer uittreksel voor preview en details:",
        options=range(1, len(table_df.columns)),
        format_func=lambda i: table_df.columns[i],
        index=0,
        key="selectbox_col"
    )
    st.divider()
    naam = table_df.columns[selected_col]
    bestand = None
    if naam in df['statutaire_naam'].tolist():
        bestand = df.loc[df['statutaire_naam'] == naam, 'bestand'].values[0]
    else:
        bestand = naam  # fallback

    idx_pdf = [i for i, f in enumerate(uploaded_files) if f.name == bestand]

    # Filter tabel tot alleen geselecteerd uittreksel + veldkolom
    single_col_df = table_df[['Veld', naam]].copy()

    # Knoppen sectie boven tabel & preview
    st.divider()
    btn_col_form, btn_col_preview, btn_col_empty = st.columns([8, 9, 7])
    with btn_col_form:
        if st.button("Opslaan naar Excel", key=f"download_{bestand}"):
            output = io.BytesIO()
            edited_df = single_col_df
            edited_df.to_excel(output, index=False)
            st.download_button(
                "Download als Excel",
                data=output.getvalue(),
                file_name=f"{naam}_uittreksel.xlsx"
            )
    with btn_col_preview:
        page_key = f"page_{bestand}"
        col_prev, col_next = st.columns([1, 1])
        with col_prev:
            if idx_pdf and st.button("← vorige", key=f"prev_{bestand}") and st.session_state.get(page_key, 1) > 1:
                st.session_state[page_key] -= 1
        with col_next:
            if idx_pdf:
                # totaal_pages wordt bepaald in preview, fallback op 1 als onbekend
                totaal_pages_local = locals().get('totaal_pages', 1)
                if st.button("volgende →", key=f"next_{bestand}") and st.session_state.get(page_key, 1) < totaal_pages_local:
                    st.session_state[page_key] += 1
    # btn_col_empty blijft leeg om ruimte op te vullen
    st.divider()

    col_form, col_preview, col_empty = st.columns([8, 9, 7])

    with col_form:
        # Maak een form aan waarin gebruiker elke gevonden waarde kan bewerken
        single_col_df = table_df[['Veld', naam]].copy()
        form_key = f"form_{bestand}"
        with st.form(key=form_key):
            updated_values = {}
            for idx, row in single_col_df.iterrows():
                label = row['Veld']
                value = row[naam]
                if "\n" in str(value):
                    updated = st.text_area(label, value=value, key=f"{form_key}_{idx}")
                else:
                    updated = st.text_input(label, value=value, key=f"{form_key}_{idx}")
                updated_values[label] = updated
            submitted = st.form_submit_button("Bevestig wijzigingen")
            if submitted:
                for i, label in enumerate(single_col_df['Veld']):
                    single_col_df.at[i, naam] = updated_values.get(label, "")
                st.session_state[f"edited_{bestand}"] = single_col_df.copy()

    with col_preview:
        # Toon PDF-preview zonder kader
        if idx_pdf:
            try:
                pdf_file = uploaded_files[idx_pdf[0]]
                pdf_file.seek(0)
                with pdfplumber.open(pdf_file) as pdf:
                    totaal_pages = len(pdf.pages)
                    page_key = f"page_{bestand}"
                    if page_key not in st.session_state:
                        st.session_state[page_key] = 1
                    pagina_index = st.session_state[page_key]
                    page = pdf.pages[pagina_index - 1]
                    img_obj = page.to_image(resolution=150)
                    pil_img = img_obj.original
                    st.image(
                        pil_img,
                        caption=f"(pagina {pagina_index} / {totaal_pages})",
                        use_container_width=True
                    )
            except Exception as e:
                st.warning(f"Kon '{bestand}' niet openen: {e}")
        else:
            st.info("Geen bijbehorend PDF-bestand gevonden.")
