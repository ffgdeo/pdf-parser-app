import streamlit as st
import os
import uuid
from datetime import datetime

st.set_page_config(
    page_title="PDF Document Parser",
    page_icon="📄",
    layout="wide",
)

# --- Constants ---
CATALOG = "fd_demo_workspace_catalog"
SCHEMA = "pdf_parser"
VOLUME = "uploads"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
TABLE = f"{CATALOG}.{SCHEMA}.parsed_documents"

# --- Database connection ---
from databricks.sdk.core import Config
from databricks import sql


@st.cache_resource(ttl=300)
def get_connection():
    cfg = Config()
    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
    return sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    )


def execute_query(query, params=None):
    """Execute a SQL query and return results."""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return columns, rows
        return None, None


def upload_file_to_volume(uploaded_file):
    """Upload a file to UC volume using the SDK."""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    target_path = f"{VOLUME_PATH}/{uploaded_file.name}"
    file_bytes = uploaded_file.getvalue()

    w.files.upload(target_path, file_bytes, overwrite=True)
    return target_path


def parse_document(volume_file_path):
    """Run ai_parse_document on a file in the volume."""
    query = f"""
    SELECT ai_parse_document(content) AS parsed
    FROM read_files('{volume_file_path}', format => 'binaryFile')
    """
    columns, rows = execute_query(query)
    if rows and len(rows) > 0:
        return rows[0][0]
    return None


def extract_text_blocks(parsed_json):
    """Extract readable text blocks from the parsed document JSON."""
    import json

    if isinstance(parsed_json, str):
        data = json.loads(parsed_json)
    else:
        data = parsed_json

    text_blocks = []
    document = data.get("document", data)
    elements = document.get("elements", [])

    for elem in elements:
        elem_type = elem.get("type", "unknown")
        content = elem.get("content", "")
        description = elem.get("description", "")

        if content:
            text_blocks.append(
                {"type": elem_type, "content": content, "description": description}
            )
        elif description:
            text_blocks.append(
                {"type": elem_type, "content": description, "description": description}
            )

    return text_blocks


def submit_to_table(filename, raw_parsed, reviewed_text):
    """Insert the reviewed document into the bronze table."""
    doc_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    escaped_raw = raw_parsed.replace("'", "''") if raw_parsed else ""
    escaped_text = reviewed_text.replace("'", "''") if reviewed_text else ""

    query = f"""
    INSERT INTO {TABLE} (id, filename, upload_ts, raw_parsed, reviewed_text, submitted_by, submitted_ts)
    VALUES (
        '{doc_id}',
        '{filename}',
        '{now}',
        '{escaped_raw}',
        '{escaped_text}',
        'app_user',
        '{now}'
    )
    """
    execute_query(query)
    return doc_id


# --- UI ---

st.title("Handwritten PDF Document Parser")
st.caption(
    "Upload handwritten PDFs, parse them with Databricks AI, review and correct the output, then submit to a Delta table."
)

# Sidebar - show submitted documents
with st.sidebar:
    st.header("Submitted Documents")
    if st.button("Refresh", key="refresh_sidebar"):
        st.cache_data.clear()

    try:
        cols, rows = execute_query(
            f"SELECT id, filename, submitted_ts FROM {TABLE} ORDER BY submitted_ts DESC LIMIT 20"
        )
        if rows:
            for row in rows:
                st.text(f"{row[1]}")
                st.caption(f"ID: {row[0][:8]}... | {row[2]}")
                st.divider()
        else:
            st.info("No documents submitted yet.")
    except Exception as e:
        st.warning(f"Could not load submitted documents: {e}")

# Main workflow tabs
tab_upload, tab_review, tab_history = st.tabs(
    ["1. Upload & Parse", "2. Review & Submit", "3. History"]
)

# --- Tab 1: Upload & Parse ---
with tab_upload:
    st.header("Upload a PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file (handwritten notes, forms, etc.)",
        type=["pdf"],
        key="pdf_uploader",
    )

    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("File Preview")
            st.info(
                f"**{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)"
            )

        with col2:
            if st.button("Upload & Parse Document", type="primary", use_container_width=True):
                with st.status("Processing document...", expanded=True) as status:
                    # Step 1: Upload
                    st.write("Uploading to Unity Catalog Volume...")
                    try:
                        volume_path = upload_file_to_volume(uploaded_file)
                        st.write(f"Uploaded to `{volume_path}`")
                    except Exception as e:
                        st.error(f"Upload failed: {e}")
                        st.stop()

                    # Step 2: Parse
                    st.write("Parsing document with ai_parse_document...")
                    try:
                        parsed_result = parse_document(volume_path)
                        if parsed_result is None:
                            st.error("Parsing returned no results.")
                            st.stop()
                        st.write("Document parsed successfully!")
                    except Exception as e:
                        st.error(f"Parsing failed: {e}")
                        st.stop()

                    # Step 3: Extract text
                    st.write("Extracting text blocks...")
                    try:
                        text_blocks = extract_text_blocks(parsed_result)
                        st.write(f"Found {len(text_blocks)} text blocks.")
                    except Exception as e:
                        st.error(f"Text extraction failed: {e}")
                        st.stop()

                    status.update(label="Document processed!", state="complete")

                # Store in session state for review tab
                st.session_state["current_file"] = uploaded_file.name
                st.session_state["raw_parsed"] = parsed_result
                st.session_state["text_blocks"] = text_blocks
                st.session_state["volume_path"] = volume_path

                st.success(
                    "Document processed! Go to the **Review & Submit** tab to review the parsed content."
                )

