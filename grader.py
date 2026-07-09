import os
import re
import json
import google.generativeai as genai

# Default rubric mapping rules
HEURISTIC_MAPPING = [
    {"keywords": ["cấu trúc", "structure", "thư mục"], "key": "structure"},
    {"keywords": ["đọc", "readability", "chất lượng code"], "key": "readability"},
    {"keywords": ["tách widget", "widget con", "build()"], "key": "widgets"},
    {"keywords": ["logic khỏi ui", "tách logic", "service", "controller"], "key": "logic"},
    {"keywords": ["state", "trạng thái", "provider", "bloc", "riverpod"], "key": "state"},
    {"keywords": ["navigation", "điều hướng", "route"], "key": "navigation"},
    {"keywords": ["model", "dữ liệu", "json"], "key": "models"},
    {"keywords": ["lỗi", "ngoại lệ", "try-catch", "validate"], "key": "errors"},
    {"keywords": ["responsive", "overflow", "tràn"], "key": "responsive"},
    {"keywords": ["tái sử dụng", "constants", "lặp"], "key": "reusability"},
    {"keywords": ["tài nguyên", "resource", "assets", "pubspec"], "key": "resources"},
    {"keywords": ["hiệu năng", "performance", "rebuild"], "key": "performance"},
    {"keywords": ["mở rộng", "extens"], "key": "extensibility"},
    {"keywords": ["convention", "quy ước", "pascal", "camel"], "key": "convention"},
    {"keywords": ["test", "kiểm thử", "hoàn thiện"], "key": "testing"}
]

def parse_rubric(criteria_text):
    """
    Parses custom markdown criteria text and extracts names and weights.
    Format: 'Name | Description | Weight%' or 'Name | Weight%'
    """
    rubric = {}
    if not criteria_text:
        return None
        
    lines = criteria_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or '|' not in line:
            continue
            
        parts = [p.strip() for p in line.split('|')]
        # Filter table header
        if any(h in parts[0].lower() for h in ["nhóm tiêu chí", "tiêu chí", "rubric", "---"]):
            continue
            
        name = parts[0]
        
        # Try to find weight (percentage) in the last columns
        weight = 0.0
        weight_found = False
        for part in reversed(parts[1:]):
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', part)
            if match:
                weight = float(match.group(1)) / 100.0
                weight_found = True
                break
                
        if not weight_found:
            # Fallback weight if not explicitly written
            weight = 0.05
            
        # Map to heuristic key
        mapped_key = "readability" # default fallback key
        for item in HEURISTIC_MAPPING:
            if any(kw in name.lower() for kw in item["keywords"]):
                mapped_key = item["key"]
                break
                
        rubric[name] = {"weight": weight, "key": mapped_key}
        
    return rubric if len(rubric) > 0 else None

