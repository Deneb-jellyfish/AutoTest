from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core.data_model import PRIORITY_LEVELS, RAW_REQUIREMENT_STATUS, Requirement, dataclass_to_dict, utc_now_iso
from core.llm_client import LlmClient, load_config
from core.plain_text_importer import extract_requirements_from_plain_text
from core.requirement_parser import parse_requirements_with_report, should_protect
from core.state_manager import generate_parsed_id, get_state, save_state
from utils.change_tracker import log_change
from utils.ids import generate_prefixed_id
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


def parse_tags(raw_tags: str) -> List[str]:
    return [item.strip() for item in raw_tags.split(",") if item.strip()]


def validate_requirement(title: str, raw_text: str) -> List[str]:
    errors = []
    if not title.strip():
        errors.append("标题为必填项")
    if len(title.strip()) > 80:
        errors.append("标题不能超过 80 个字符")
    if not raw_text.strip():
        errors.append("需求原文为必填项")
    return errors


def generate_requirement_id(ps: Dict[str, Any]) -> str:
    return generate_prefixed_id([item.get("requirement_id") or item.get("req_id") for item in ps["requirements"]], "REQ")


def build_requirement_record(ps: Dict[str, Any], row: Dict[str, Any], source: str) -> Dict[str, Any]:
    requirement_id = generate_requirement_id(ps)
    return dataclass_to_dict(
        Requirement(
            requirement_id=requirement_id,
            req_id=requirement_id,
            title=str(row.get("title", "")).strip() or requirement_id,
            raw_text=str(row.get("raw_text", "")).strip(),
            source=source,
            priority=str(row.get("priority", "Medium")).strip() if str(row.get("priority", "")).strip() in PRIORITY_LEVELS else "Medium",
            review_status="Imported",
            source_annotations=row.get("source_annotations") or [{"text": str(row.get("raw_text", "")).strip()[:80], "category": "source"}],
            tags=parse_tags(str(row.get("tags", ""))),
            notes=str(row.get("notes", "")).strip(),
            created_at=utc_now_iso(),
        )
    )


def import_requirement_rows(ps: Dict[str, Any], rows: List[Dict[str, Any]], source: str) -> int:
    imported = 0
    for row in rows:
        title = str(row.get("title", "")).strip()
        raw_text = str(row.get("raw_text", "")).strip()
        if not raw_text:
            continue
        record = build_requirement_record(ps, {"title": title or raw_text[:36], **row}, source)
        ps["requirements"].append(record)
        log_change(ps, "requirement", record["requirement_id"], "Created", "record", None, record, "human", f"Imported via {source}")
        imported += 1
    return imported


def sync_batch_structured_results(ps: Dict[str, Any], parsed_records: List[Dict[str, Any]]) -> tuple[int, int]:
    updated = 0
    skipped = 0
    existing_map = {item["requirement_id"]: item for item in ps["parsed_requirements"]}

    for record in parsed_records:
        existing = existing_map.get(record["requirement_id"])
        if existing and should_protect(existing):
            skipped += 1
            continue
        if existing:
            old_value = deepcopy(existing)
            existing.update(record)
            existing["parsed_id"] = old_value["parsed_id"]
            log_change(ps, "parsed_req", existing["parsed_id"], "Regenerated", "record", old_value, existing, "llm", "Batch structure from import page")
        else:
            if not record.get("parsed_id"):
                record["parsed_id"] = generate_parsed_id(ps)
            ps["parsed_requirements"].append(record)
            log_change(ps, "parsed_req", record["parsed_id"], "Created", "record", None, record, "llm", "Batch structure from import page")
        updated += 1

    for requirement in ps["requirements"]:
        if requirement["requirement_id"] in {item["requirement_id"] for item in parsed_records}:
            requirement["review_status"] = "Structured"
    return updated, skipped


st.set_page_config(page_title="Requirement Import", layout="wide", page_icon="🧪")
apply_reference_theme()

ps = get_state()
llm_client = LlmClient(load_config())
use_llm = bool(st.session_state.get("use_llm", False))

