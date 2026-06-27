"""
AutoFill AI - 智能表单自动填写系统 (后端入口)

使用方式:
  python -m autofill_ai <pdf表单路径> <资料文件夹路径> [--output 输出路径]
  python -m autofill_ai form.pdf ./my_profile/
  python -m autofill_ai form.pdf ./my_profile/ --output filled.pdf
  python -m autofill_ai form.pdf ./my_profile/ --no-ml

依赖:
  已安装 skills:
    - PyMuPDF (pymupdf4llm): PDF解析与LLM格式转换
    - CommonForms (02-):    ML模型检测静态表单字段
  可选 skills (备用):
    - Zerox (08-):         OCR处理扫描件
    - MinerU (03-):        高精度文档解析
"""

import argparse
import sys
from pathlib import Path

from .scanner import scan_folder
from .extractor import extract_profile
from .detector import detect_fields
from .mapper import match_fields, print_match_summary
from .filler import fill_form


def main():
    parser = argparse.ArgumentParser(
        description="AutoFill AI - 智能表单自动填写系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m autofill_ai 实习申请表.pdf ./个人资料/
  python -m autofill_ai form.pdf ./data/ --output result.pdf
  python -m autofill_ai form.pdf ./data/ --no-ml   (仅AcroForm，不加载ML模型)
        """,
    )
    parser.add_argument(
        "pdf_path", type=str,
        help="需要填写的PDF表单文件路径",
    )
    parser.add_argument(
        "profile_dir", type=str,
        help="包含个人资料文件的文件夹路径 (支持 .txt .json .md)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="输出PDF路径 (默认: [原文件名]_已填写.pdf)",
    )
    parser.add_argument(
        "--no-ml", action="store_true",
        help="禁用CommonForms ML模型检测 (仅使用AcroForm)",
    )
    parser.add_argument(
        "--font-size", type=int, default=10,
        help="默认字号 (默认: 10)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅解析和匹配，不生成输出文件",
    )
    args = parser.parse_args()

    # 验证输入
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"[错误] PDF文件不存在: {pdf_path}")
        sys.exit(1)

    profile_dir = Path(args.profile_dir)
    if not profile_dir.exists():
        print(f"[错误] 资料文件夹不存在: {profile_dir}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = pdf_path.parent / f"{pdf_path.stem}_已填写.pdf"

    print("=" * 60)
    print("  AutoFill AI - 智能表单自动填写系统")
    print(f"  PDF表单: {pdf_path}")
    print(f"  资料目录: {profile_dir}")
    print(f"  输出文件: {output_path}")
    print(f"  ML检测: {'禁用' if args.no_ml else '启用 (CommonForms FFDNet-L)'}")
    print("=" * 60)

    # ---- 模块1: 文件感知 ----
    print(f"\n{'='*50}")
    print("[模块1] 文件感知器 - 扫描资料文件夹")
    print(f"{'='*50}")
    files = scan_folder(str(profile_dir))
    total_files = sum(len(v) for v in files.values())
    print(f"  -> 发现 {total_files} 个文件:"
          f" 文本={len(files['profile_files'])},"
          f" JSON={len(files['json_files'])},"
          f" 图片={len(files['image_files'])}")
    if total_files == 0:
        print("[错误] 资料文件夹中没有可处理的文件。")
        sys.exit(1)

    # ---- 模块2: 资料提取 ----
    print(f"\n{'='*50}")
    print("[模块2] 资料提取引擎 - 结构化为JSON")
    print(f"{'='*50}")
    profile = extract_profile(str(profile_dir))
    if not profile:
        print("[错误] 未能从资料文件中提取到任何字段。")
        sys.exit(1)
    print(f"  -> 提取到 {len(profile)} 个有效字段")

    # ---- 模块3: PDF表单检测 ----
    print(f"\n{'='*50}")
    print("[模块3] 文档理解定位器 - 检测表单字段")
    print(f"{'='*50}")
    use_ml = not args.no_ml
    requirements = detect_fields(str(pdf_path), use_ml=use_ml)
    if not requirements:
        print("[错误] PDF中未检测到任何表单字段。")
        sys.exit(1)
    print(f"  -> 共检测到 {len(requirements)} 个表单字段")

    # ---- 语义映射 ----
    print(f"\n{'='*50}")
    print("[映射引擎] 智能匹配 表单需求 <-> 个人资料")
    print(f"{'='*50}")
    tasks = match_fields(requirements, profile)
    print_match_summary(tasks)

    matched_count = sum(1 for t in tasks if t["matched"])
    if matched_count == 0:
        print("\n[警告] 没有字段可以匹配，输出文件将为空。")

    # ---- 模块4: PDF填写 ----
    if not args.dry_run:
        print(f"\n{'='*50}")
        print("[模块4] 内容合成渲染器 - 填写PDF")
        print(f"{'='*50}")
        fill_form(
            str(pdf_path),
            tasks,
            str(output_path),
            font_size=args.font_size,
        )
        print(f"\n{'='*60}")
        print(f"  填写完成！")
        print(f"  结果: {output_path}")
        print(f"  已填: {matched_count}/{len(tasks)} 个字段")
        print(f"{'='*60}")
    else:
        print(f"\n[Dry-Run] 仅解析，未生成输出文件。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
