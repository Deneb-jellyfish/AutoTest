const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, PageBreak, Header, Footer, TabStopType,
  TabStopPosition, PositionalTab, PositionalTabAlignment,
  PositionalTabRelativeTo, PositionalTabLeader
} = require('docx');
const fs = require('fs');

const BLUE = "1E4D8C";
const BLUE_LIGHT = "D6E4F7";
const PURPLE = "4B3A8C";
const PURPLE_LIGHT = "E8E3F7";
const GREEN_LIGHT = "E2F0D9";
const AMBER_LIGHT = "FFF2CC";
const GRAY_LIGHT = "F2F2F2";
const RED_LIGHT = "FCE4D6";
const TEAL_LIGHT = "DDEBF7";
const BLACK = "000000";
const DARK_GRAY = "404040";
const MED_GRAY = "595959";

const border = { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

const thickBorder = { style: BorderStyle.SINGLE, size: 8, color: BLUE };
const thickBorders = { top: thickBorder, bottom: thickBorder, left: thickBorder, right: thickBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE } },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: BLUE })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: PURPLE })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: DARK_GRAY })]
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: opts.color || DARK_GRAY, bold: opts.bold || false, italics: opts.italic || false })]
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: DARK_GRAY })]
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: DARK_GRAY })]
  });
}

function spacer(n = 1) {
  return Array.from({ length: n }, () => new Paragraph({ children: [new TextRun("")] }));
}

function headerRow(cells, widths, bg = BLUE) {
  return new TableRow({
    tableHeader: true,
    children: cells.map((text, i) =>
      new TableCell({
        borders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: bg, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
          children: [new TextRun({ text, font: "Arial", size: 20, bold: true, color: "FFFFFF" })]
        })]
      })
    )
  });
}

function dataRow(cells, widths, bg = "FFFFFF") {
  return new TableRow({
    children: cells.map((text, i) =>
      new TableCell({
        borders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: bg, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
          children: [new TextRun({ text: String(text), font: "Arial", size: 20, color: DARK_GRAY })]
        })]
      })
    )
  });
}

function dataRowBold(cells, widths, boldIdx = [], bg = "FFFFFF") {
  return new TableRow({
    children: cells.map((text, i) =>
      new TableCell({
        borders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: bg, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
          children: [new TextRun({ text: String(text), font: "Arial", size: 20, color: DARK_GRAY, bold: boldIdx.includes(i) })]
        })]
      })
    )
  });
}

function infoBox(label, text, color = BLUE_LIGHT) {
  return new Table({
    width: { size: 9026, type: WidthType.DXA },
    columnWidths: [9026],
    rows: [new TableRow({
      children: [new TableCell({
        borders: { ...noBorders, left: { style: BorderStyle.SINGLE, size: 16, color: BLUE } },
        width: { size: 9026, type: WidthType.DXA },
        shading: { fill: color, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 160, right: 120 },
        children: [
          new Paragraph({ children: [new TextRun({ text: label, font: "Arial", size: 20, bold: true, color: BLUE })] }),
          new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, color: DARK_GRAY })] })
        ]
      })]
    })]
  });
}