def get_heuristic_score_for_key(key, analysis):
    """
    Calculate the score and feedback for a specific heuristic key.
    """
    if key == "structure":
        struct_score = analysis["structure"]["folder_structure_score"] / 10.0
        return {
            "score": struct_score,
            "feedback": f"Cấu trúc thư mục đạt {struct_score*10}%. " + 
                        ("; ".join(analysis["structure"]["details"]) if analysis["structure"]["details"] else "")
        }
        
    elif key == "readability":
        readability = 10.0
        large_files_count = len(analysis["stats"]["large_files"])
        readability -= min(3.0, large_files_count * 1.0)
        return {
            "score": readability,
            "feedback": f"Phân tích kích thước file. Có {large_files_count} file lớn (>300 dòng) ảnh hưởng tới khả năng đọc."
        }
        
    elif key == "widgets":
        widget_score = 9.0
        large_files = analysis["stats"]["large_files"]
        for lf in large_files:
            if "screen" in lf["file"].lower() or "widget" in lf["file"].lower():
                widget_score -= 1.0
        return {
            "score": max(5.0, widget_score),
            "feedback": "Cần xem xét tách các screen/widget con ở những file dài."
        }
        
    elif key == "logic":
        logic_score = 7.0
        if len(analysis["heuristics"]["api_calls_in_build"]) > 0:
            logic_score -= 3.0
        return {
            "score": max(4.0, logic_score),
            "feedback": f"Có {len(analysis['heuristics']['api_calls_in_build'])} vi phạm gọi API trực tiếp trong build()."
        }
        
    elif key == "state":
        has_state_mgr = len(analysis["heuristics"]["state_management"]) > 0
        state_score = 9.0 if has_state_mgr else 6.0
        feedback_sm = f"Sử dụng quản lý state: {', '.join(analysis['heuristics']['state_management'])}" if has_state_mgr else "Không tìm thấy Provider, Bloc, Riverpod hay GetX."
        return {
            "score": state_score,
            "feedback": feedback_sm
        }
        
    elif key == "navigation":
        nav_score = 8.5 if len(analysis["heuristics"]["navigation_patterns"]) > 0 else 6.0
        return {
            "score": nav_score,
            "feedback": f"Tìm thấy điều hướng trong {len(analysis['heuristics']['navigation_patterns'])} files."
        }
        
    elif key == "models":
        has_models = analysis["structure"]["has_models"]
        models_score = 9.0 if has_models else 6.0
        feedback_models = "Có định nghĩa models rõ ràng." if has_models else "Không tìm thấy thư mục model. Khuyến khích dùng class thay vì Map thô."
        return {
            "score": models_score,
            "feedback": feedback_models
        }
        
    elif key == "errors":
        err_count = analysis["heuristics"]["error_handling_count"]
        err_score = min(10.0, 5.0 + err_count * 0.5)
        return {
            "score": err_score,
            "feedback": f"Phát hiện {err_count} khối xử lý try-catch."
        }
        
    elif key == "responsive":
        resp_widgets = analysis["heuristics"]["responsive_widgets_used"]
        resp_score = min(10.0, 5.0 + len(resp_widgets) * 1.5)
        return {
            "score": resp_score,
            "feedback": f"Sử dụng các widgets layout/responsive: {', '.join(resp_widgets)}"
        }
        
    elif key == "reusability":
        return {
            "score": 7.5,
            "feedback": "Cần xem xét để tránh lặp code. Tách các hằng số dùng chung vào Core/Constants."
        }
        
    elif key == "resources":
        has_assets = analysis["heuristics"]["pubspec_details"].get("has_assets", False)
        res_score = 9.0 if has_assets else 6.0
        return {
            "score": res_score,
            "feedback": "Đã định nghĩa tài nguyên trong pubspec.yaml." if has_assets else "Không cấu hình assets trong pubspec.yaml."
        }
        
    elif key == "performance":
        perf_score = 9.0
        if len(analysis["heuristics"]["api_calls_in_build"]) > 0:
            perf_score -= 2.0
        return {
            "score": perf_score,
            "feedback": "Không có gọi API lặp trong build() nếu đạt 9/10."
        }
        
    elif key == "extensibility":
        return {
            "score": 7.5,
            "feedback": "Khả năng mở rộng phụ thuộc vào cấu trúc module hóa lib/."
        }
        
    elif key == "convention":
        violations = len(analysis["stats"]["naming_violations"])
        conv_score = max(4.0, 10.0 - violations * 0.5)
        return {
            "score": conv_score,
            "feedback": f"Phát hiện {violations} lỗi convention (tên file hoặc tên class)."
        }
        
    elif key == "testing":
        return {
            "score": 6.0,
            "feedback": "Cần bổ sung thêm unit test hoặc widget test."
        }
        
    return {"score": 7.0, "feedback": "Đánh giá tiêu chí chung."}

def fallback_heuristic_grade(analysis, parsed_rubric=None):
    """
    Generate heuristic scores based on the static analysis and dynamic rubric.
    """
    scores = {}
    
    # Use parsed rubric or fallback to default
    rubric_to_use = parsed_rubric
    if not rubric_to_use:
        # Reconstruct default
        from grader import DEFAULT_RUBRIC
        rubric_to_use = DEFAULT_RUBRIC
        
    total_score = 0.0
    total_weight = 0.0
    
    for name, item in rubric_to_use.items():
        res = get_heuristic_score_for_key(item["key"], analysis)
        scores[name] = res
        total_score += res["score"] * item["weight"]
        total_weight += item["weight"]
        
    # Normalize score if weights do not sum up to 1.0
    final_score = (total_score / total_weight) if total_weight > 0 else total_score
    
    return {
        "overall_score": round(final_score, 2),
        "criteria_breakdown": scores,
        "summary": "Kết quả được chấm điểm tự động bằng hệ thống heuristics tĩnh. Cung cấp Gemini API Key để được đánh giá sâu sắc hơn.",
        "warnings": analysis["heuristics"]["api_calls_in_build"] + analysis["stats"]["naming_violations"]
    }

def get_key_files_content(project_path):
    """
    Get content of primary flutter files to provide context to Gemini
    """
    file_contents = {}
    lib_path = os.path.join(project_path, "lib")
    if not os.path.exists(lib_path):
        return file_contents
        
    targets = ['main.dart', 'pubspec.yaml']
    
    for root, dirs, files in os.walk(lib_path):
        for file in files:
            if file.endswith('.dart') and len(file_contents) < 12:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                
                is_key = any(k in file.lower() for k in ['controller', 'provider', 'bloc', 'model', 'screen', 'service', 'main'])
                if is_key or len(file_contents) < 5:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            file_contents[rel_path] = "".join(lines[:150]) + ("\n... [Đã cắt bớt file]" if len(lines) > 150 else "")
                    except:
                        pass
                        
    pub_path = os.path.join(project_path, 'pubspec.yaml')
    if os.path.exists(pub_path):
        try:
            with open(pub_path, 'r', encoding='utf-8') as f:
                file_contents['pubspec.yaml'] = f.read()
        except:
            pass
            
    return file_contents

