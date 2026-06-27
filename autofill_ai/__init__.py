"""
AutoFill AI - 智能表单自动填写系统 (后端)

基于四模块流水线:
  模块1: 文件感知器 - 扫描资料文件夹
  模块2: 资料提取引擎 - 将个人资料结构化为JSON
  模块3: 文档理解定位器 - 解析PDF表单字段与坐标 (AcroForm + CommonForms ML)
  模块4: 内容合成渲染器 - 精准坐标回填生成最终PDF

使用方式:
  python -m autofill_ai <pdf表单路径> <资料文件夹路径> [--output 输出路径]
"""

__version__ = "1.0.0"
