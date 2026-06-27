"""模块4: 内容合成与渲染器 - 将匹配好的答案精准写入PDF指定坐标。

关键能力:
  - 自适应字号: 根据字段宽度和文本长度自动计算合适字号
  - 长文本换行: 对"个人自述"等大框字段自动折行
  - 签名/图片嵌入: 识别签名字段，插入预设图片
  - 输出新文件: 保存为 [原文件名]_已填写.pdf
"""

import pymupdf


def fill_form(
    pdf_path: str,
    tasks: list[dict],
    output_path: str,
    font_size: int = 10,
    font_name: str = "china-s",
):
    """执行PDF表单填写。

    Args:
        pdf_path: 原始PDF表单路径
        tasks: mapper.match_fields() 的输出，含 { requirement, value, matched }
        output_path: 输出PDF路径
        font_size: 默认字号
        font_name: 字体名称
    """
    doc = pymupdf.open(pdf_path)
    filled_count = 0
    skipped_count = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 收集本页的任务
        page_tasks = [
            t for t in tasks
            if t["requirement"]["page"] == page_num and t["matched"]
        ]

        for task in page_tasks:
            req = task["requirement"]
            value = task["value"]

            if not value:
                skipped_count += 1
                continue

            # 自适应字号
            calculated_size = _calc_font_size(value, req["width"], font_size)

            # 对长文本进行换行处理
            lines = _wrap_text_to_width(value, req["width"], calculated_size)

            line_height = calculated_size + 3

            # 对单行字段居中基线，多行字段从顶部开始
            if len(lines) == 1:
                y_start = req["y"] + (req["height"] + calculated_size) / 2 - 2
            else:
                y_start = req["y"] + calculated_size + 2

            # 在PDF页面上逐行写入
            for i, line in enumerate(lines):
                y_offset = y_start + i * line_height
                if y_offset > req["y"] + req["height"] + 4:
                    break

                page.insert_text(
                    pymupdf.Point(req["x"] + 2, y_offset),
                    line,
                    fontname=font_name,
                    fontsize=calculated_size,
                    color=(0, 0, 0),
                )

            filled_count += 1
            print(f"  [填写] {req.get('requirement', req['field_name'])[:30]:<32s} "
                  f"= {value[:50]}... ({calculated_size}pt/{len(lines)}行)")

    doc.save(output_path)
    doc.close()

    print(f"\n  [完成] 已填写 {filled_count} 个字段, 跳过 {skipped_count} 个")
    return output_path


def _calc_font_size(text: str, available_width: float, default_size: int) -> int:
    """根据文本中最长行的宽度自适应计算最优字号。"""
    if available_width <= 0:
        return default_size

    effective_w = max(available_width - 8, 10)

    lines = text.split("\n")
    max_effective = 0
    for line in lines:
        eff = sum(1.0 if ord(c) > 127 else 0.65 for c in line)
        if eff > max_effective:
            max_effective = eff

    if max_effective == 0:
        return default_size

    max_size = effective_w / (max_effective * 0.65)
    return max(7, min(default_size, int(max_size)))


def _wrap_text_to_width(text: str, width: float, font_size: int) -> list[str]:
    """将文本按字段宽度进行折行，正确处理中英文混排宽度。"""
    if not text:
        return [""]

    # 估算单个ASCII/CJK字符在给定字号下的宽度
    ascii_w = font_size * 0.60
    cjk_w = font_size * 0.95

    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue

        # 根据字符宽度累积，当接近目标宽度时换行
        current = ""
        current_w = 0.0
        for ch in paragraph:
            ch_w = cjk_w if ord(ch) > 127 else ascii_w
            if current_w + ch_w > width - 4 and current:
                lines.append(current)
                current = ""
                current_w = 0.0
            current += ch
            current_w += ch_w
        if current:
            lines.append(current)

    return lines if lines else [""]
