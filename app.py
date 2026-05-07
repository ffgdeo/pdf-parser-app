import streamlit as st
import os
import uuid
from io import StringIO
from datetime import datetime
import pandas as pd
from streamlit_pdf_viewer import pdf_viewer

st.set_page_config(
    page_title="PDF Document Parser",
    page_icon="📄",
    layout="wide",
)

# --- Configure these for your workspace ----------------------------------
# Unity Catalog target: schema, volume, and bronze table all live under
# CATALOG.SCHEMA. SCHEMA, VOLUME, and the bronze table name can stay as-is
# or be renamed; just make sure the SQL in README.md matches.
CATALOG = "fd_serverless_workspace_catalog"  # ← change this to your catalog
SCHEMA = "pdf_parser"
VOLUME = "uploads"
# --------------------------------------------------------------------------
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
TABLE = f"{CATALOG}.{SCHEMA}.parsed_documents"

# --- Database connection (OBO: runs as the logged-in user) ---
from databricks.sdk.core import Config
from databricks import sql


def _get_user_token():
    """Pull the calling user's OAuth token from the X-Forwarded-Access-Token header.

    Databricks Apps with user authorization (OBO) inject this header on every
    request to the app. The token carries only the scopes declared in the app's
    user_api_scopes (e.g. sql, files.files).
    """
    try:
        token = st.context.headers.get("x-forwarded-access-token")
        if token:
            return token
    except Exception:
        pass
    return None


def _require_user_token():
    token = _get_user_token()
    if not token:
        st.error(
            "No user token in request headers. This app must run in OBO mode "
            "with sql + files.files scopes configured."
        )
        st.stop()
    return token


def get_connection():
    """Per-request SQL connection authenticated as the calling user."""
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]
    return sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        access_token=_require_user_token(),
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
    """Upload a file to UC volume as the calling user (OBO).

    Apps runtime injects DATABRICKS_CLIENT_ID/SECRET (the SP's OAuth creds) into
    the env. We need to bypass those and force the SDK to use only the user's
    PAT-style bearer token from X-Forwarded-Access-Token. Pinning auth_type="pat"
    prevents the SDK from co-mixing both auth paths.
    """
    from databricks.sdk import WorkspaceClient

    host = os.environ["DATABRICKS_HOST"]
    w = WorkspaceClient(host=host, token=_require_user_token(), auth_type="pat")
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


def _try_parse_html_table(html_text):
    """Attempt to parse an HTML table string into a DataFrame.
    Returns the DataFrame on success, None on failure.
    """
    if not html_text or "<table" not in html_text.lower():
        return None
    try:
        tables = pd.read_html(StringIO(html_text))
        if tables:
            return tables[0].fillna("").astype(str)
    except Exception:
        pass
    return None


# ai_parse_document rasterizes pages around 200 DPI before extracting bboxes,
# so its coords are ~2.78× the PDF point space (72 DPI). Multiplying by 72/200
# converts them back to PDF points, which is what streamlit-pdf-viewer expects.
PARSER_COORD_SCALE = 72.0 / 200.0


def _df_to_markdown(df):
    """Render a DataFrame as a GitHub-flavored markdown table (no extra deps)."""
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for _, row in df.iterrows():
        body.append("| " + " | ".join(str(v) if pd.notna(v) else "" for v in row) + " |")
    return "\n".join([header, sep] + body)