with st.sidebar:
    render_workflow_sidebar("Requirement Import")
    st.divider()
    st.subheader("Project")
    st.text_input("Project Name", value=ps["project_meta"].get("project_name", ""), key="sidebar_project_name")
    st.caption("切分纯文本/TXT 时可选用 LLM；结构化阶段必须使用真实 LLM。")

render_hero(
    "AI-Assisted Requirement Intake",
    "Requirement Import",
    "Import raw requirements from multiple sources, review the table directly, then batch-structure them in one pass.",
)

req_count = len(ps["requirements"])
structured_count = len(ps["parsed_requirements"])
approved_count = len([item for item in ps["parsed_requirements"] if item.get("review_status") == "Approved"])
high_risk = len([item for item in ps["risk_items"] if item.get("risk_level") == "High"])

metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    st.metric("Requirements", req_count)
with metric2:
    st.metric("Structured Items", structured_count)
with metric3:
    st.metric("Approved", approved_count)
with metric4:
    st.metric("High Risk", high_risk)

action_left, action_right = st.columns([1.2, 2])
with action_left:
    if st.button("Structure Requirements", type="primary", use_container_width=True):
        if not ps["requirements"]:
            st.error("当前没有可结构化的需求。")
        elif not use_llm or not llm_client.enabled:
            st.error("结构化需求只支持真实 LLM。请先在侧边栏启用并配置 LLM。")
        else:
            parsed_id_lookup = {
                item["requirement_id"]: item["parsed_id"]
                for item in ps["parsed_requirements"]
            }
            try:
                result = parse_requirements_with_report(ps["requirements"], llm_client, parsed_id_lookup=parsed_id_lookup)
                updated, skipped = sync_batch_structured_results(ps, result["parsed_requirements"])
                log_change(
                    ps,
                    "parsed_req",
                    "batch",
                    "Regenerated",
                    "record",
                    None,
                    result["report"],
                    "llm",
                    f"Batch structured {updated} requirements; skipped {skipped} approved records",
                )
                save_state(ps)
                st.success(f"结构化完成：更新 {updated} 条，跳过 {skipped} 条已 Approved 记录。")
                st.rerun()
            except Exception as exc:
                st.error(f"批量结构化失败：{exc}")
with action_right:
    st.info("这里的 Structure Requirements 会把当前 requirements 整批送去结构化，不是一条条调用。")

st.markdown("### Import Raw Requirements")
tab_manual, tab_csv, tab_text, tab_txt = st.tabs(["Manual", "CSV", "Plain Text", "TXT"])

with tab_manual:
    with st.form("manual_req_form"):
        title = st.text_input("Title *")
        raw_text = st.text_area("Requirement Text *", height=180)
        priority = st.selectbox("Priority", PRIORITY_LEVELS, index=1)
        tags = st.text_input("Tags")
        notes = st.text_area("Notes", height=80)
        submit_manual = st.form_submit_button("Add Requirement", type="secondary")
    if submit_manual:
        errors = validate_requirement(title, raw_text)
        if errors:
            for error in errors:
                st.error(error)
        else:
            record = build_requirement_record(
                ps,
                {"title": title, "raw_text": raw_text, "priority": priority, "tags": tags, "notes": notes},
                "manual_input",
            )
            ps["requirements"].append(record)
            log_change(ps, "requirement", record["requirement_id"], "Created", "record", None, record, "human", "Manual add")
            save_state(ps)
            st.success(f"已新增 {record['requirement_id']}")
            st.rerun()

