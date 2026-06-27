"""模块2: 个人资料提取引擎 - 将原始资料文件结构化为标准JSON。

处理流程:
  1. 读取 TXT/JSON/MD 文件
  2. 规则+正则提取关键字段
  3. 输出统一的 profile JSON: { "name": "张三", "phone": "...", ... }
"""

import json
import re
from pathlib import Path


def extract_profile(folder_path: str) -> dict:
    """从资料文件夹中提取并合并所有个人资料，返回统一的结构化字典。"""
    from .scanner import scan_folder

    files = scan_folder(folder_path)
    profile = {}

    # 1) 优先加载 JSON 文件（精确结构化数据）
    for jf in files["json_files"]:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                profile.update(data)
                print(f"  [提取] JSON: {jf.name} -> {len(data)} 个字段")
        except Exception as e:
            print(f"  [警告] JSON解析失败 {jf.name}: {e}")

    # 2) 解析 TXT/MD 文本资料
    for tf in files["profile_files"]:
        try:
            extracted = parse_text_file(tf)
            profile.update(extracted)
            print(f"  [提取] 文本: {tf.name} -> {len(extracted)} 个字段")
        except Exception as e:
            print(f"  [警告] 文本解析失败 {tf.name}: {e}")

    # 3) 后处理: 清理空白值
    profile = {k: v for k, v in profile.items() if v and v != "N/A"}

    return profile


def parse_text_file(file_path: Path) -> dict:
    """解析文本文件，用正则提取关键字段。"""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    profile = {}

    # 字段提取规则（中文 + 英文 key）
    # 单行字段用 [^\n]+ 防止贪婪跨行匹配
    single_line_rules = {
        "name": [r"姓名[:：]\s*([^\n]+)", r"Name[:：]\s*([^\n]+)"],
        "name_en": [r"英文名[:：]\s*([^\n]+)", r"English Name[:：]\s*([^\n]+)"],
        "gender": [r"性别[:：]\s*([^\n]+)", r"Gender[:：]\s*([^\n]+)"],
        "dob": [r"出生日期[:：]\s*([^\n]+)", r"Date of Birth[:：]\s*([^\n]+)"],
        "phone": [r"电话[:：]\s*([^\n]+)", r"联系[电话方式]+[:：]\s*([^\n]+)",
                  r"Phone[:：]\s*([^\n]+)"],
        "email": [r"邮箱[:：]\s*([^\n]+)", r"电子邮箱[:：]\s*([^\n]+)",
                  r"Email[:：]\s*([^\n]+)"],
        "address": [r"地址[:：]\s*([^\n]+)", r"Address[:：]\s*([^\n]+)"],
        "university": [r"当前学历[:：]\s*(\S+)", r"大学[:：]\s*([^\n]+)",
                       r"学校[:：]\s*([^\n]+)", r"University[:：]\s*([^\n]+)"],
        "major": [r"当前学历[:：].+?(\S+专业)",
                  r"Major[:：]\s*([^\n]+)"],
        "gpa": [r"GPA[:：]\s*([^\n]+)", r"绩点[:：]\s*([^\n]+)"],
        "grad_year": [r"毕业年份[:：]\s*([^\n]+)", r"Graduation[:：]\s*([^\n]+)"],
        "education_level": [r"当前学历[:：]\s*\S+\s+(\S+)",
                            r"学[历位][:：]\s*([^\n]+)",
                            r"Education Level[:：]\s*([^\n]+)"],
    }

    # 多行字段用 .+? 非贪婪跨行匹配（终止于空行或下一个标签行）
    multi_line_rules = {
        "skills": [r"技能特长[:：]\s*(.+?)(?:\n\n|\Z)",
                   r"编程语言[:：]\s*(.+?)(?:\n\n|\Z)"],
        "languages": [r"语言能力[:：]\s*(.+?)(?:\n\n|\Z)"],
        "project_experience": [r"项目经验[:：]\s*(.+?)(?:\n\n|\Z)"],
        "self_intro": [r"个人自述[:：]\s*(.+?)(?:\n\n|\Z)",
                       r"自我[介绍评价][:：]\s*(.+?)(?:\n\n|\Z)"],
        "awards": [r"获奖[与和]?\S*[:：]\s*(.+?)(?:\n\n|\Z)",
                   r"获奖[与和][:：]?\s*(.+?)(?:\n\n|\Z)"],
    }

    # 匹配单行字段
    for field, patterns in single_line_rules.items():
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip().rstrip(",")
                if field == "university":
                    value = value.split()[0] if value else ""
                if value:
                    profile[field] = value
                break

    # 匹配多行字段
    for field, patterns in multi_line_rules.items():
        for pat in patterns:
            match = re.search(pat, text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip().rstrip(",")
                if value:
                    profile[field] = value
                break

    return profile