# --- Tab 2: Review & Submit ---
with tab_review:
    st.header("Review Parsed Content")

    if "text_blocks" not in st.session_state or not st.session_state["text_blocks"]:
        st.info("No document parsed yet. Upload and parse a PDF in the first tab.")
    else:
        st.subheader(f"Reviewing: {st.session_state['current_file']}")
        st.caption(
            "Edit any incorrectly parsed text below. For example, if '700' was misread as '100', correct it here."
        )

        text_blocks = st.session_state["text_blocks"]

        # Build editable form
        with st.form("review_form"):
            edited_blocks = []

            for i, block in enumerate(text_blocks):
                badge = block["type"].upper()
                st.markdown(f"**Block {i+1}** `{badge}`")

                edited_content = st.text_area(
                    f"Content (block {i+1})",
                    value=block["content"],
                    height=100 if len(block["content"]) > 200 else 68,
                    key=f"block_{i}",
                    label_visibility="collapsed",
                )
                edited_blocks.append(
                    {"type": block["type"], "content": edited_content}
                )

                if block.get("description") and block["description"] != block["content"]:
                    with st.expander(f"AI Description (block {i+1})"):
                        st.write(block["description"])

                st.divider()

            col_submit, col_raw = st.columns([1, 1])
            with col_submit:
                submitted = st.form_submit_button(
                    "Submit to Bronze Table", type="primary", use_container_width=True
                )

        if submitted:
            # Combine edited blocks into reviewed text
            reviewed_text = "\n\n".join(
                [f"[{b['type'].upper()}]\n{b['content']}" for b in edited_blocks]
            )

            raw_str = (
                st.session_state["raw_parsed"]
                if isinstance(st.session_state["raw_parsed"], str)
                else str(st.session_state["raw_parsed"])
            )

            with st.spinner("Submitting to Delta table..."):
                try:
                    doc_id = submit_to_table(
                        st.session_state["current_file"],
                        raw_str,
                        reviewed_text,
                    )
                    st.success(f"Document submitted! ID: `{doc_id}`")
                    # Clear session
                    for key in ["text_blocks", "raw_parsed", "current_file", "volume_path"]:
                        st.session_state.pop(key, None)
                except Exception as e:
                    st.error(f"Submission failed: {e}")

        # Show raw JSON in expander
        if "raw_parsed" in st.session_state:
            with st.expander("View Raw Parsed JSON"):
                st.json(st.session_state["raw_parsed"])

# --- Tab 3: History ---
with tab_history:
    st.header("Submission History")

    try:
        cols, rows = execute_query(
            f"""
            SELECT id, filename, upload_ts, reviewed_text, submitted_ts
            FROM {TABLE}
            ORDER BY submitted_ts DESC
            LIMIT 50
            """
        )
        if rows:
            import pandas as pd

            df = pd.DataFrame(rows, columns=cols)
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "id": st.column_config.TextColumn("Document ID", width="small"),
                    "filename": st.column_config.TextColumn("Filename"),
                    "upload_ts": st.column_config.DatetimeColumn("Uploaded"),
                    "reviewed_text": st.column_config.TextColumn(
                        "Reviewed Text", width="large"
                    ),
                    "submitted_ts": st.column_config.DatetimeColumn("Submitted"),
                },
            )

            # Detail view
            selected_id = st.selectbox(
                "Select a document to view details",
                options=[row[0] for row in rows],
                format_func=lambda x: f"{[r[1] for r in rows if r[0] == x][0]} ({x[:8]}...)",
            )

            if selected_id:
                detail_cols, detail_rows = execute_query(
                    f"SELECT * FROM {TABLE} WHERE id = '{selected_id}'"
                )
                if detail_rows:
                    row = detail_rows[0]
                    st.subheader(f"Document: {row[1]}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Reviewed Text:**")
                        st.text(row[4])
                    with col2:
                        st.markdown("**Raw Parsed Output:**")
                        with st.expander("Show JSON"):
                            st.json(row[3])
        else:
            st.info("No documents submitted yet.")
    except Exception as e:
        st.warning(f"Could not load history: {e}")
