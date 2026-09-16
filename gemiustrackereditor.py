import streamlit as st
import zipfile
import io
import re
import os

st.set_page_config(page_title="Gemius Tracker Batch Editor", layout="wide")

def main():
    st.title("Gemius Tracker Batch Editor")
    st.write("Upload a ZIP file containing your folder structure. The app will find all `.txt` files (assumed to contain trackers), let you batch edit them, and download the updated ZIP.")

    uploaded_file = st.file_uploader("Upload ZIP file", type="zip")

    if uploaded_file is not None:
        try:
            # Read the zip file into memory
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                # Get a list of all files in the zip
                file_list = zip_ref.namelist()
                
                # Filter for txt files
                txt_files = [f for f in file_list if f.endswith('.txt')]
                
                if not txt_files:
                    st.warning("No .txt files found in the uploaded ZIP.")
                    return

                # Store the original content of all files so we can reconstruct the zip later
                original_files_content = {}
                for file_name in file_list:
                     original_files_content[file_name] = zip_ref.read(file_name)

            st.success(f"Found {len(txt_files)} `.txt` files.")
            
            # Initialize session state for tracker content if not already there
            if 'tracker_data' not in st.session_state or st.session_state.get('last_uploaded') != uploaded_file.name:
                st.session_state.tracker_data = {}
                for txt_file in txt_files:
                    try:
                        content = original_files_content[txt_file].decode('utf-8')
                        st.session_state.tracker_data[txt_file] = content
                    except UnicodeDecodeError:
                        st.session_state.tracker_data[txt_file] = original_files_content[txt_file].decode('latin-1', errors='replace')
                st.session_state.last_uploaded = uploaded_file.name

            st.header("Batch Editing Tools")
            
            col1, col2 = st.columns(2)
            with col1:
                find_text = st.text_input("Find macro/text:", placeholder="e.g., [CACHEBUSTER]")
            with col2:
                replace_text = st.text_input("Replace with:", placeholder="e.g., %%CACHEBUSTER%%")

            if st.button("Apply Batch Replace"):
                if find_text:
                    replacements_made = 0
                    for filename, content in st.session_state.tracker_data.items():
                        if find_text in content:
                            st.session_state.tracker_data[filename] = content.replace(find_text, replace_text)
                            replacements_made += 1
                    
                    if replacements_made > 0:
                        st.success(f"Successfully replaced '{find_text}' with '{replace_text}' in {replacements_made} files.")
                        st.rerun()
                    else:
                        st.info(f"Text '{find_text}' not found in any tracker files.")
                else:
                    st.warning("Please enter text to find.")

            st.header("Review and Manual Edit")
            st.write("You can review and edit individual files below.")
            
            # Create a dictionary to hold the potentially manually edited content
            edited_data = {}
            
            for filename, content in st.session_state.tracker_data.items():
                with st.expander(f"File: {filename}"):
                    # Allow manual editing of the file content
                    edited_content = st.text_area(
                        "Tracker Content:", 
                        value=content, 
                        height=150, 
                        key=f"text_area_{filename}"
                    )
                    edited_data[filename] = edited_content
                    
                    # Update session state immediately if manual edit occurs
                    if edited_content != content:
                         st.session_state.tracker_data[filename] = edited_content

            st.header("Download Updated ZIP")
            
            if st.button("Generate Updated ZIP"):
                output_zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(output_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as out_zip:
                    # Write all original files back, replacing the edited txt files
                    for filename, original_content in original_files_content.items():
                        if filename in edited_data:
                            # It's an edited text file
                            out_zip.writestr(filename, edited_data[filename].encode('utf-8'))
                        else:
                            # It's some other file (image, html, etc.)
                            out_zip.writestr(filename, original_content)
                
                output_zip_buffer.seek(0)
                
                st.download_button(
                    label="Download Result.zip",
                    data=output_zip_buffer,
                    file_name="updated_trackers.zip",
                    mime="application/zip"
                )

        except zipfile.BadZipFile:
            st.error("Error: The uploaded file is not a valid ZIP file.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
