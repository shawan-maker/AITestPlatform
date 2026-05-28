"""Generate ai-layer-flow-2-api-combined.png (7-layer API case generation data flow)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "service" / "design" / "img" / "ai-layer-flow-2-api-combined.png"

# Layer band colors (aligned with flow-1)
LAYER_COLORS = [
    "#D6EAF8",  # ① 接入层
    "#AED6F1",  # ② HTTP
    "#D7BDE2",  # ③ Agent
    "#FAD7A0",  # ④ MCP
    "#A3E4D7",  # ⑤ Workflow
    "#F9E79F",  # ⑥ 知识与模型
    "#ABEBC6",  # ⑦ 持久化
]

LAYER_LABELS = [
    "① 接入层",
    "② HTTP 编排层",
    "③ Agent 编排层",
    "④ MCP 工具层",
    "⑤ Workflow 层",
    "⑥ 知识与模型层",
    "⑦ 持久化层",
]

# Canvas: 7 layers + title area
FIG_W, FIG_H = 22, 16
MARGIN_L, MARGIN_R = 1.0, 1.0
TITLE_H = 0.9
LEGEND_H = 0.55
CONTENT_TOP = FIG_H - TITLE_H - LEGEND_H - 0.15
CONTENT_H = CONTENT_TOP - 0.35
LAYER_H = CONTENT_H / 7
LABEL_W = 1.55
BAND_X0 = MARGIN_L + LABEL_W
BAND_X1 = FIG_W - MARGIN_R


def _layer_y(i: int) -> tuple[float, float]:
    """Return (y_bottom, y_top) for layer index 0..6 (bottom to top)."""
    y_top = CONTENT_TOP - i * LAYER_H
    y_bot = y_top - LAYER_H
    return y_bot, y_top


def _box(ax, x, y, w, h, text, fc="#FFFFFF", ec="#333333", fontsize=8, lw=1.0, alpha=1.0):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        alpha=alpha,
        transform=ax.transData,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        wrap=True,
        zorder=4,
    )
    return patch


def _arrow(ax, x1, y1, x2, y2, dashed=False, color="#333333", lw=1.2, style="-|>", rad=0.0):
    ls = (0, (4, 3)) if dashed else "solid"
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=10,
        linewidth=lw,
        linestyle=ls,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        zorder=5,
    )
    ax.add_patch(arr)


def _dashed_group(ax, x0, y, w, h, label, boxes: list[tuple[float, float, str]], fontsize=7.5):
    """Draw a group of boxes with dashed horizontal arrows between them."""
    group = FancyBboxPatch(
        (x0, y),
        w,
        h,
        boxstyle="round,pad=0.03,rounding_size=0.1",
        facecolor="#FFFFFF",
        edgecolor="#666666",
        linewidth=0.8,
        linestyle=(0, (3, 2)),
        zorder=2,
    )
    ax.add_patch(group)
    ax.text(x0 + 0.12, y + h - 0.18, label, fontsize=7.5, fontweight="bold", va="top", zorder=4)
    n = len(boxes)
    gap = 0.12
    inner_w = w - 0.24
    bw = (inner_w - gap * (n - 1)) / n
    bx = x0 + 0.12
    by = y + 0.22
    bh = h - 0.42
    centers = []
    for i, (_, _, txt) in enumerate(boxes):
        _box(ax, bx, by, bw, bh, txt, fc="#F8FBFF", fontsize=fontsize)
        centers.append((bx + bw / 2, by + bh / 2))
        bx += bw + gap
    for i in range(n - 1):
        _arrow(
            ax,
            centers[i][0] + bw / 2 + 0.02,
            centers[i][1],
            centers[i + 1][0] - bw / 2 - 0.02,
            centers[i + 1][1],
            dashed=True,
            color="#555555",
            lw=1.0,
        )


def main():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, FIG_H)
    ax.axis("off")

    # Title
    ax.text(
        FIG_W / 2,
        FIG_H - 0.35,
        "图2：API 接口用例生成数据流（智能体 + 接口详情合一）",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
    )
    ax.text(
        FIG_W / 2,
        FIG_H - TITLE_H - 0.05,
        "虚线箭头 = UI 操作顺序    |    实线箭头 = 数据 / 调用流",
        ha="center",
        va="center",
        fontsize=9,
        color="#444444",
    )

    # Layer bands
    for i, (label, color) in enumerate(zip(LAYER_LABELS, LAYER_COLORS)):
        yb, yt = _layer_y(i)
        band = FancyBboxPatch(
            (BAND_X0, yb + 0.04),
            BAND_X1 - BAND_X0,
            LAYER_H - 0.08,
            boxstyle="square,pad=0",
            facecolor=color,
            edgecolor="#888888",
            linewidth=0.6,
            alpha=0.55,
            zorder=0,
        )
        ax.add_patch(band)
        ax.text(
            MARGIN_L + 0.05,
            (yb + yt) / 2,
            label,
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold",
            rotation=0,
        )

    # ── ① 接入层 ──
    y1b, y1t = _layer_y(0)
    _dashed_group(
        ax,
        BAND_X0 + 0.15,
        y1b + 0.12,
        9.2,
        LAYER_H - 0.24,
        "入口 A · ApiAgentPanel（智能体中心·接口 Tab）",
        [
            (0, 0, "创建\n会话"),
            (0, 0, "对话区\n输入发送"),
            (0, 0, "预览区\nbase_cases"),
            (0, 0, "勾选\nconfirm"),
        ],
    )
    _dashed_group(
        ax,
        BAND_X0 + 9.55,
        y1b + 0.12,
        9.2,
        LAYER_H - 0.24,
        "入口 B · InterfaceCaseGenerateDialog（接口 Tab3）",
        [
            (0, 0, "打开\n生成弹窗"),
            (0, 0, "填写\nuser_prompt"),
            (0, 0, "预览\n勾选"),
            (0, 0, "选环境\nconfirm"),
        ],
    )

    # ── ② HTTP 编排层 ──
    y2b, _ = _layer_y(1)
    ha_x = BAND_X0 + 0.15
    ha_w = 2.05
    ha_h = LAYER_H - 0.28
    ha_y = y2b + 0.14
    ha_boxes = [
        "POST /api/sessions\ncreate_api_session",
        "POST /messages\nSSE · AgentStream",
        "PATCH /preview",
        "POST /api/confirm",
    ]
    ha_centers = []
    for i, txt in enumerate(ha_boxes):
        x = ha_x + i * (ha_w + 0.12)
        _box(ax, x, ha_y, ha_w, ha_h, txt, fc="#FFFFFF", fontsize=7)
        ha_centers.append((x + ha_w / 2, ha_y + ha_h / 2))

    hb_x = BAND_X0 + 9.55
    _box(
        ax,
        hb_x,
        ha_y,
        4.3,
        ha_h,
        "POST .../generate-preview\nApiCaseGenerationService.preview",
        fc="#FFFFFF",
        fontsize=7.5,
    )
    _box(
        ax,
        hb_x + 4.55,
        ha_y,
        4.3,
        ha_h,
        "POST .../cases/confirm\n→ confirm_session()",
        fc="#FFFFFF",
        fontsize=7.5,
    )
    hb_preview_c = (hb_x + 2.15, ha_y + ha_h / 2)
    hb_confirm_c = (hb_x + 6.7, ha_y + ha_h / 2)

    # ── ③ Agent 编排层 ──
    y3b, _ = _layer_y(2)
    ag_x = BAND_X0 + 1.5
    ag_w = 7.5
    ag_h = LAYER_H - 0.3
    ag_y = y3b + 0.15
    _box(
        ax,
        ag_x,
        ag_y,
        ag_w,
        ag_h,
        "api_case_generate_agent\nAgentManage.agent_chat()\nDualMemoryManager · thread_id=api-{session_id}",
        fc="#FFFFFF",
        fontsize=8,
    )
    ag_c = (ag_x + ag_w / 2, ag_y + ag_h / 2)
    _box(
        ax,
        BAND_X0 + 10.5,
        ag_y,
        7.8,
        ag_h,
        "入口 B：无 Agent\npreview 直连 Workflow",
        fc="#F5F5F5",
        ec="#999999",
        fontsize=8.5,
    )
    # supervisor note
    _box(
        ax,
        BAND_X0 + 19.0,
        ag_y,
        2.35,
        ag_h,
        "supervisor_agent\nCLI/Demo",
        fc="#EEEEEE",
        ec="#AAAAAA",
        fontsize=7,
        lw=0.8,
    )

    # ── ④ MCP 工具层 ──
    y4b, _ = _layer_y(3)
    mcp_y = y4b + 0.14
    mcp_h = LAYER_H - 0.28
    mcp_w = 2.6
    mcp_x0 = BAND_X0 + 0.4
    mcp_labels = [
        "search_api_document\nRagGateway.query(_stream)",
        "generate_base_cases\nAPIDocumentParser\n+ basecase WF",
        "sync_api_base_payload\n→ output_payload",
    ]
    mcp_centers = []
    for i, txt in enumerate(mcp_labels):
        x = mcp_x0 + i * (mcp_w + 0.35)
        _box(ax, x, mcp_y, mcp_w, mcp_h, txt, fc="#FFFFFF", fontsize=7.2)
        mcp_centers.append((x + mcp_w / 2, mcp_y + mcp_h / 2))
    ax.text(
        BAND_X0 + 10.2,
        mcp_y + mcp_h / 2,
        "入口 B 不经过 MCP",
        ha="center",
        va="center",
        fontsize=8.5,
        color="#666666",
        style="italic",
    )

    # ── ⑤ Workflow 层 ──
    y5b, _ = _layer_y(4)
    wf_y = y5b + 0.12
    wf_h = LAYER_H - 0.24
    # Preview workflow
    _box(
        ax,
        BAND_X0 + 0.3,
        wf_y,
        8.5,
        wf_h * 0.48,
        "ApiBaseCaseGeneratorWorkflow（预览 · 共用）\n生成 basecase → 覆盖率校验 → 补全(≤MAX) → output_base_cases",
        fc="#FFFFFF",
        fontsize=7.5,
    )
    _box(
        ax,
        BAND_X0 + 9.0,
        wf_y,
        4.5,
        wf_h * 0.48,
        "入口 B 直连\n_invoke_basecase_workflow\n（无 APIDocumentParser）",
        fc="#FFFFFF",
        ec="#666666",
        fontsize=7.5,
    )
    # Confirm shared workflow (green dashed border)
    cf_y = wf_y - wf_h * 0.52 - 0.05
    cf_group = FancyBboxPatch(
        (BAND_X0 + 0.25, cf_y),
        BAND_X1 - BAND_X0 - 0.5,
        wf_h * 0.5,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor="#E8F8F5",
        edgecolor="#1E8449",
        linewidth=1.2,
        linestyle=(0, (4, 3)),
        zorder=2,
    )
    ax.add_patch(cf_group)
    ax.text(
        BAND_X0 + 0.4,
        cf_y + wf_h * 0.5 - 0.12,
        "confirm 共用 · 两入口后半段合一",
        fontsize=7.5,
        fontweight="bold",
        color="#1E8449",
        va="top",
    )
    cf_inner_y = cf_y + 0.08
    cf_inner_h = wf_h * 0.5 - 0.28
    cf_w = 3.8
    cf_items = [
        "confirm_session()",
        "TestEnvironment 校验",
        "concurrent_pre_run_base_cases\nThreadPool · MAX_BATCH_SIZE",
        "APIRuncaseGeneratorWorkflow × N\n结构化 + TestRunner 预执行",
    ]
    cf_centers = []
    for i, txt in enumerate(cf_items):
        x = BAND_X0 + 0.45 + i * (cf_w + 0.25)
        _box(ax, x, cf_inner_y, cf_w, cf_inner_h, txt, fc="#FFFFFF", fontsize=7, ec="#1E8449")
        cf_centers.append((x + cf_w / 2, cf_inner_y + cf_inner_h / 2))
    for i in range(len(cf_centers) - 1):
        _arrow(
            ax,
            cf_centers[i][0] + cf_w / 2 + 0.02,
            cf_centers[i][1],
            cf_centers[i + 1][0] - cf_w / 2 - 0.02,
            cf_centers[i + 1][1],
            color="#1E8449",
        )

    bc_c = (BAND_X0 + 4.55, wf_y + wf_h * 0.24)
    direct_c = (BAND_X0 + 11.25, wf_y + wf_h * 0.24)

    # ── ⑥ 知识与模型层 ──
    y6b, _ = _layer_y(5)
    km_y = y6b + 0.14
    km_h = LAYER_H - 0.28
    _box(
        ax,
        BAND_X0 + 0.3,
        km_y,
        4.2,
        km_h,
        "知识库 · RAG 检索\n（仅入口 A 可选）\nEMBED + RERANK + LLM",
        fc="#FFFFFF",
        fontsize=7.5,
    )
    rag_c = (BAND_X0 + 2.4, km_y + km_h / 2)
    _box(
        ax,
        BAND_X0 + 4.85,
        km_y,
        5.5,
        km_h,
        "大模型 · LLM\nbasecase / runcase / parser\nconfig.settings.llm",
        fc="#FFFFFF",
        fontsize=7.5,
    )
    llm_c = (BAND_X0 + 7.6, km_y + km_h / 2)
    _box(
        ax,
        BAND_X0 + 10.65,
        km_y,
        5.5,
        km_h,
        "执行引擎 · TestRunner\n+ TestEnvDataAssembler\n（confirm 预执行 · 非 LLM）",
        fc="#FFFFFF",
        fontsize=7.5,
    )
    eng_c = (BAND_X0 + 13.4, km_y + km_h / 2)

    # ── ⑦ 持久化层 ──
    y7b, _ = _layer_y(6)
    p_y = y7b + 0.14
    p_h = LAYER_H - 0.28
    p_w = 3.5
    persist = [
        "ai_generation_session\noutput_payload.base_cases",
        "ai_generation_message\n（仅入口 A）",
        "api_base_case",
        "api_test_case\ncase_payload",
    ]
    p_centers = []
    for i, txt in enumerate(persist):
        x = BAND_X0 + 0.35 + i * (p_w + 0.3)
        _box(ax, x, p_y, p_w, p_h, txt, fc="#FFFFFF", fontsize=7.5)
        p_centers.append((x + p_w / 2, p_y + p_h / 2))
    ses_c = p_centers[0]
    msg_c = p_centers[1]
    abc_c = p_centers[2]
    atc_c = p_centers[3]

    preview_a_c = (BAND_X0 + 3.0, y1b + LAYER_H * 0.55)
    preview_b_c = (BAND_X0 + 12.5, y1b + LAYER_H * 0.55)

    # ── Vertical / cross-layer solid arrows ──
    # A UI → HTTP
    _arrow(ax, preview_a_c[0] - 1.5, y1b + 0.12, ha_centers[0][0], ha_centers[0][1] + ha_h / 2 + 0.05, rad=0.1)
    _arrow(ax, preview_a_c[0], y1b + 0.12, ha_centers[1][0], ha_centers[1][1] + ha_h / 2 + 0.05, rad=0.05)
    _arrow(ax, preview_a_c[0] + 1.2, y1b + 0.12, ha_centers[3][0], ha_centers[3][1] + ha_h / 2 + 0.05, rad=-0.08)

    # B UI → HTTP
    _arrow(ax, preview_b_c[0] - 1.0, y1b + 0.12, hb_preview_c[0], hb_preview_c[1] + ha_h / 2 + 0.05, rad=0.1)
    _arrow(ax, preview_b_c[0] + 1.5, y1b + 0.12, hb_confirm_c[0], hb_confirm_c[1] + ha_h / 2 + 0.05, rad=-0.1)

    # HTTP A → Agent / session
    _arrow(ax, ha_centers[0][0], ha_centers[0][1] - ha_h / 2 - 0.02, ses_c[0], p_centers[0][1] + p_h / 2 + 0.02, rad=0.15)
    _arrow(ax, ha_centers[1][0], ha_centers[1][1] - ha_h / 2 - 0.02, ag_c[0], ag_c[1] + ag_h / 2 + 0.02)
    _arrow(ax, ha_centers[1][0], ha_centers[1][1] - ha_h / 2 - 0.02, msg_c[0], msg_c[1] + p_h / 2 + 0.02, rad=0.2)

    # Agent → MCP
    _arrow(ax, ag_c[0], ag_c[1] - ag_h / 2 - 0.02, mcp_centers[0][0], mcp_centers[0][1] + mcp_h / 2 + 0.02)
    _arrow(ax, mcp_centers[0][0] + mcp_w / 2 + 0.02, mcp_centers[0][1], mcp_centers[1][0] - mcp_w / 2 - 0.02, mcp_centers[1][1])
    _arrow(ax, mcp_centers[1][0] + mcp_w / 2 + 0.02, mcp_centers[1][1], mcp_centers[2][0] - mcp_w / 2 - 0.02, mcp_centers[2][1])

    # MCP → Workflow
    _arrow(ax, mcp_centers[1][0], mcp_centers[1][1] - mcp_h / 2 - 0.02, bc_c[0], bc_c[1] + wf_h * 0.24 + 0.02)
    _arrow(ax, mcp_centers[2][0], mcp_centers[2][1] - mcp_h / 2 - 0.02, ses_c[0], ses_c[1] + p_h / 2 + 0.02, rad=0.12)

    # B HTTP preview → direct workflow + session
    _arrow(ax, hb_preview_c[0], hb_preview_c[1] - ha_h / 2 - 0.02, direct_c[0], direct_c[1] + wf_h * 0.24 + 0.02, rad=0.1)
    _arrow(ax, hb_preview_c[0], hb_preview_c[1] - ha_h / 2 - 0.02, ses_c[0] + 0.5, ses_c[1] + p_h / 2 + 0.02, rad=0.25)
    _arrow(ax, direct_c[0], direct_c[1] - wf_h * 0.24 - 0.02, bc_c[0] + 2.0, bc_c[1], rad=0.15)

    # Workflow → LLM
    _arrow(ax, bc_c[0], bc_c[1] - wf_h * 0.24 - 0.02, llm_c[0], llm_c[1] + km_h / 2 + 0.02)
    _arrow(ax, cf_centers[3][0], cf_centers[3][1] - cf_inner_h / 2 - 0.02, eng_c[0], eng_c[1] + km_h / 2 + 0.02, rad=0.1)
    _arrow(ax, cf_centers[3][0] - 1.5, cf_centers[3][1] - cf_inner_h / 2 - 0.02, llm_c[0] + 1.0, llm_c[1] + km_h / 2 + 0.02, rad=0.15)

    # RAG ↔ MCP search
    _arrow(ax, mcp_centers[0][0], mcp_centers[0][1] - mcp_h / 2 - 0.02, rag_c[0], rag_c[1] + km_h / 2 + 0.02)
    _arrow(ax, rag_c[0] + 2.0, rag_c[1], mcp_centers[1][0] - 1.0, mcp_centers[1][1] - mcp_h / 2 - 0.15, rad=0.2)

    # Confirm HTTP → confirm workflow → persist
    _arrow(ax, ha_centers[3][0], ha_centers[3][1] - ha_h / 2 - 0.02, cf_centers[0][0], cf_centers[0][1] + cf_inner_h / 2 + 0.02, rad=0.1)
    _arrow(ax, hb_confirm_c[0], hb_confirm_c[1] - ha_h / 2 - 0.02, cf_centers[0][0] + 1.5, cf_centers[0][1] + cf_inner_h / 2 + 0.02, rad=-0.1)
    _arrow(ax, cf_centers[3][0], cf_centers[3][1] - cf_inner_h / 2 - 0.02, abc_c[0], abc_c[1] + p_h / 2 + 0.02)
    _arrow(ax, cf_centers[3][0] + 0.5, cf_centers[3][1] - cf_inner_h / 2 - 0.02, atc_c[0], atc_c[1] + p_h / 2 + 0.02, rad=0.12)

    # Echo: persist → preview (dashed)
    _arrow(ax, ses_c[0], ses_c[1] + p_h / 2 + 0.02, preview_a_c[0] + 0.5, y1b + 0.12, dashed=True, color="#2E86C1", lw=1.3)
    _arrow(ax, ses_c[0] + 0.8, ses_c[1] + p_h / 2 + 0.02, preview_b_c[0], y1b + 0.12, dashed=True, color="#2E86C1", lw=1.3)
    ax.text(BAND_X0 + 8.2, y5b + LAYER_H * 0.85, "回显", fontsize=8, color="#2E86C1", ha="center")

    # Side notes
    ax.text(
        BAND_X1 - 0.1,
        y4b + LAYER_H * 0.5,
        "对话阶段\n不含预执行",
        ha="right",
        va="center",
        fontsize=7.5,
        color="#555555",
        bbox=dict(boxstyle="round", facecolor="#FFFDE7", edgecolor="#CCCCCC", alpha=0.9),
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
