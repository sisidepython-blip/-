"""语义映射引擎 - 将PDF表单字段需求与个人资料字段进行智能匹配。

策略:
  1. 精确匹配: field_name 直接命中 profile key
  2. 关键词匹配: "Applicant Name" -> profile["name_en"]
  3. 语义映射表: requirement 中文描述 → profile key
"""

# 中文/英文 字段需求 → 个人资料 profile key 映射表
REQUIREMENT_TO_PROFILE_KEY = {
    # 姓名
    "申请人姓名": "name", "姓名": "name", "名字": "name",
    "applicant name": "name_en", "applicant_name": "name_en",
    "full name": "name_en", "name": "name_en",
    # 性别
    "性别": "gender", "gender": "gender", "sex": "gender",
    # 出生日期
    "出生日期": "dob", "出生年月": "dob",
    "date of birth": "dob", "date_of_birth": "dob", "dob": "dob",
    # 联系方式
    "联系电话": "phone", "电话": "phone", "手机": "phone",
    "phone": "phone", "telephone": "phone", "mobile": "phone",
    "电子邮箱": "email", "邮箱": "email", "email": "email",
    "地址": "address", "address": "address",
    # 教育
    "就读大学": "university", "学校": "university",
    "university": "university", "school": "university",
    "专业": "major", "major": "major",
    "gpa": "gpa", "gpa成绩": "gpa", "绩点": "gpa",
    "毕业年份": "grad_year", "graduation year": "grad_year",
    "grad_year": "grad_year",
    "当前学历": "education_level", "education level": "education_level",
    "学历": "education_level",
    # 技能
    "技能特长": "skills", "技能": "skills", "skills": "skills",
    "语言能力": "languages", "languages": "languages",
    # 经验
    "项目经验": "project_experience",
    "project experience": "project_experience",
    # 其他
    "个人自述": "self_intro", "自我评价": "self_intro",
    "self introduction": "self_intro",
    "获奖": "awards", "awards": "awards",
}


# field_type 默认值映射（在profile中找不到时使用）
TYPE_DEFAULTS = {
    "CheckBox": "Yes",
    "ChoiceButton": "Yes",
}


def match_fields(requirements: list[dict], profile: dict) -> list[dict]:
    """将检测到的表单字段与个人资料进行匹配。

    Args:
        requirements: detector.detect_fields() 的输出
        profile: extractor.extract_profile() 的输出

    Returns:
        填充任务列表: [{ "req": {...}, "value": "填写内容", "matched": true/false }]
    """
    tasks = []

    for req in requirements:
        task = {
            "requirement": req,
            "value": "",
            "matched": False,
            "profile_key": None,
        }

        # 策略1: field_name 直接命中 profile key
        fn = req["field_name"].lower().replace("-", "_").replace(" ", "_")
        if fn in profile:
            task["value"] = str(profile[fn])
            task["matched"] = True
            task["profile_key"] = fn

        # 策略2: requirement 关键词匹配
        if not task["matched"]:
            req_text = req.get("requirement", "").strip().lower()
            req_text = req_text.rstrip(":：_* ")
            if req_text in REQUIREMENT_TO_PROFILE_KEY:
                pk = REQUIREMENT_TO_PROFILE_KEY[req_text]
                if pk in profile:
                    task["value"] = str(profile[pk])
                    task["matched"] = True
                    task["profile_key"] = pk

        # 策略3: 模糊匹配 - 在映射表中查找包含关系
        if not task["matched"]:
            req_text = req.get("requirement", "").strip().lower()
            for req_key, prof_key in REQUIREMENT_TO_PROFILE_KEY.items():
                if req_key in req_text or req_text in req_key:
                    if prof_key in profile:
                        task["value"] = str(profile[prof_key])
                        task["matched"] = True
                        task["profile_key"] = prof_key
                        break

        # 策略4: field_name 部分匹配 profile key
        if not task["matched"]:
            for pk, pv in profile.items():
                if pk.lower() in fn or fn in pk.lower():
                    task["value"] = str(pv)
                    task["matched"] = True
                    task["profile_key"] = pk
                    break

        # 特殊类型: CheckBox 默认填 "Yes" 或映射布尔值
        if not task["matched"] and req["field_type"] in TYPE_DEFAULTS:
            task["value"] = TYPE_DEFAULTS[req["field_type"]]
            task["matched"] = True

        tasks.append(task)

    return tasks


def print_match_summary(tasks: list[dict]):
    """打印匹配摘要。"""
    matched = sum(1 for t in tasks if t["matched"])
    total = len(tasks)
    print(f"\n  [映射] 字段匹配结果: {matched}/{total} 已匹配")
    for t in tasks:
        status = "+" if t["matched"] else "-"
        req_name = (t["requirement"].get("requirement", "")
                    or t["requirement"].get("field_name", ""))[:30]
        value_preview = (t["value"][:40] + "..." if len(t["value"]) > 40
                         else t["value"])
        print(f"    [{status}] {req_name:<32s} -> {value_preview}")