def _normalize_bbox(elem):
    """Pull a (page, x, y, width, height) tuple out of the element.

    Databricks ai_parse_document emits bbox as:
        bbox: [{coord: [x1, y1, x2, y2], page_id: <0-indexed int>}, ...]

    We take the first region and convert to (page, x, y, width, height) where
    page is 1-indexed for streamlit-pdf-viewer.

    Falls back to other common shapes (single dict, flat 4-list) for safety.
    """
    bbox = elem.get("bbox") or elem.get("bounding_box") or elem.get("coordinates")
    if bbox is None:
        return None

    # Primary case: [{coord: [...], page_id: int}, ...]
    if isinstance(bbox, list) and bbox and isinstance(bbox[0], dict):
        first = bbox[0]
        coord = first.get("coord") or first.get("coords")
        page_id = first.get("page_id", first.get("page", first.get("page_number")))
        if coord and len(coord) == 4 and page_id is not None:
            x1, y1, x2, y2 = coord
            try:
                return {
                    "page": int(page_id) + 1,  # 0-indexed → 1-indexed
                    "x": float(x1), "y": float(y1),
                    "width": float(x2) - float(x1),
                    "height": float(y2) - float(y1),
                }
            except (TypeError, ValueError):
                return None

    # Fallback shapes — element-level page + flat list / dict bbox
    page = (elem.get("page_number") or elem.get("page")
            or elem.get("page_id") or elem.get("page_index"))
    if page is None:
        return None

    if isinstance(bbox, list) and len(bbox) == 4:
        x1, y1, b, c = bbox
        if b > x1 and c > y1:
            x, y, w, h = x1, y1, b - x1, c - y1
        else:
            x, y, w, h = x1, y1, b, c
    elif isinstance(bbox, dict):
        x = bbox.get("x", bbox.get("left", 0))
        y = bbox.get("y", bbox.get("top", 0))
        w = bbox.get("width", bbox.get("w", 0))
        h = bbox.get("height", bbox.get("h", 0))
    else:
        return None

    try:
        return {"page": int(str(page).split(".")[0]) + 1,
                "x": float(x), "y": float(y),
                "width": float(w), "height": float(h)}
    except (TypeError, ValueError):
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
        bbox = _normalize_bbox(elem)

        if content:
            text_blocks.append({
                "type": elem_type, "content": content,
                "description": description, "bbox": bbox,
                "raw": elem,  # keep the original for debug visibility
            })
        elif description:
            text_blocks.append({
                "type": elem_type, "content": description,
                "description": description, "bbox": bbox,
                "raw": elem,
            })

    return text_blocks


def submit_to_table(filename, raw_parsed, reviewed_text, reviewed_blocks_json):
    """Insert the reviewed document into the bronze table."""
    doc_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    def esc(s):
        return s.replace("'", "''") if s else ""

    query = f"""
    INSERT INTO {TABLE}
        (id, filename, upload_ts, raw_parsed, reviewed_text, reviewed_blocks, submitted_by, submitted_ts)
    VALUES (
        '{doc_id}',
        '{filename}',
        '{now}',
        '{esc(raw_parsed)}',
        '{esc(reviewed_text)}',
        '{esc(reviewed_blocks_json)}',
        'app_user',
        '{now}'
    )
    """
    execute_query(query)
    return doc_id


# --- UI ---