function codeBlock(text) {
  return new Table({
    width: { size: 9026, type: WidthType.DXA },
    columnWidths: [9026],
    rows: [new TableRow({
      children: [new TableCell({
        borders,
        width: { size: 9026, type: WidthType.DXA },
        shading: { fill: "1E1E1E", type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        children: text.split('\n').map(line =>
          new Paragraph({
            children: [new TextRun({ text: line || " ", font: "Courier New", size: 18, color: "D4D4D4" })]
          })
        )
      })]
    })]
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: PURPLE },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: DARK_GRAY },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
        ]},
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.DECIMAL, text: "%1.%2.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
        ]},
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" } },
          spacing: { after: 120 },
          children: [new TextRun({ text: "AutoTestDesign Tool — 项目文档  |  Assignment 2", font: "Arial", size: 18, color: MED_GRAY })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" } },
          spacing: { before: 120 },
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
          children: [
            new TextRun({ text: "机密 — 仅供小组内部使用", font: "Arial", size: 16, color: MED_GRAY }),
            new TextRun({ text: "\t第 ", font: "Arial", size: 16, color: MED_GRAY }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: MED_GRAY }),
            new TextRun({ text: " 页", font: "Arial", size: 16, color: MED_GRAY }),
          ]
        })]
      })
    },
    children: [

      // ─────────────────────── 封面 ───────────────────────
      new Paragraph({ spacing: { before: 1200 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 240 },
        children: [new TextRun({ text: "AutoTestDesign", font: "Arial", size: 72, bold: true, color: BLUE })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [new TextRun({ text: "AI 驱动的自动化测试设计工具", font: "Arial", size: 36, color: PURPLE })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 480 },
        children: [new TextRun({ text: "项目文档  ·  Assignment 2 Final Project", font: "Arial", size: 26, color: MED_GRAY, italics: true })]
      }),

      new Table({
        width: { size: 5000, type: WidthType.DXA },
        columnWidths: [2000, 3000],
        rows: [
          new TableRow({ children: [
            new TableCell({ borders, shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              width: { size: 2000, type: WidthType.DXA },
              children: [new Paragraph({ children: [new TextRun({ text: "课程", font: "Arial", size: 20, bold: true, color: BLUE })] })] }),
            new TableCell({ borders, width: { size: 3000, type: WidthType.DXA },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: "Software Testing", font: "Arial", size: 20, color: DARK_GRAY })] })] }),
          ]}),
          new TableRow({ children: [
            new TableCell({ borders, shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              width: { size: 2000, type: WidthType.DXA },
              children: [new Paragraph({ children: [new TextRun({ text: "小组成员", font: "Arial", size: 20, bold: true, color: BLUE })] })] }),
            new TableCell({ borders, width: { size: 3000, type: WidthType.DXA },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: "成员 A  ·  成员 B  ·  成员 C", font: "Arial", size: 20, color: DARK_GRAY })] })] }),
          ]}),
          new TableRow({ children: [
            new TableCell({ borders, shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              width: { size: 2000, type: WidthType.DXA },
              children: [new Paragraph({ children: [new TextRun({ text: "技术栈", font: "Arial", size: 20, bold: true, color: BLUE })] })] }),
            new TableCell({ borders, width: { size: 3000, type: WidthType.DXA },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: "Python · Streamlit · Claude API", font: "Arial", size: 20, color: DARK_GRAY })] })] }),
          ]}),
          new TableRow({ children: [
            new TableCell({ borders, shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              width: { size: 2000, type: WidthType.DXA },
              children: [new Paragraph({ children: [new TextRun({ text: "目标应用", font: "Arial", size: 20, bold: true, color: BLUE })] })] }),
            new TableCell({ borders, width: { size: 3000, type: WidthType.DXA },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: "待定（登录系统 / 待办事项 App）", font: "Arial", size: 20, color: DARK_GRAY })] })] }),
          ]}),
          new TableRow({ children: [
            new TableCell({ borders, shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              width: { size: 2000, type: WidthType.DXA },
              children: [new Paragraph({ children: [new TextRun({ text: "提交截止", font: "Arial", size: 20, bold: true, color: BLUE })] })] }),
            new TableCell({ borders, width: { size: 3000, type: WidthType.DXA },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: "第 13 周周五 17:00", font: "Arial", size: 20, color: DARK_GRAY })] })] }),
          ]}),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ─────────────────────── 第一章 项目概述 ───────────────────────
      h1("1  项目概述"),
      h2("1.1  背景与目标"),
      para("本项目要求开发一套 AI 驱动的 AutoTestDesign 工具，实现需求导入、结构化解析、风险分析、测试用例自动生成和结果导出等核心功能，符合 ISTQB 基础级原则及 ISO/IEC/IEEE 29119 系列标准。"),
      para("工具开发完成后，将选取一个独立的目标应用（如登录系统、待办事项 App），通过工具完整走一遍“概念 → 覆盖项识别 → 覆盖策略 → 测试用例设计 → 结果分析 → 改进”流程，以验证工具的有效性。"),
      ...spacer(1),
      h2("1.2  技术选型"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2000, 3000, 4026],
        rows: [
          headerRow(["层面", "技术", "选型理由"], [2000, 3000, 4026]),
          dataRow(["前端框架", "Streamlit 1.35+", "Python 原生，快速构建交互式 Web 界面，无需前后端分离"], [2000, 3000, 4026]),
          dataRow(["AI 引擎", "Claude API (claude-sonnet-4-20250514)", "强大的文本理解与结构化生成能力，支持 JSON 输出"], [2000, 3000, 4026], GRAY_LIGHT),
          dataRow(["数据处理", "pandas 2.x", "需求解析与测试用例的表格化存储和处理"], [2000, 3000, 4026]),
          dataRow(["可视化", "plotly 5.x", "风险雷达图、覆盖率分布等交互图表"], [2000, 3000, 4026], GRAY_LIGHT),
          dataRow(["导出", "openpyxl + json", "生成多 Sheet Excel 报告和标准 JSON 文件"], [2000, 3000, 4026]),
          dataRow(["状态管理", "st.session_state", "页面间数据共享，维护完整工作流状态"], [2000, 3000, 4026], GRAY_LIGHT),
        ]
      }),
      ...spacer(1),

      // ─────────────────────── 第二章 功能需求 ───────────────────────
      new Paragraph({ children: [new PageBreak()] }),
      h1("2  功能需求清单"),
      para("根据作业要求，功能需求分为必须实现（核心分）和可选实现（加分项）两类。"),
      ...spacer(1),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [1000, 2000, 4026, 1000, 1000],
        rows: [
          headerRow(["ID", "功能类别", "描述", "优先级", "状态"], [1000, 2000, 4026, 1000, 1000]),
          dataRow(["FR 1.0", "输入/解析", "支持 CSV、纯文本、直接输入三种需求导入方式", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000]),
          dataRow(["FR 1.1", "需求结构化", "解析识别：输入字段(蓝)、数据范围(黄)、条件(红)、预期动作(绿)", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000], GRAY_LIGHT),
          dataRow(["FR 2.0", "风险分析", "四维度评分 → High/Medium/Low 优先级，支持人工调整", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000]),
          dataRow(["FR 3.0", "黑盒测试设计", "EP / BVA / DT 三种技术自动生成用例，可扩展", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000], GRAY_LIGHT),
          dataRow(["FR 6.0", "输出导出", "生成 JSON / CSV / Excel 三种格式测试报告", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000]),
          dataRow(["FR 4.0", "白盒测试建模", "状态转换图建模 + All-States 覆盖测试序列生成", "加分", "可选"], [1000, 2000, 4026, 1000, 1000], AMBER_LIGHT),
          dataRow(["FR 5.0", "测试预言生成", "根据需求和输入数据 AI 合成预期结果", "加分", "可选"], [1000, 2000, 4026, 1000, 1000], AMBER_LIGHT),
          dataRow(["FR 7.0", "测试套件优化", "去重检测、风险排序、最小化裁剪", "加分", "可选"], [1000, 2000, 4026, 1000, 1000], AMBER_LIGHT),
          dataRow(["NFR 1", "性能", "测试用例生成时间 ≤ 2 秒（单条需求），支持异步调用", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000]),
          dataRow(["NFR 2", "可用性", "交互式设计审查：覆盖项、策略、测试用例均可修改", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000], GRAY_LIGHT),
          dataRow(["NFR 3", "安全性", "API Key 通过环境变量注入，不硬编码", "必须", "待开发"], [1000, 2000, 4026, 1000, 1000]),
        ]
      }),
      ...spacer(1),

      // ─────────────────────── 第三章 系统架构 ───────────────────────
      new Paragraph({ children: [new PageBreak()] }),
      h1("3  系统架构设计"),
      h2("3.1  整体架构"),
      para("系统采用单 Python 应用架构，Streamlit 负责所有页面渲染，Claude API 负责所有 AI 推理，st.session_state 作为统一状态总线。"),
      ...spacer(1),
      infoBox("架构核心原则",
        "所有 AI 调用均封装在 services/ 层，页面层只读写 session_state，不直接调用 API。这样的好处是：AI Prompt 修改不影响页面代码；页面 UI 调整不影响 AI 逻辑；测试时可以 Mock service 层。",
        BLUE_LIGHT),
      ...spacer(1),
      h2("3.2  目录结构"),
      codeBlock(
`autotestdesign/
├── app.py                    # 入口：页面路由 + session 初始化
├── requirements.txt          # 依赖锁定
├── .env.example              # API Key 配置模板
│
├── pages/                    # Streamlit 多页面
│   ├── 1_requirement_import.py
│   ├── 2_structured_review.py
│   ├── 3_coverage_risk.py
│   ├── 4_strategy_mapping.py
│   ├── 5_test_case_workspace.py
│   └── 6_optimization_export.py
│
├── services/                 # AI 调用封装层
│   ├── claude_client.py      # API 客户端 + 重试逻辑
│   ├── parser_service.py     # FR1.1 需求结构化解析
│   ├── risk_service.py       # FR2.0 风险评分
│   ├── testgen_service.py    # FR3.0 测试用例生成
│   └── export_service.py     # FR6.0 导出逻辑
│
├── components/               # 可复用 UI 组件
│   ├── highlight_renderer.py # 彩色标注渲染
│   ├── editable_table.py     # 可编辑 st.data_editor 封装
│   └── risk_badge.py         # High/Med/Low 标签组件
│
└── utils/
    ├── state_manager.py      # session_state 键名常量
    └── prompt_templates.py   # 所有 Prompt 模板集中管理`
      ),
      ...spacer(1),
      h2("3.3  数据流设计"),
      para("session_state 中维护以下核心数据结构，各页面按需读写："),
      ...spacer(1),
      codeBlock(
`# state_manager.py 中的键名常量和数据结构

STATE_REQUIREMENTS = "requirements"
# List[Dict]，每条需求包含：
# { "id": "REQ-001", "raw_text": "...", "source": "csv",
#   "parsed": { "input_fields": [...], "conditions": [...],
#               "actions": [...], "ranges": [...] },
#   "risk": { "score": 78, "level": "High", "dimensions": {...} },
#   "coverage_items": [...], "strategy": ["EP","BVA"],
#   "modified_by_user": True }

STATE_TEST_CASES = "test_cases"
# List[Dict]，每条用例包含：
# { "tc_id": "TC-001", "req_id": "REQ-001", "technique": "BVA",
#   "condition": "...", "input_data": "...", "expected": "...",
#   "priority": "High", "coverage_item": "...",
#   "ai_generated": True, "user_modified": False }

STATE_CURRENT_PAGE = "current_page"
STATE_EXPORT_CONFIG = "export_config"`
      ),
      ...spacer(1),

      // ─────────────────────── 第四章 各模块详细设计 ───────────────────────
      new Paragraph({ children: [new PageBreak()] }),
      h1("4  各模块详细设计"),

      h2("4.1  模块一：Requirement Import"),
      h3("4.1.1  UI 布局"),
      para("页面分三个 Tab，用户选择导入方式后触发解析流程。"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [1500, 3500, 4026],
        rows: [
          headerRow(["Tab", "输入方式", "处理逻辑"], [1500, 3500, 4026]),
          dataRow(["Tab 1", "上传文件（CSV / TXT）", "CSV：自动识别列名，映射到 raw_text 列；TXT：每行切分一条需求"], [1500, 3500, 4026]),
          dataRow(["Tab 2", "粘贴文本", "按句号/换行切分，调用 Claude API 做语义切分，返回条目列表"], [1500, 3500, 4026], GRAY_LIGHT),
          dataRow(["Tab 3", "手动填写", "st.data_editor 空白表格，支持逐行录入，实时预览"], [1500, 3500, 4026]),
        ]
      }),
      ...spacer(1),
      h3("4.1.2  核心代码"),
      codeBlock(
`# pages/1_requirement_import.py

import streamlit as st
import pandas as pd
from services.parser_service import split_requirements

def render():
    st.title("Requirement Import")
    tab1, tab2, tab3 = st.tabs(["上传文件", "粘贴文本", "手动填写"])

    with tab1:
        uploaded = st.file_uploader("上传 CSV 或 TXT", type=["csv","txt"])
        if uploaded:
            df = parse_upload(uploaded)
            st.dataframe(df, use_container_width=True)
            if st.button("确认导入", type="primary"):
                st.session_state["requirements"] = df.to_dict("records")
                st.success(f"已导入 {len(df)} 条需求")
                st.page_link("pages/2_structured_review.py", label="下一步 →")

    with tab2:
        raw = st.text_area("粘贴需求文本", height=200)
        if st.button("AI 切分") and raw:
            with st.spinner("正在解析..."):
                reqs = split_requirements(raw)   # 调用 Claude API
            st.session_state["requirements"] = reqs
            st.success(f"识别出 {len(reqs)} 条需求")

    with tab3:
        blank_df = pd.DataFrame({"需求ID":[],"需求描述":[],"来源模块":[]})
        edited = st.data_editor(blank_df, num_rows="dynamic",
                                use_container_width=True)
        if st.button("保存手动输入"):
            st.session_state["requirements"] = edited.to_dict("records")`
      ),
      ...spacer(1),

      h2("4.2  模块二：Structured Requirement Review"),
      h3("4.2.1  颜色标注规则"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2000, 1800, 2226, 3000],
        rows: [
          headerRow(["字段类型", "颜色", "示例文本", "说明"], [2000, 1800, 2226, 3000]),
          dataRow(["Input Field", "蓝色 #BFDBFE", "用户名、密码、金额", "系统接受的输入参数名称"], [2000, 1800, 2226, 3000]),
          dataRow(["Data Range", "黄色 #FEF08A", "1-100、长度≤20", "数值或字符限制范围"], [2000, 1800, 2226, 3000], GRAY_LIGHT),
          dataRow(["Condition", "红色 #FECACA", "连续错误3次、余额不足", "触发某行为的前置条件"], [2000, 1800, 2226, 3000]),
          dataRow(["Expected Action", "绿色 #BBF7D0", "锁定账号、显示错误提示", "系统应执行的预期行为"], [2000, 1800, 2226, 3000], GRAY_LIGHT),
        ]
      }),
      ...spacer(1),
      h3("4.2.2  高亮渲染实现"),
      codeBlock(
`# components/highlight_renderer.py

def render_highlighted(parsed: dict) -> str:
    """
    将解析结果转换为带颜色 span 的 HTML 字符串
    """
    html = parsed["raw_text"]
    for cond in parsed.get("conditions", []):
        html = html.replace(cond,
            f'<span style="background:#FECACA;padding:2px 4px;'
            f'border-radius:3px;font-weight:500">{cond}</span>')
    for action in parsed.get("actions", []):
        html = html.replace(action,
            f'<span style="background:#BBF7D0;padding:2px 4px;'
            f'border-radius:3px;font-weight:500">{action}</span>')
    for field in parsed.get("input_fields", []):
        html = html.replace(field,
            f'<span style="background:#BFDBFE;padding:2px 4px;'
            f'border-radius:3px">{field}</span>')
    for rng in parsed.get("ranges", []):
        html = html.replace(rng,
            f'<span style="background:#FEF08A;padding:2px 4px;'
            f'border-radius:3px">{rng}</span>')
    return html

# 在页面中调用：
# st.markdown(render_highlighted(req["parsed"]),
#             unsafe_allow_html=True)`
      ),
      ...spacer(1),
      h3("4.2.3  交互式修改设计"),
      para("每条需求下展开一个 expander，内含四个可编辑字段。用户修改后点击“应用”即写回 session_state，并标记 modified_by_user=True。提供“重新 AI 解析”按钮可覆盖当前修改。"),
      ...spacer(1),
      infoBox("作业要求对应",
        "本模块直接对应作业 Mainly 段落的“交互式审查”要求：设计者必须能够在工具中修改覆盖项识别结果。所有人工修改需记录版本，以便在最终报告中展示'改进证据'。",
        PURPLE_LIGHT),
      ...spacer(1),

      h2("4.3  模块三：Coverage and Risk Review"),
      h3("4.3.1  风险评分 Prompt 设计"),
      codeBlock(
`# utils/prompt_templates.py - RISK_SCORING_PROMPT

RISK_PROMPT = """
你是一名 ISTQB 认证的高级测试工程师。
请分析以下软件需求，从四个维度各给 0-25 分：

1. 业务关键性（Business Criticality）：该功能失败对业务的影响
2. 实现复杂度（Implementation Complexity）：技术实现的复杂程度  
3. 测试难度（Test Difficulty）：设计有效测试用例的难度
4. 变更频率（Change Frequency）：该类需求历史上的变更概率

需求文本：
{requirement_text}

请严格按照以下 JSON 格式返回，不要有任何其他文字：
{{
  "total_score": <0-100整数>,
  "level": "<High|Medium|Low>",
  "dimensions": {{
    "business_criticality": <0-25>,
    "implementation_complexity": <0-25>,
    "test_difficulty": <0-25>,
    "change_frequency": <0-25>
  }},
  "reason": "<50字以内的中文说明>"
}}

判断标准：total_score >= 70 → High，40-69 → Medium，< 40 → Low
"""`
      ),
      ...spacer(1),
      h3("4.3.2  覆盖项识别"),
      para("风险评分完成后，自动触发覆盖项识别。AI 返回该需求的测试覆盖点列表，用户可通过 checkbox 勾选/取消，勾选结果直接影响后续 Strategy Mapping 的可用策略。"),
      ...spacer(1),

      h2("4.4  模块四：Strategy Mapping"),
      h3("4.4.1  技术选择逻辑"),
      para("每条需求对应一行，展示 AI 推荐的测试技术（基于覆盖项类型自动推断），用户可覆盖选择。"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2000, 2500, 4526],
        rows: [
          headerRow(["技术", "适用场景", "AI 推荐触发条件"], [2000, 2500, 4526]),
          dataRow(["EP（等价划分）", "有明确分类或区间的输入", "覆盖项中含 input_fields 或 ranges"], [2000, 2500, 4526]),
          dataRow(["BVA（边界值分析）", "数值范围类需求", "parsed.ranges 不为空"], [2000, 2500, 4526], GRAY_LIGHT),
          dataRow(["DT（决策表）", "多条件组合需求", "parsed.conditions 数量 >= 2"], [2000, 2500, 4526]),
          dataRow(["ST（状态转换）", "有状态流转的需求", "覆盖项中含状态相关词汇"], [2000, 2500, 4526], AMBER_LIGHT),
        ]
      }),
      ...spacer(1),
      h3("4.4.2  变更通知机制"),
      para("当用户在本模块修改策略选择后，系统在 session_state 中标记对应需求的 strategy_dirty=True。Test Case Workspace 检测到此标记时，在该需求的用例区域显示黄色提示条："),
      codeBlock(
`# pages/5_test_case_workspace.py

for req in st.session_state["requirements"]:
    if req.get("strategy_dirty"):
        st.warning(f"⚠️ 需求 {req['id']} 的策略已变更，"
                   f"建议点击'重新生成'更新测试用例")`
      ),
      ...spacer(1),

      h2("4.5  模块五：Test Case Workspace"),
      h3("4.5.1  测试用例数据结构"),
      codeBlock(
`# 每条测试用例的完整字段
{
    "tc_id":          "TC-001",
    "req_id":         "REQ-001",     # 追溯到需求
    "technique":      "BVA",          # EP / BVA / DT / ST
    "coverage_item":  "密码长度上边界", # 追溯到覆盖项
    "condition":      "密码长度恰好为 20 个字符",
    "input_data":     "password='a'*20",
    "expected_result":"登录成功，跳转首页",
    "priority":       "High",
    "ai_generated":   True,
    "user_modified":  False,
    "version":        1               # 每次修改 +1
}`
      ),
      ...spacer(1),
      h3("4.5.2  生成 Prompt 设计"),
      codeBlock(
`# utils/prompt_templates.py - TESTCASE_GEN_PROMPT

TESTCASE_PROMPT = """
你是一名专业测试设计工程师，遵循 ISO 29119-4 标准。

需求信息：
- 需求文本：{req_text}
- 已识别的覆盖项：{coverage_items}
- 选定的测试技术：{techniques}

请使用所有选定技术，为上述需求生成测试用例。
要求：
1. 每个覆盖项至少一条用例
2. EP：每个等价类至少一条有效 + 一条无效用例
3. BVA：必须包含上边界、下边界、边界内、边界外四类
4. DT：穷举所有有效条件组合（组合数 > 8 时可精简为重要组合）

严格按以下 JSON 数组格式返回：
[{{
  "technique": "BVA",
  "coverage_item": "密码长度边界",
  "condition": "密码长度为边界值",
  "input_data": "password = 'a' * 8（最小有效值）",
  "expected_result": "登录成功",
  "priority": "High"
}}, ...]
"""`
      ),
      ...spacer(1),
      h3("4.5.3  用例表颜色方案"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2500, 2000, 4526],
        rows: [
          headerRow(["状态", "行背景色", "说明"], [2500, 2000, 4526]),
          dataRow(["AI 生成，未修改", "白色 #FFFFFF", "默认状态"], [2500, 2000, 4526]),
          dataRow(["用户已修改", "淡黄 #FFFBEB", "user_modified=True 时标记"], [2500, 2000, 4526], GRAY_LIGHT),
          dataRow(["新增（用户手动）", "淡绿 #F0FDF4", "tc_id 以 'USR-' 开头的用例"], [2500, 2000, 4526]),
          dataRow(["被标记为冗余", "淡红 #FEF2F2", "优化模块检测为重复的用例"], [2500, 2000, 4526], GRAY_LIGHT),
        ]
      }),
      ...spacer(1),

      h2("4.6  模块六：Optimization and Export"),
      h3("4.6.1  优化功能（FR 7.0 加分项）"),
      bullet("去重检测：对所有用例的 condition + input_data 做 TF-IDF 相似度计算，> 0.85 的对用红色高亮标注"),
      bullet("风险排序：按 High → Medium → Low 重排用例顺序，优先保证高风险用例"),
      bullet("最小化建议：AI 分析用例集，推荐可删除的冗余用例，保留覆盖率不变的最小集"),
      ...spacer(1),
      h3("4.6.2  Excel 多 Sheet 导出"),
      codeBlock(
`# services/export_service.py

import pandas as pd
from io import BytesIO

def export_to_excel(requirements, test_cases, risk_scores):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: 需求分析
        req_df = pd.DataFrame(requirements)[
            ["id","raw_text","risk_level","risk_score","strategy"]]
        req_df.to_excel(writer, sheet_name="需求分析", index=False)

        # Sheet 2: 测试用例
        tc_df = pd.DataFrame(test_cases)
        tc_df.to_excel(writer, sheet_name="测试用例", index=False)

        # Sheet 3: 风险报告
        risk_df = build_risk_report(requirements)
        risk_df.to_excel(writer, sheet_name="风险报告", index=False)

        # Sheet 4: 覆盖矩阵（追溯性）
        matrix_df = build_coverage_matrix(requirements, test_cases)
        matrix_df.to_excel(writer, sheet_name="覆盖矩阵", index=False)

    return output.getvalue()

# 在页面中提供下载按钮：
# st.download_button("下载 Excel 报告", data=export_to_excel(...),
#                    file_name="test_suite.xlsx")`
      ),
      ...spacer(1),

      // ─────────────────────── 第五章 三人分工 ───────────────────────
      new Paragraph({ children: [new PageBreak()] }),
      h1("5  三人分工方案"),
      ...spacer(1),
      infoBox("分工设计原则",
        "按模块垂直切分，每人负责完整的服务层 + 页面层 + 对应文档，减少接口依赖。共享层（services/claude_client.py、utils/state_manager.py）由成员 A 统一维护，其他成员调用。",
        BLUE_LIGHT),
      ...spacer(1),
      h2("5.1  分工总览"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [1200, 2200, 3626, 2000],
        rows: [
          headerRow(["成员", "主责模块", "工具开发内容", "文档交付物"], [1200, 2200, 3626, 2000]),
          dataRowBold(["成员 A", "项目架构 + 模块 1、2",
            "app.py 入口、session_state 设计、claude_client.py、\nRequirement Import 页面、Structured Review 页面 + 高亮渲染组件",
            "README、架构文档、模块 1-2 注释"], [1200, 2200, 3626, 2000], [0], BLUE_LIGHT),
          dataRowBold(["成员 B", "模块 3、4、7（加分）",
            "Coverage & Risk 页面 + risk_service.py、\nStrategy Mapping 页面、优化模块（FR 7.0）",
            "风险分析报告、策略设计说明"], [1200, 2200, 3626, 2000], [0], GREEN_LIGHT),
          dataRowBold(["成员 C", "模块 5、6 + 目标应用测试",
            "Test Case Workspace + testgen_service.py、\nOptimization & Export + export_service.py、\n使用工具对目标应用完整测试",
            "详细测试设计文档、测试执行报告"], [1200, 2200, 3626, 2000], [0], AMBER_LIGHT),
        ]
      }),
      ...spacer(1),

      h2("5.2  成员 A — 项目架构 + 模块 1、2"),
      h3("核心任务"),
      bullet("搭建 Streamlit 多页面项目骨架（app.py + pages/ 结构）"),
      bullet("设计并实现 state_manager.py，定义所有 session_state 键名和数据结构"),
      bullet("实现 claude_client.py：API 调用封装、重试逻辑、超时处理、流式响应"),
      bullet("实现 Requirement Import 页面（三种导入方式 + 预览 + 确认）"),
      bullet("实现 Structured Requirement Review 页面（高亮渲染 + 可编辑字段 + 修改记录）"),
      bullet("编写 parser_service.py：需求切分和结构化解析 Prompt"),
      bullet("编写项目 README：环境配置、启动说明、API Key 设置"),
      ...spacer(1),
      h3("关键技术点"),
      bullet("highlight_renderer.py：HTML span 颜色标注，用 st.markdown unsafe_allow_html=True 渲染"),
      bullet("修改版本记录：每次人工修改在 session_state 中追加 edit_history 列表，供最终报告引用"),
      bullet("claude_client.py 须支持同步调用（单条解析）和批量调用（多条需求并发）"),
      ...spacer(1),

      h2("5.3  成员 B — 模块 3、4 + 优化（加分）"),
      h3("核心任务"),
      bullet("实现 Coverage & Risk Review 页面：风险评分展示（Plotly 雷达图）+ 覆盖项 checkbox"),
      bullet("实现 risk_service.py：四维度评分 Prompt、JSON 解析、人工调整写回"),
      bullet("实现 Strategy Mapping 页面：技术选择 UI + AI 推荐逻辑 + 变更通知"),
      bullet("实现优化模块（FR 7.0）：相似度去重 + 风险排序 + AI 最小化建议"),
      bullet("负责风险分析报告（作业交付物第 2 项）的撰写"),
      ...spacer(1),
      h3("关键技术点"),
      bullet("Plotly 雷达图：px.line_polar，四个维度，展示 AI 评分 vs 用户调整后对比"),
      bullet("相似度计算：sklearn.feature_extraction.text.TfidfVectorizer + cosine_similarity"),
      bullet("策略推荐算法：基于 parsed 字段中各类型的数量做简单规则推断，再由 AI 验证"),
      ...spacer(1),

      h2("5.4  成员 C — 模块 5、6 + 目标应用测试"),
      h3("核心任务"),
      bullet("实现 Test Case Workspace：st.data_editor 可编辑表格 + 行颜色标注 + 追溯 expander"),
      bullet("实现 testgen_service.py：EP/BVA/DT 三技术用例生成 Prompt + 结果解析"),
      bullet("实现 Optimization & Export 页面：三种格式导出 + 下载按钮"),
      bullet("实现 export_service.py：Excel 多 Sheet + JSON 标准格式 + CSV"),
      bullet("选定目标应用，使用本工具完整跑一遍测试流程"),
      bullet("撰写详细测试设计与执行文档（作业交付物第 4 项）"),
      ...spacer(1),
      h3("关键技术点"),
      bullet("st.data_editor 行颜色：通过 column_config 和 pandas Styler 实现行级背景色"),
      bullet("追溯功能：点击某行触发 st.selectbox 联动，右侧显示对应覆盖项和设计依据"),
      bullet("覆盖矩阵 Sheet：行 = 需求，列 = 用例 ID，格子内填写覆盖关系，体现可追溯性"),
      ...spacer(1),

      h2("5.5  协作接口约定"),
      para("三人开发并行时需约定以下接口，避免互相阻塞："),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2500, 2500, 4026],
        rows: [
          headerRow(["接口", "提供方", "约定格式"], [2500, 2500, 4026]),
          dataRow(["claude_client.call(prompt)", "成员 A（第 1 周完成）", "返回 str，调用方自行解析 JSON"], [2500, 2500, 4026]),
          dataRow(["session_state 键名", "成员 A（第 1 周冻结）", "见 state_manager.py，所有成员只读不写常量文件"], [2500, 2500, 4026], GRAY_LIGHT),
          dataRow(["risk_service.score(req_text)", "成员 B（第 2 周完成）", "返回 Dict{score, level, dimensions, reason}"], [2500, 2500, 4026]),
          dataRow(["testgen_service.generate(req, strategies)", "成员 C（第 2 周完成）", "返回 List[Dict]，字段见 4.5.1 节"], [2500, 2500, 4026], GRAY_LIGHT),
        ]
      }),
      ...spacer(1),

      // ─────────────────────── 第六章 开发计划 ───────────────────────
      new Paragraph({ children: [new PageBreak()] }),
      h1("6  开发计划与里程碑"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [1200, 1500, 3526, 2800],
        rows: [
          headerRow(["周次", "时间节点", "完成内容", "负责人"], [1200, 1500, 3526, 2800]),
          dataRowBold(["第 1 周", "前 3 天", "项目骨架、state_manager、claude_client、环境配置", "成员 A（主）"], [1200, 1500, 3526, 2800], [], BLUE_LIGHT),
          dataRow(["第 1 周", "后 4 天", "模块 1（导入）+ 模块 2（解析）初版 + highlight_renderer", "成员 A"], [1200, 1500, 3526, 2800], BLUE_LIGHT),
          dataRowBold(["第 2 周", "前 3 天", "模块 3（风险）+ 模块 4（策略）初版 + risk_service", "成员 B（主）"], [1200, 1500, 3526, 2800], [], GREEN_LIGHT),
          dataRow(["第 2 周", "前 3 天", "模块 5（用例）+ testgen_service 初版（EP/BVA）", "成员 C（并行）"], [1200, 1500, 3526, 2800], GREEN_LIGHT),
          dataRowBold(["第 3 周", "前 4 天", "DT 用例生成 + 模块 6（导出）+ 优化功能（FR 7.0）", "成员 B+C"], [1200, 1500, 3526, 2800], [], AMBER_LIGHT),
          dataRow(["第 3 周", "后 3 天", "端对端联调 + Bug 修复 + 性能优化（< 2 秒）", "全员"], [1200, 1500, 3526, 2800], AMBER_LIGHT),
          dataRowBold(["第 4 周", "全周", "目标应用测试 + 文档撰写 + 演示视频录制", "成员 C（主）+ 全员"], [1200, 1500, 3526, 2800], [], RED_LIGHT),
          dataRow(["提交", "第 13 周五", "所有材料打包提交 TA", "全员确认"], [1200, 1500, 3526, 2800], RED_LIGHT),
        ]
      }),
      ...spacer(1),

      // ─────────────────────── 第七章 Prompt 模板 ───────────────────────
      new Paragraph({ children: [new PageBreak()] }),
      h1("7  核心 Prompt 模板"),
      h2("7.1  需求结构化解析 Prompt（FR 1.1）"),
      codeBlock(
`PARSE_PROMPT = """
你是一名软件测试分析师，请分析以下需求文本，识别并提取四类关键组件。

需求文本：{requirement_text}

请返回严格的 JSON 格式（不要有任何额外文字）：
{{
  "input_fields": ["字段1", "字段2"],     // 系统接受的输入参数
  "data_ranges":  ["范围描述1"],           // 数值或字符限制
  "conditions":   ["条件1", "条件2"],      // 触发某行为的前置条件
  "actions":      ["行为1", "行为2"]       // 系统应执行的动作
}}
如某类为空，返回空数组 []。
"""`
      ),
      ...spacer(1),
      h2("7.2  测试用例生成 Prompt（FR 3.0）"),
      codeBlock(
`TESTCASE_PROMPT = """
你是一名遵循 ISO 29119-4 标准的测试设计工程师。

需求：{req_text}
覆盖项：{coverage_items}
选定技术：{techniques}  // 如 ["EP","BVA"]

规则：
- EP：每个等价类1条有效 + 1条无效用例
- BVA：上边界、下边界、边界内、边界外各1条
- DT：重要条件组合覆盖（≤8条）

返回 JSON 数组，每条用例字段：
{{"technique","coverage_item","condition","input_data",
  "expected_result","priority"}}

只返回 JSON，不要解释文字。
"""`
      ),
      ...spacer(1),
      h2("7.3  Prompt 调优建议"),
      bullet("每个 Prompt 在 utils/prompt_templates.py 集中管理，方便对比不同版本效果"),
      bullet("生产环境 Prompt 应包含 few-shot 示例（2-3 条），提高输出格式稳定性"),
      bullet("如 JSON 解析失败，实现 fallback 重试：追加'你上次的回答格式有误，请重新输出'"),
      bullet("演示视频中展示 Prompt 修改 → 效果对比，体现'Prompt Design'这一评分维度"),
      ...spacer(1),

      // ─────────────────────── 第八章 非功能需求 ───────────────────────
      h1("8  非功能需求实现方案"),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [1500, 3000, 4526],
        rows: [
          headerRow(["NFR", "要求", "实现方案"], [1500, 3000, 4526]),
          dataRow(["性能", "用例生成 ≤ 2 秒", "单条需求用 asyncio 异步调用；批量时用 ThreadPoolExecutor 并发；结果缓存到 session_state 避免重复调用"], [1500, 3000, 4526]),
          dataRow(["可用性", "交互式修改", "st.data_editor（可编辑表格）+ expander 展开修改面板 + 所有修改有撤销入口"], [1500, 3000, 4526], GRAY_LIGHT),
          dataRow(["安全性", "API Key 保护", "通过 st.secrets 或 .env 注入，代码中仅引用 os.getenv('ANTHROPIC_API_KEY')，.env 加入 .gitignore"], [1500, 3000, 4526]),
          dataRow(["可维护性", "代码质量", "services 层 + pages 层分离；所有 Prompt 集中在 prompt_templates.py；关键函数有 docstring"], [1500, 3000, 4526], GRAY_LIGHT),
        ]
      }),
      ...spacer(2),

      // ─────────────────────── 附录 ───────────────────────
      h1("附录  快速启动指南"),
      codeBlock(
`# 1. 克隆项目
git clone <repo-url>
cd autotestdesign

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate   # Windows: venv\\Scripts\\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env，填入：ANTHROPIC_API_KEY=sk-ant-...

# 5. 启动应用
streamlit run app.py

# 6. 浏览器访问
# http://localhost:8501`
      ),
      ...spacer(1),
      para("requirements.txt 内容：", { bold: true }),
      codeBlock(
`streamlit>=1.35.0
anthropic>=0.28.0
pandas>=2.0.0
plotly>=5.0.0
openpyxl>=3.1.0
scikit-learn>=1.3.0
python-dotenv>=1.0.0`
      ),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('./AutoTestDesign_项目文档.docx', buffer);
  console.log('Done');
});
