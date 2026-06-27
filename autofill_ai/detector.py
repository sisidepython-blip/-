"""模块3: 文档理解与坐标定位器 - 深度解析PDF，提取所有填写字段及坐标。

双路径解析策略:
  Path A - AcroForm 交互式表单: 直接读取Widget字段（精确、快速）
  Path B - 静态表单: 使用 CommonForms (FFDNet-L ML模型) 检测文本框/复选框/签名区

输出统一的需求清单:
  [{ "id": 0, "field_name": "name", "requirement": "姓名",
     "x": 180, "y": 62, "width": 200, "height": 22, "type": "TextBox" }]
"""

import sys
from pathlib import Path


def detect_fields(pdf_path: str, use_ml: bool = True) -> list[dict]:
    """解析PDF表单，返回填写字段需求清单。"""
    import pymupdf

    # ---- Path A: 尝试 AcroForm ----
    doc = pymupdf.open(pdf_path)
    has_acroform = any(page.widgets() for page in doc)
    doc.close()

    if has_acroform:
        print(f"  [检测] 路径A: 交互式表单 (AcroForm)")
        return _parse_acroform(pdf_path)
    else:
        print(f"  [检测] 路径B: 静态表单 (无AcroForm)")
        if use_ml:
            return _parse_with_commonforms(pdf_path)
        else:
            return _parse_static_heuristic(pdf_path)


def _parse_acroform(pdf_path: str) -> list[dict]:
    """解析AcroForm交互式表单，直接提取字段名和坐标。"""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    fields = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        for widget in page.widgets():
            rect = widget.rect
            field_type = _classify_widget_type(widget)

            fields.append({
                "id": len(fields),
                "field_name": widget.field_name or f"field_{len(fields)}",
                "field_type": field_type,
                "x": rect.x0,
                "y": rect.y0,
                "width": rect.width,
                "height": rect.height,
                "page": page_num,
                "requirement": widget.field_name or "",
            })

    doc.close()
    return fields


def _classify_widget_type(widget) -> str:
    """根据PyMuPDF的Widget属性判断字段类型。"""
    ft = getattr(widget, "field_type", None)
    if ft is not None:
        type_map = {3: "TextBox", 4: "TextBox", 6: "TextBox",
                    2: "CheckBox", 7: "Signature"}
        return type_map.get(ft, "TextBox")
    return "TextBox"


# ---- Path B: CommonForms ML 检测 ----
def _parse_with_commonforms(pdf_path: str) -> list[dict]:
    """使用 CommonForms ML模型检测静态表单中的填写字段。

    使用已下载的 02-CommonForms 项目中的 FFDNet-L 模型:
      - 检测 TextBox / ChoiceButton / Signature
      - 返回归一化坐标 → 转为绝对坐标
    """
    import pymupdf

    print("  [CommonForms] 加载 FFDNet-L 模型并检测表单字段...")

    try:
        from commonforms.inference import (
            render_pdf,
            FFDNetDetector,
        )

        # 渲染PDF页面为图像
        pages = render_pdf(pdf_path)
        print(f"  [CommonForms] 渲染了 {len(pages)} 页")

        # 使用FFDNet-L模型检测
        detector = FFDNetDetector("FFDNet-L", device="cpu")
        results = detector.extract_widgets(pages, confidence=0.3, image_size=1600)

        # 获取页面尺寸用于坐标转换
        doc = pymupdf.open(pdf_path)
        page_sizes = []
        for i in range(len(doc)):
            page = doc[i]
            rect = page.rect
            page_sizes.append((rect.width, rect.height))
        doc.close()

        # 转换归一化坐标 → 绝对坐标
        fields = []
        for page_ix, widgets in results.items():
            pw, ph = page_sizes[page_ix] if page_ix < len(page_sizes) else (595, 842)
            for widget in widgets:
                bb = widget.bounding_box
                fields.append({
                    "id": len(fields),
                    "field_name": f"{widget.widget_type.lower()}_{widget.page}_{len(fields)}",
                    "field_type": widget.widget_type,
                    "x": bb.x0 * pw,
                    "y": bb.y0 * ph,
                    "width": (bb.x1 - bb.x0) * pw,
                    "height": (bb.y1 - bb.y0) * ph,
                    "page": widget.page,
                    "requirement": _find_nearby_text(
                        pages[page_ix] if page_ix < len(pages) else None,
                        widget,
                    ),
                })

        print(f"  [CommonForms] 检测到 {len(fields)} 个字段"
              f" ({sum(1 for f in fields if f['field_type']=='TextBox')} TextBox,"
              f" {sum(1 for f in fields if f['field_type']=='ChoiceButton')} CheckBox)")

        return fields

    except ImportError as e:
        print(f"  [警告] CommonForms 未安装或加载失败: {e}")
        print("  [回退] 使用启发式静态检测...")
        return _parse_static_heuristic(pdf_path)


def _find_nearby_text(page, widget) -> str:
    """在widget附近查找关联文本标签，作为填写要求描述。"""
    if page is None or not page.text_fragments:
        return widget.widget_type

    best = None
    best_dist = float("inf")
    wcx = (widget.bounding_box.x0 + widget.bounding_box.x1) / 2
    wcy = (widget.bounding_box.y0 + widget.bounding_box.y1) / 2

    for frag in page.text_fragments:
        # 文本在widget附近（上方或左侧）
        if frag.y0 > wcy + 0.1:
            continue
        dist = abs(frag.y0 - wcy) + abs(frag.x0 - wcx) * 0.5
        if dist < best_dist:
            best_dist = dist
            best = frag.text

    return best or widget.widget_type


# ---- Path B 备用: 启发式静态检测 ----
def _parse_static_heuristic(pdf_path: str) -> list[dict]:
    """启发式检测静态表单：扫描下划线和矩形框，关联附近文本。"""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    fields = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 1) 获取绘图指令，检测水平线条（填空线）
        drawings = page.get_drawings()
        lines = []
        for drawing in drawings:
            for item in drawing.get("items", []):
                if item[0] == "l":
                    _, start, end = item
                    if (abs(start.y - end.y) < 2
                            and abs(end.x - start.x) > 30):
                        lines.append({
                            "x0": min(start.x, end.x),
                            "y0": start.y,
                            "x1": max(start.x, end.x),
                            "width": abs(end.x - start.x),
                        })

        # 2) 获取文本块
        blocks = page.get_text("dict").get("blocks", [])
        texts = []
        for block in blocks:
            for line in block.get("lines", []):
                bbox = line["bbox"]
                text = "".join(
                    s["text"] for s in line["spans"]
                ).strip().rstrip(":：_")
                if text:
                    texts.append({"text": text, "x": bbox[0], "y": bbox[1]})

        # 3) 将线条关联到最近的文本
        for i, line in enumerate(lines):
            nearest = ""
            min_dist = float("inf")
            for t in texts:
                if t["y"] < line["y0"]:
                    dist = abs(t["y"] - line["y0"]) + abs(t["x"] - line["x0"])
                    if dist < min_dist:
                        min_dist = dist
                        nearest = t["text"]

            fields.append({
                "id": len(fields),
                "field_name": f"field_{page_num}_{i}",
                "field_type": "TextBox",
                "x": line["x0"],
                "y": line["y0"] - 4,
                "width": line["width"],
                "height": 18,
                "page": page_num,
                "requirement": nearest,
            })

    doc.close()
    print(f"  [启发式] 检测到 {len(fields)} 个字段（{len(lines)}条填写线）")
    return fields