st.title("PDF Document Parser")
st.caption(
    "Upload PDFs, parse them with Databricks AI, review and correct the output, then submit to a Delta table."
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
        "Choose a PDF file",
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
                st.session_state["pdf_bytes"] = uploaded_file.getvalue()

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
            "Compare the original PDF on the left with the parsed blocks on the right. "
            "Edit any incorrect text or table cells, then submit."
        )

        text_blocks = st.session_state["text_blocks"]

        # CSS: pin the PDF column so it stays in view while the blocks scroll
        st.markdown(
            """
            <style>
              [data-testid="stHorizontalBlock"] > div:first-child {
                position: sticky; top: 4rem; align-self: flex-start;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )

        col_pdf, col_blocks = st.columns([1, 1], gap="medium")

        active_idx = st.session_state.get("active_block_idx", 0)
        annotations = []
        block_to_annotation = {}
        for i, b in enumerate(text_blocks):
            bb = b.get("bbox")
            if not bb:
                continue
            block_to_annotation[i] = len(annotations)
            s = PARSER_COORD_SCALE
            annotations.append({
                "page": bb["page"],
                "x": bb["x"] * s, "y": bb["y"] * s,
                "width": bb["width"] * s, "height": bb["height"] * s,
                "color": "red" if i == active_idx else "lightblue",
            })
        scroll_target = block_to_annotation.get(active_idx)

        with col_pdf:
            st.markdown("**Original PDF**")
            if st.session_state.get("pdf_bytes"):
                viewer_kwargs = {
                    "height": 900,
                    "width": "100%",
                    "annotations": annotations,
                    "key": f"pdf_view_{active_idx}",
                }
                if scroll_target is not None:
                    viewer_kwargs["scroll_to_annotation"] = scroll_target
                pdf_viewer(st.session_state["pdf_bytes"], **viewer_kwargs)
                if not annotations:
                    st.caption("_No bounding-box info from the parser — highlights unavailable._")
            else:
                st.info("PDF preview unavailable — re-upload to enable preview.")

        with col_blocks:
            st.markdown("**Parsed Blocks** _(click 📍 to highlight on PDF, edit as needed)_")

            with_bbox = sum(1 for b in text_blocks if b.get("bbox"))
            if with_bbox == 0:
                st.warning(
                    "⚠️ The parser returned no bounding-box info for any block "
                    "— PDF highlights are unavailable. Expand any block's "
                    "🔬 _raw element_ panel below to see what fields the parser actually returned."
                )
            elif with_bbox < len(text_blocks):
                st.info(f"ℹ️ {with_bbox}/{len(text_blocks)} blocks have bbox info.")

            edited_blocks = []
            for i, block in enumerate(text_blocks):
                badge = block["type"].upper()
                page_label = f" · p.{block['bbox']['page']}" if block.get("bbox") else ""
                is_active = (i == active_idx)
                header_icon = "🔴" if is_active else "⚪"

                col_label, col_focus = st.columns([5, 1])
                with col_label:
                    st.markdown(f"{header_icon} **Block {i+1}** `{badge}`{page_label}")
                with col_focus:
                    can_focus = block.get("bbox") is not None
                    if st.button("📍 Show", key=f"focus_btn_{i}",
                                 disabled=not can_focus,
                                 help="Highlight this block on the PDF" if can_focus
                                      else "No bbox info available for this block"):
                        st.session_state["active_block_idx"] = i
                        st.rerun()

                df = _try_parse_html_table(block["content"]) if block["type"].lower() == "table" else None
                if df is not None:
                    edited_df = st.data_editor(
                        df, num_rows="dynamic", use_container_width=True,
                        key=f"block_{i}_table", hide_index=True,
                    )
                    edited_blocks.append({"type": "table", "dataframe": edited_df})
                else:
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

                with st.expander(f"🔬 raw element (block {i+1})"):
                    st.json(block.get("raw", {}))

                st.divider()

            submitted = st.button(
                "Submit to Bronze Table", type="primary", use_container_width=True,
                key="submit_review",
            )

        if submitted:
            import json as _json

            # Build typed JSON for downstream consumption (notebook reads this directly).
            # Tables keep their column headers + per-row maps — no LLM re-parsing needed.
            reviewed_blocks_for_storage = []
            parts = []  # markdown for human readability
            for b in edited_blocks:
                if b["type"] == "table" and "dataframe" in b:
                    df = b["dataframe"].astype(str)
                    cols = [str(c) for c in df.columns]
                    rows = df.to_dict(orient="records")
                    reviewed_blocks_for_storage.append({
                        "type": "table",
                        "columns": cols,
                        "rows": rows,
                    })
                    parts.append("[TABLE]\n" + _df_to_markdown(b["dataframe"]))
                else:
                    reviewed_blocks_for_storage.append({
                        "type": b["type"],
                        "content": b.get("content", ""),
                    })
                    parts.append(f"[{b['type'].upper()}]\n{b.get('content','')}")

            reviewed_text = "\n\n".join(parts)
            reviewed_blocks_json = _json.dumps(reviewed_blocks_for_storage, ensure_ascii=False)

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
                        reviewed_blocks_json,
                    )
                    st.success(f"Document submitted! ID: `{doc_id}`")
                    for key in ["text_blocks", "raw_parsed", "current_file", "volume_path"]:
                        st.session_state.pop(key, None)
                except Exception as e:
                    st.error(f"Submission failed: {e}")

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