with tab_csv:
    uploaded_csv = st.file_uploader("Upload CSV", type=["csv"], key="req_csv_upload")
    if uploaded_csv is not None:
        try:
            csv_df = pd.read_csv(uploaded_csv)
            if "raw_text" not in csv_df.columns:
                st.error("CSV 必须包含 `raw_text` 列。")
            else:
                if "title" not in csv_df.columns:
                    csv_df["title"] = [f"Requirement {index}" for index in range(1, len(csv_df) + 1)]
                for col in ["priority", "tags", "notes"]:
                    if col not in csv_df.columns:
                        csv_df[col] = ""
                st.session_state["csv_preview_rows"] = csv_df[["title", "raw_text", "priority", "tags", "notes"]].fillna("").to_dict(orient="records")
        except Exception as exc:
            st.error(f"CSV 读取失败：{exc}")

    csv_preview_rows = st.session_state.get("csv_preview_rows", [])
    if csv_preview_rows:
        csv_preview_df = pd.DataFrame(csv_preview_rows)
        edited_csv_df = st.data_editor(
            csv_preview_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="csv_preview_editor_new",
        )
        if st.button("Import CSV Requirements", type="primary"):
            imported = import_requirement_rows(ps, edited_csv_df.to_dict(orient="records"), "csv_import")
            save_state(ps)
            st.success(f"已导入 {imported} 条需求")
            st.session_state.pop("csv_preview_rows", None)
            st.rerun()

with tab_text:
    text_input = st.text_area("Paste plain-text requirements", height=220, placeholder="支持多段文本、编号列表或长段落。", key="plain_text_input")
    if st.button("Extract Requirements from Text", key="extract_text_btn"):
        result = extract_requirements_from_plain_text(text_input, use_llm=use_llm, llm_client=llm_client)
        st.session_state["text_preview_rows"] = result["requirements"]
        st.session_state["text_preview_method"] = result["method"]
        st.session_state["text_preview_warnings"] = result["warnings"]
    if st.session_state.get("text_preview_rows"):
        st.caption(f"切分方式：{st.session_state.get('text_preview_method')}")
        for warning in st.session_state.get("text_preview_warnings", []):
            st.warning(warning)
        text_preview_df = pd.DataFrame(st.session_state["text_preview_rows"])
        edited_text_df = st.data_editor(
            text_preview_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="text_preview_editor",
        )
        if st.button("Use Text Requirements", type="primary"):
            imported = import_requirement_rows(ps, edited_text_df.to_dict(orient="records"), "paste")
            save_state(ps)
            st.success(f"已导入 {imported} 条需求")
            st.session_state.pop("text_preview_rows", None)
            st.rerun()

with tab_txt:
    uploaded_txt = st.file_uploader("Upload TXT", type=["txt"], key="txt_upload")
    if uploaded_txt is not None:
        raw_bytes = uploaded_txt.getvalue()
        try:
            txt_content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            txt_content = raw_bytes.decode("gbk", errors="ignore")
        if st.button("Extract Requirements from TXT", key="extract_txt_btn"):
            result = extract_requirements_from_plain_text(txt_content, use_llm=use_llm, llm_client=llm_client)
            st.session_state["txt_preview_rows"] = result["requirements"]
            st.session_state["txt_preview_method"] = result["method"]
            st.session_state["txt_preview_warnings"] = result["warnings"]
    if st.session_state.get("txt_preview_rows"):
        st.caption(f"切分方式：{st.session_state.get('txt_preview_method')}")
        for warning in st.session_state.get("txt_preview_warnings", []):
            st.warning(warning)
        txt_preview_df = pd.DataFrame(st.session_state["txt_preview_rows"])
        edited_txt_df = st.data_editor(
            txt_preview_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="txt_preview_editor",
        )
        if st.button("Use TXT Requirements", type="primary"):
            imported = import_requirement_rows(ps, edited_txt_df.to_dict(orient="records"), "txt_upload")
            save_state(ps)
            st.success(f"已导入 {imported} 条需求")
            st.session_state.pop("txt_preview_rows", None)
            st.rerun()

st.markdown("### Current Requirements")
if not ps["requirements"]:
    st.info("还没有 requirement。先从上面的任一入口导入。")
else:
    requirement_rows = []
    for item in ps["requirements"]:
        requirement_rows.append(
            {
                "requirement_id": item.get("requirement_id", item.get("req_id")),
                "title": item.get("title", ""),
                "priority": item.get("priority", "Medium"),
                "review_status": item.get("review_status", "Imported"),
                "source": item.get("source", ""),
                "raw_text": item.get("raw_text", ""),
            }
        )
    st.dataframe(pd.DataFrame(requirement_rows), use_container_width=True, hide_index=True)
