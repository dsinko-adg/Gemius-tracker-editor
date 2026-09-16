import streamlit as st
import zipfile
import io
import re
import pandas as pd

st.set_page_config(page_title="Gemius Tracker Batch Editor", layout="wide")

st.title("Gemius Tracker Batch Editor")
st.markdown("Upload a ZIP file containing folders with `.txt` tracker files. The app will extract the impression and click URLs into separate columns.")

uploaded_file = st.file_uploader("Upload ZIP file", type=["zip"])

if uploaded_file is not None:
    tracker_data = []
    
    with zipfile.ZipFile(uploaded_file, 'r') as z:
        for filename in z.namelist():
            if filename.endswith(".txt"):
                try:
                    content = z.read(filename).decode('utf-8', errors='ignore')
                    
                    imp_url = ""
                    click_url = ""
                    
                    lines = content.splitlines()
                    for line in lines:
                        line = line.strip()
                        
                        # Impression tracker: extract middle part of <IMG SRC="..." />
                        if '<IMG' in line.upper() and 'SRC=' in line.upper():
                            # Regex to capture everything between the quotes of SRC=" "
                            match = re.search(r'SRC=["\'](.*?)["\']', line, re.IGNORECASE)
                            if match:
                                imp_url = match.group(1)
                                
                        # Click tracker: a line starting with http(s) that is not part of an IMG tag 
                        # (usually right after the click comment)
                        elif line.startswith('http') and '<IMG' not in line.upper():
                            click_url = line
                    
                    if imp_url or click_url:
                        tracker_data.append({
                            "File Path": filename,
                            "Impression Tracker": imp_url,
                            "Click Tracker": click_url
                        })
                except Exception as e:
                    st.error(f"Could not read {filename}: {e}")
                    
    if not tracker_data:
        st.warning("No Gemius trackers found in the provided ZIP file.")
    else:
        df = pd.DataFrame(tracker_data)
        
        # Fill any missing values with empty strings so text replacement doesn't error out
        df['Impression Tracker'] = df['Impression Tracker'].fillna('')
        df['Click Tracker'] = df['Click Tracker'].fillna('')

        st.subheader("Edit Trackers")
        
        st.markdown("### 1. DV360 Macro Toggle")
        apply_dv360 = st.checkbox("Replace `gdpr=0/gdpr_consent=` with DV360 Macros")
        
        st.markdown("### 2. Custom Find & Replace (Optional)")
        col1, col2 = st.columns(2)
        with col1:
            find_text = st.text_input("Find text:")
        with col2:
            replace_text = st.text_input("Replace with:")

        modified_df = df.copy()

        # Apply DV360 Logic
        if apply_dv360:
            target_str = "gdpr=0/gdpr_consent="
            replacement_str = "gdpr=${GDPR}/gdpr_consent=${GDPR_CONSENT_328}"
            
            modified_df['Impression Tracker'] = modified_df['Impression Tracker'].str.replace(target_str, replacement_str, regex=False)
            modified_df['Click Tracker'] = modified_df['Click Tracker'].str.replace(target_str, replacement_str, regex=False)

        # Apply Custom Find/Replace Logic
        if find_text:
            modified_df['Impression Tracker'] = modified_df['Impression Tracker'].str.replace(find_text, replace_text, regex=False)
            modified_df['Click Tracker'] = modified_df['Click Tracker'].str.replace(find_text, replace_text, regex=False)

        st.markdown(f"**Found {len(modified_df)} tracker files.** Preview:")
        st.dataframe(modified_df, use_container_width=True)

        # We use an in-memory buffer to generate the Excel file so the user can download it
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            modified_df.to_excel(writer, index=False, sheet_name='Trackers')
            
            # Optional: auto-adjust column widths for better readability in Excel
            worksheet = writer.sheets['Trackers']
            for col_idx, col in enumerate(modified_df.columns, 1):
                worksheet.column_dimensions[chr(64 + col_idx)].width = 50 

        st.download_button(
            label="⬇️ Download All Trackers as Excel",
            data=excel_buffer.getvalue(),
            file_name="gemius_trackers_modified.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
