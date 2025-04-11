import streamlit as st
import pandas as pd
import svgwrite
from io import BytesIO, StringIO
import zipfile
import re
from pyhershey import glyph_factory
import time
import platform
st.sidebar.text(f"Python version: {platform.python_version()}")

# 🎨 Supported fonts in pyhershey
available_fonts = [
    'roman_simplex', 'roman_duplex', 'roman_triplex',
    'italic_complex', 'italic_triplex',
    'script_simplex', 'script_complex'
]

# 🖥️ Streamlit App Title
st.title("🖋️ TechNinja Personalized SVG Note Generator")
st.subheader("For Bachin T-A4 Drawing Machine")

# 📤 Upload the Shopify CSV file
uploaded_file = st.file_uploader("📄 Upload Shopify CSV", type=['csv'])

# 📝 Message template input
template = st.text_input(
    "📝 Message Template (use [Placeholder] from CSV columns)",
    "Hi [First Name], thanks for your orders! 👍"
)

# Font selection
selected_font = st.selectbox("🔤 Choose Font", available_fonts)

# 🎨 SVG Customization
st.sidebar.header("🎨 SVG Customization")
stroke_color = st.sidebar.color_picker("🖋️ Stroke Color", "#FFFFFF")  # White ink by default
stroke_width = st.sidebar.number_input("📏 Stroke Width", min_value=0.1, value=1.0, step=0.1)

# 🔲 Background color default = Black (TechNinja theme)
background_color = st.sidebar.color_picker("🖼️ Background Color", "#000000")

# 🔄 Clear uploaded file
clear_uploader = st.sidebar.button("🗑️ Clear Uploaded File")
if clear_uploader:
    uploaded_file = None
    st.session_state.uploaded_file = None
    st.experimental_rerun()

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file

# 🔧 Convert text to stroke SVG path using pyhershey
def text_to_stroke_svg_path(text, font_name, scale=1.5, x_offset=10, y_offset=70):
    path_data = ""
    current_x = x_offset
    for char in text:
        try:
            glyph = glyph_factory.from_ascii(char, font_name)
            strokes = glyph.as_path()
        except Exception:
            continue  # skip characters not found in the font

        offset_path = ""
        for cmd in strokes.strip().split():
            if cmd.startswith("M") or cmd.startswith("L"):
                coords = cmd[1:].split(",")
                if len(coords) == 2:
                    try:
                        x = float(coords[0]) * scale + current_x
                        y = float(coords[1]) * scale + y_offset
                        offset_path += f"{cmd}{x},{y} "
                    except ValueError:
                        continue
        path_data += offset_path
        current_x += 20 * scale
    return path_data.strip()

# 🧩 Replace [placeholders] in the message with CSV data
def fill_placeholders(template, row):
    matches = re.findall(r"\[([^\]]+)\]", template)
    for match in matches:
        value = str(row.get(match, f"[{match}]"))
        template = template.replace(f"[{match}]", value)
    return template

# 🖼️ Generate the SVG file content
def generate_svg(text, font, filename, stroke_color, stroke_width, background_color):
    dwg = svgwrite.Drawing(size=(600, 200), debug=False)
    if background_color:
        dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill=background_color))

    path_data = text_to_stroke_svg_path(text, font)
    path = dwg.path(d=path_data, fill='none', stroke=stroke_color, stroke_width=stroke_width)
    dwg.add(path)

    svg_str = StringIO()
    dwg.write(svg_str)
    svg_bytes = svg_str.getvalue().encode("utf-8")  # For ZIP or download

    return filename, svg_bytes

# 💣 Main logic
if st.session_state.uploaded_file is not None and template:
    try:
        df = pd.read_csv(st.session_state.uploaded_file)

        placeholders = re.findall(r"\[([^\]]+)\]", template)
        if not placeholders:
            st.warning("⚠️ Your message doesn't contain any placeholders. All notes will have the same message.")

        missing_cols = [col for col in placeholders if col not in df.columns]
        if missing_cols:
            st.warning(f"⚠️ Missing columns in CSV: {', '.join(missing_cols)}")

        svg_zip = BytesIO()
        num_rows = len(df)
        skipped_rows = 0
        with zipfile.ZipFile(svg_zip, 'w') as zipf:
            progress_bar = st.progress(0)
            for i, row in df.iterrows():
                try:
                    message = fill_placeholders(template, row)
                    safe_name = str(row.get("First Name", f"note_{i}")).lower().replace(" ", "_")
                    filename, svg_content = generate_svg(
                        message,
                        selected_font,
                        f"{safe_name}_note.svg",
                        stroke_color,
                        stroke_width,
                        background_color
                    )
                    zipf.writestr(filename, svg_content)
                except KeyError as e:
                    st.warning(f"⚠️ Missing placeholder '{e}' in row {i+2}. Skipped.")
                    skipped_rows += 1
                except Exception as e:
                    st.error(f"🚨 Error in row {i+2}: {e}")
                    skipped_rows += 1
                progress_bar.progress(int((i + 1) / num_rows * 100))

        svg_zip.seek(0)
        st.success(f"✅ Generated {num_rows - skipped_rows} personalized SVG notes!")
        if skipped_rows > 0:
            st.warning(f"⚠️ Skipped {skipped_rows} rows due to missing data or errors.")

        st.download_button(
            "⬇️ Download ZIP of SVGs",
            svg_zip,
            file_name="techninja_notes.zip",
            mime="application/zip"
        )

    except pd.errors.EmptyDataError:
        st.error("🚫 The uploaded CSV file is empty.")
    except FileNotFoundError:
        st.error("🚫 The uploaded CSV file was not found.")
    except Exception as e:
        st.error(f"🚨 An unexpected error occurred: {e}")
elif st.session_state.uploaded_file is None and template:
    st.info("☝️ Please upload a Shopify CSV file to generate personalized SVGs.")
elif st.session_state.uploaded_file is not None and not template:
    st.info("📝 Please enter a message template.")
else:
    st.info("📄 Please upload a Shopify CSV file and enter a message template.")
