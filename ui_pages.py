"""
UI pages module for mail merge application.
Contains Streamlit page components and UI logic.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

from template_processor import extract_placeholders, validate_template_placeholders
from data_handler import (
    normalize_column_names, create_field_mapping, create_context_from_row,
    calculate_totals, reshape_wide_to_rows
)
from document_generator import (
    generate_empty_data_file, open_file_in_system, render_template_preview,
    generate_single_document, generate_documents_batch, validate_template_before_generation
)


def render_template_upload_page():
    """Render the template upload page (Page 1)."""
    st.title("📄 Word Template Upload")
    
    uploaded_template = st.file_uploader("Upload een Word-bestand (.docx) als template:", type=["docx"])
    
    if uploaded_template:
        curly, square = extract_placeholders(uploaded_template)
        
        # Validate template placeholders
        validation_results = validate_template_placeholders(curly)
        
        if validation_results['invalid']:
            st.error(
                "❌ Ongeldige variabelenamen gevonden:\n\n- " +
                "\n- ".join(validation_results['invalid']) +
                "\n\n🔧 Gebruik alleen letters, cijfers, underscores en optioneel punt-notatie (bv. `row.Naam`)."
            )
        
        if validation_results['control_in_print']:
            st.error(
                "❌ Controle-structuren (for/if) gevonden binnen `{{ ... }}`:\n\n- " +
                "\n- ".join(validation_results['control_in_print']) +
                "\n\n🔧 Gebruik `{% ... %}` voor for/if/else/endfor/endif in plaats van `{{ ... }}`."
            )
        
        if validation_results['unclosed']:
            st.error(
                "⚠️ Mogelijk onvolledige of losse placeholders:\n\n- " +
                "\n- ".join(validation_results['unclosed']) +
                "\n\n🔧 Controleer of alle Jinja-tags correct zijn geopend en gesloten."
            )
        
        if any(validation_results.values()):
            st.stop()
        
        # Display found fields
        st.subheader("🔍 Gevonden velden tussen accolades")
        if curly:
            st.table(pd.DataFrame(curly, columns=["Veldnaam"]))
        else:
            st.info("Geen velden tussen accolades gevonden.")
        
        st.subheader("🟦 Gevonden velden tussen blokhaken")
        if square:
            df = pd.DataFrame({"Veldnaam": square, "Opnemen als veld?": [False]*len(square)})
            edited = st.data_editor(df, use_container_width=True, num_rows="fixed")
            st.session_state.square_fields = edited
        else:
            st.info("Geen velden tussen blokhaken gevonden.")
        
        st.markdown("_Of genereer een leeg databestand op basis van deze velden._")
        
        if st.button("Genereer leeg databestand (.xlsx)"):
            excel_path = generate_empty_data_file(curly)
            open_file_in_system(excel_path)
            st.success("Een leeg databestand is geopend in Excel. Vul de velden aan, sla het bestand op en upload het op de volgende pagina.")
        
        if st.button("Maak één document (velden invullen in browser)"):
            st.session_state.single_form_fields = curly
            st.session_state.uploaded_template_single = uploaded_template
            st.session_state.page = "single"
            st.rerun()
        
        if st.button("Volgende stap: keuze data-file ➡️"):
            st.session_state.uploaded_template = uploaded_template
            st.session_state.curly_fields = curly
            st.session_state.page = 2
            st.rerun()


def render_data_upload_page():
    """Render the data upload page (Page 2)."""
    st.title("📊 Upload een data-bestand")
    
    uploaded_data = st.file_uploader("Upload een Excel- of CSV-bestand:", type=["xlsx", "csv"])
    st.markdown("_Of genereer een leeg databestand op basis van deze velden op de vorige pagina._")
    
    if uploaded_data:
        if uploaded_data.name.endswith("csv"):
            df_data = pd.read_csv(uploaded_data, dtype=str)
        else:
            df_data = pd.read_excel(uploaded_data, dtype=str)
        
        # Normalize column names
        df_data = normalize_column_names(df_data)
        headers = df_data.columns.tolist()
        st.session_state['headers'] = headers
        
        word_fields = st.session_state.curly_fields
        
        # Create field mapping
        mapping_data = create_field_mapping(word_fields, headers, df_data)
        
        st.subheader("🧠 Automatische veldkoppeling")
        st.table(pd.DataFrame(mapping_data, columns=["Word-veld", "Voorstel match", "Voorbeeldwaarde"]))
        
        # Create mapping tool with example values
        col_examples = {h: str(df_data[h].iloc[0]) if not df_data.empty else "" for h in headers}
        dropdown_options = [""] + [f"{h} ({col_examples[h]})" for h in headers]
        display_to_header = {f"{h} ({col_examples[h]})": h for h in headers}
        
        def match_to_display(match):
            if match in headers:
                return f"{match} ({col_examples[match]})"
            return ""
        
        mapping_df = pd.DataFrame(mapping_data, columns=["Word-veld", "Voorstel match", "Voorbeeldwaarde"])
        mapping_df["Gekozen kolom"] = mapping_df["Voorstel match"].apply(match_to_display)
        
        st.markdown("**Je ziet nu naast elke kolom in de dropdown ook de eerste waarde uit die kolom.**")
        
        # Data editor with custom options
        edited_mapping = st.data_editor(
            mapping_df,
            column_config={
                "Gekozen kolom": st.column_config.SelectboxColumn(
                    "Kies kolom", options=dropdown_options
                )
            },
            use_container_width=True
        )
        
        # Save mapping
        st.session_state['field_mapping'] = {
            row["Word-veld"]: display_to_header.get(row["Gekozen kolom"], "")
            for _, row in edited_mapping.iterrows()
        }
        
        st.info("Indien de automatische match niet klopt, kun je hierboven handmatig de juiste kolom kiezen.")
        
        # Show extra columns
        from template_processor import normalize
        extra_cols = [h for h in headers if normalize(h) not in [normalize(f) for f in word_fields]]
        if extra_cols:
            st.subheader("⚠️ Extra kolommen in Excel")
            st.write("Deze kolommen komen niet voor in het Word-template. Wil je deze toevoegen?")
            st.write(extra_cols)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ Terug naar template-upload"):
                st.session_state.page = 1
                st.rerun()
        with col2:
            if uploaded_data and st.button("Volgende stap: uitvoerinstellingen ➡️"):
                st.session_state.df_data = df_data
                st.session_state.headers = headers
                st.session_state.page = 3
                st.rerun()


def render_preview_page():
    """Render the template preview page (Page 3)."""
    st.title("👀 Template Preview")
    
    uploaded_template = st.session_state.get("uploaded_template")
    df_data = st.session_state.get("df_data")
    
    if not uploaded_template:
        st.warning("Upload eerst een template op pagina 1.")
        st.stop()
    if df_data is None or df_data.empty:
        st.warning("Upload eerst een data-bestand op pagina 2.")
        st.stop()
    
    st.subheader("Template Preview")
    
    # Validate placeholders
    try:
        curly_fields, _square_fields = extract_placeholders(uploaded_template)
    except Exception:
        curly_fields = []
    
    from template_processor import is_valid_jinja_var
    invalid_placeholders = [f for f in curly_fields if not is_valid_jinja_var(f)]
    
    if invalid_placeholders:
        st.error(
            "❌ Je template bevat ongeldige Jinja-plaats-houders (bijv. spaties of vreemde tekens):\n\n- " +
            "\n- ".join(invalid_placeholders) +
            "\n\n🔧 Oplossing: vervang spaties en speciale tekens door underscores. Voorbeeld: `{{ Voornaam Klant }}` → `{{ Voornaam_Klant }}`."
        )
        st.stop()
    
    # Prepare context from first data row
    sample_row = df_data.iloc[0]
    orig_row = {str(k): v for k, v in sample_row.items()}
    context = {}
    
    for key, value in orig_row.items():
        context[key] = value
        context[f"row.{key}"] = value
    
    # Add rows for template loops
    context["rows_one"] = reshape_wide_to_rows(orig_row)
    rows_all = df_data.to_dict("records")
    context["rows_all"] = rows_all
    context["rows"] = context["rows_all"]  # Backward compatibility
    
    # Render preview
    preview_text = render_template_preview(uploaded_template, context)
    st.write(preview_text)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Terug naar data-upload"):
            st.session_state.page = 2
            st.rerun()
    with col2:
        if st.button("Volgende stap: uitvoerinstellingen ➡️"):
            st.session_state.page = 4
            st.rerun()


def render_output_settings_page():
    """Render the output settings page (Page 4)."""
    st.title("📁 Uitvoerinstellingen")
    
    # Language selection
    lang_default = st.session_state.get("target_lang", "UK")
    target_lang = st.selectbox("Taal voor datumopmaak", options=["UK", "US", "NL"], index=["UK","US","NL"].index(lang_default))
    st.session_state["target_lang"] = target_lang
    
    df_data = st.session_state.get("df_data")
    headers = st.session_state.get("headers", [])
    uploaded_template = st.session_state.get("uploaded_template")
    
    # Output directory and filename settings
    from os.path import expanduser
    import os
    
    # Use different base directory for cloud vs local environments
    if (
        os.getenv('STREAMLIT_CLOUD') or 
        os.getenv('STREAMLIT_SERVER_HEADLESS') or
        '/home/appuser' in str(Path.cwd()) or
        'streamlit.app' in os.getenv('STREAMLIT_SERVER_ADDRESS', '')
    ):
        # Cloud environment - use temp directory
        default_base = Path("/tmp/mailmerge_output")
    else:
        # Local environment - use Desktop
        default_base = Path(expanduser("~/Desktop"))
    
    prefix = st.text_input("Voorlooptekst voor bestandsnaam (bv. 'Angel Subscription Letter'):", value="Document")
    output_dir = default_base / prefix
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filename format settings
    primary_column = st.selectbox("Gebruik deze kolom voor personalisatie:", options=headers)
    remaining_columns = [col for col in headers if col != primary_column]
    secondary_column = st.selectbox("Als deze kolom leeg is, gebruik dan:", options=remaining_columns)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Terug naar voorbeeldweergave"):
            st.session_state.page = 3
            st.rerun()
    with col2:
        if st.button("📄 Genereer documenten"):
            st.caption("📁 De map met gegenereerde documenten wordt automatisch geopend na afloop.")
            
            if uploaded_template:
                # Validate template before generation
                validation_errors = validate_template_before_generation(uploaded_template)
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                    st.stop()
                
                # Generate documents
                documents_generated, generated_files = generate_documents_batch(
                    uploaded_template,
                    df_data,
                    st.session_state.get('field_mapping', {}),
                    st.session_state.get("square_fields", pd.DataFrame()).to_dict('records'),
                    output_dir,
                    prefix,
                    primary_column,
                    secondary_column,
                    target_lang
                )
                
                st.success(f"{documents_generated} documenten succesvol gegenereerd!")
                
                # Show download options for cloud environments
                import os
                # Check multiple indicators for cloud environment
                is_cloud = (
                    os.getenv('STREAMLIT_CLOUD') or 
                    os.getenv('STREAMLIT_SERVER_HEADLESS') or
                    '/home/appuser' in str(output_dir) or
                    '/tmp' in str(output_dir) or
                    'streamlit.app' in os.getenv('STREAMLIT_SERVER_ADDRESS', '')
                )
                
                if is_cloud and generated_files:
                    st.subheader("📥 Download gegenereerde documenten")
                    st.info("Documenten zijn gegenereerd in de cloud. Download ze hieronder:")
                    
                    # Create a zip file with all documents
                    import zipfile
                    import io
                    
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for file_path in generated_files:
                            if file_path.exists():
                                zip_file.write(file_path, file_path.name)
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label=f"📦 Download alle {documents_generated} documenten (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"{prefix}_documents_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.zip",
                        mime="application/zip"
                    )
                    
                    # Individual download buttons
                    st.subheader("📄 Individuele downloads")
                    for i, file_path in enumerate(generated_files[:5]):  # Show first 5
                        if file_path.exists():
                            with open(file_path, 'rb') as f:
                                file_data = f.read()
                            st.download_button(
                                label=f"📄 {file_path.name}",
                                data=file_data,
                                file_name=file_path.name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"download_{i}"
                            )
                    
                    if len(generated_files) > 5:
                        st.info(f"... en {len(generated_files) - 5} meer documenten (gebruik de ZIP download)")
                else:
                    st.info(f"Documenten opgeslagen in: {output_dir}")
                
                # Open output directory (only in local environments)
                if not is_cloud:
                    try:
                        from streamlit import runtime
                        is_local = runtime.exists()
                        if is_local:
                            open_file_in_system(str(output_dir))
                    except Exception:
                        pass


def render_single_document_page():
    """Render the single document form page."""
    st.title("🔑 Velden invullen voor single-use document")
    fields = st.session_state.get("single_form_fields", [])
    uploaded_template = st.session_state.get("uploaded_template_single")
    form_data = {}
    
    st.markdown("Vul alle velden in en download direct je document.")
    
    with st.form("doc_form"):
        for field in fields:
            form_data[field] = st.text_input(f"{field}")
        submitted = st.form_submit_button("Genereer document")
    
    if submitted:
        output = generate_single_document(uploaded_template, form_data)
        st.success("Document gegenereerd! Download hieronder.")
        st.download_button(
            "⬇️ Download gegenereerd document",
            output.getvalue(),
            file_name="Document.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    if st.button("⬅️ Terug naar start"):
        st.session_state.page = 1
        st.rerun()