def grade_project_with_gemini(project_path, api_key, analysis_report, custom_criteria_text=None):
    parsed_rubric = parse_rubric(custom_criteria_text)
    
    if not api_key:
        return fallback_heuristic_grade(analysis_report, parsed_rubric)
        
    try:
        genai.configure(api_key=api_key)
        
        # Prepare context of codebase
        key_files = get_key_files_content(project_path)
        codebase_summary = "\n\n".join([f"--- FILE: {path} ---\n{content}" for path, content in key_files.items()])
        
        # Default criteria if none provided
        criteria_str = custom_criteria_text
        if not criteria_str:
            criteria_str = "Cấu trúc project | 10%\nCode dễ đọc | 10%\nTách UI widget | 10%\nTách logic khỏi UI | 10%\nQuản lý state | 10%\nNavigation | 8%\nModel | 8%\nXử lý lỗi | 8%\nResponsive UI | 8%\nTái sử dụng | 6%\nHiệu năng | 6%\nHoàn thiện | 6%\nQuản lý tài nguyên | 6%\nCode mở rộng | 6%\nConvention | 6%"
            parsed_rubric = parse_rubric(criteria_str)

        # Dynamically build JSON schema requirements
        schema_examples = {}
        weight_list_str = []
        for name, item in parsed_rubric.items():
            schema_examples[name] = {
                "score": 0.0,
                "feedback": "Lời khuyên/nhận xét cho tiêu chí này"
            }
            weight_list_str.append(f"- {name}: {int(item['weight']*100)}%")
            
        weights_instruction = "\n".join(weight_list_str)

        prompt = f"""
Bạn là giảng viên hoặc chuyên gia review code di động (Flutter/Dart). Nhiệm vụ của bạn là chấm điểm bài tập lớn của sinh viên dựa trên source code được cung cấp dưới đây và báo cáo phân tích tĩnh (Static Analysis).

Dưới đây là một số file chính trong dự án Flutter:
{codebase_summary}

Báo cáo phân tích tĩnh (thư mục, vi phạm đặt tên, file lớn):
{json.dumps(analysis_report, ensure_ascii=False, indent=2)}

Tiêu chí chấm điểm:
{criteria_str}

Hãy trả về kết quả dưới định dạng JSON duy nhất. JSON trả về phải khớp với cấu trúc sau:
{{
  "overall_score": <điểm tổng hợp từ 0.0 đến 10.0, tính theo trọng số và làm tròn đến 2 chữ số thập phân>,
  "criteria_breakdown": {json.dumps(schema_examples, ensure_ascii=False, indent=4)},
  "summary": "<Tổng hợp điểm mạnh và điểm yếu lớn nhất của dự án>",
  "warnings": [
     "<Cảnh báo lỗi/Anti-pattern 1>",
     "<Cảnh báo lỗi/Anti-pattern 2>"
  ]
}}

LƯU Ý: 
- Tính toán điểm tổng hợp (overall_score) dựa trên trọng số sau:
{weights_instruction}
- Trả về đúng các tiêu chí được định nghĩa trong JSON breakdown ở trên.
- Đưa ra phản hồi bằng Tiếng Việt thân thiện, mang tính xây dựng và chính xác cao.
- Không trả về bất kỳ text nào ngoài JSON thô.
"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        # Fallback to heuristic
        res = fallback_heuristic_grade(analysis_report, parsed_rubric)
        res["summary"] = f"Lỗi gọi Gemini API ({str(e)}). Đã chuyển sang chế độ chấm tĩnh tự động."
        return res

# Retain default rubric variable for fallback compatibility
DEFAULT_RUBRIC = {
    "1. Cấu trúc project rõ ràng": {"weight": 0.10, "key": "structure"},
    "2. Code dễ đọc, dễ hiểu": {"weight": 0.10, "key": "readability"},
    "3. Tách UI thành các widget nhỏ": {"weight": 0.10, "key": "widgets"},
    "4. Tách logic khỏi UI": {"weight": 0.10, "key": "logic"},
    "5. Quản lý state hợp lý": {"weight": 0.10, "key": "state"},
    "6. Xử lý navigation đúng": {"weight": 0.08, "key": "navigation"},
    "7. Quản lý dữ liệu bằng model": {"weight": 0.08, "key": "models"},
    "8. Xử lý lỗi và ngoại lệ": {"weight": 0.08, "key": "errors"},
    "9. Giao diện responsive và không bị overflow": {"weight": 0.08, "key": "responsive"},
    "10. Tái sử dụng code": {"weight": 0.06, "key": "reusability"},
    "11. Quản lý tài nguyên tốt": {"weight": 0.06, "key": "resources"},
    "12. Hiệu năng cơ bản": {"weight": 0.06, "key": "performance"},
    "13. Code có khả năng mở rộng": {"weight": 0.06, "key": "extensibility"},
    "14. Tuân thủ coding convention": {"weight": 0.06, "key": "convention"},
    "15. Có kiểm thử hoặc kiểm tra chức năng cơ bản": {"weight": 0.06, "key": "testing"}
}
