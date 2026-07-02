import os
import json
import google.generativeai as genai

# Default rubric rules in case Gemini is not used or fails
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

def fallback_heuristic_grade(analysis):
    """
    Generate heuristic scores based on the static analysis.
    """
    scores = {}
    
    # 1. Structure
    struct_score = analysis["structure"]["folder_structure_score"] / 10.0
    scores["1. Cấu trúc project rõ ràng"] = {
        "score": struct_score,
        "feedback": f"Cấu trúc thư mục đạt {struct_score*10}%. " + 
                    ("; ".join(analysis["structure"]["details"]) if analysis["structure"]["details"] else "")
    }
    
    # 2. Readability
    readability = 10.0
    large_files_count = len(analysis["stats"]["large_files"])
    readability -= min(3.0, large_files_count * 1.0)
    scores["2. Code dễ đọc, dễ hiểu"] = {
        "score": readability,
        "feedback": f"Đánh giá sơ bộ qua kích thước file. Có {large_files_count} file quá dài cần tối ưu hóa."
    }
    
    # 3. Widget decomposition
    widget_score = 9.0
    large_files = analysis["stats"]["large_files"]
    for lf in large_files:
        if "screen" in lf["file"].lower() or "widget" in lf["file"].lower():
            widget_score -= 1.0
    widget_score = max(5.0, widget_score)
    scores["3. Tách UI thành các widget nhỏ"] = {
        "score": widget_score,
        "feedback": "Cần xem xét chia nhỏ các widgets ở các file có dòng code lớn hơn 300 dòng."
    }
    
    # 4. Logic Separation
    logic_score = 7.0
    if len(analysis["heuristics"]["api_calls_in_build"]) > 0:
        logic_score -= 3.0
    scores["4. Tách logic khỏi UI"] = {
        "score": max(4.0, logic_score),
        "feedback": f"Có {len(analysis['heuristics']['api_calls_in_build'])} vi phạm gọi API trực tiếp trong hàm build."
    }
    
    # 5. State Management
    has_state_mgr = len(analysis["heuristics"]["state_management"]) > 0
    state_score = 9.0 if has_state_mgr else 6.0
    feedback_sm = f"Sử dụng các thư viện quản lý state: {', '.join(analysis['heuristics']['state_management'])}" if has_state_mgr else "Không tìm thấy thư viện quản lý state chính thống (Bloc, Provider, Riverpod...). Cần bổ sung nếu dự án lớn."
    scores["5. Quản lý state hợp lý"] = {
        "score": state_score,
        "feedback": feedback_sm
    }
    
    # 6. Navigation
    nav_score = 8.5 if len(analysis["heuristics"]["navigation_patterns"]) > 0 else 6.0
    scores["6. Xử lý navigation đúng"] = {
        "score": nav_score,
        "feedback": f"Tìm thấy điều hướng trong {len(analysis['heuristics']['navigation_patterns'])} files."
    }
    
    # 7. Data Models
    has_models = analysis["structure"]["has_models"]
    models_score = 9.0 if has_models else 6.0
    feedback_models = "Có thư mục model và định nghĩa cấu trúc dữ liệu." if has_models else "Không tìm thấy thư mục model. Sinh viên có thể đang lạm dụng Map để truyền nhận dữ liệu."
    scores["7. Quản lý dữ liệu bằng model"] = {
        "score": models_score,
        "feedback": feedback_models
    }
    
    # 8. Error handling
    err_count = analysis["heuristics"]["error_handling_count"]
    err_score = min(10.0, 5.0 + err_count * 0.5)
    scores["8. Xử lý lỗi và ngoại lệ"] = {
        "score": err_score,
        "feedback": f"Tìm thấy {err_count} khối try-catch trong dự án."
    }
    
    # 9. Responsive
    resp_widgets = analysis["heuristics"]["responsive_widgets_used"]
    resp_score = min(10.0, 5.0 + len(resp_widgets) * 1.5)
    scores["9. Giao diện responsive và không bị overflow"] = {
        "score": resp_score,
        "feedback": f"Sử dụng các widgets responsive/layout: {', '.join(resp_widgets)}"
    }
    
    # 10. Reusability
    scores["10. Tái sử dụng code"] = {
        "score": 7.5,
        "feedback": "Cần xem xét kỹ để xác định các UI lặp lại. Khuyến nghị tách các hằng số màu sắc, chữ ra file Core/Constants."
    }
    
    # 11. Resource management
    has_assets = analysis["heuristics"]["pubspec_details"].get("has_assets", False)
    res_score = 9.0 if has_assets else 6.0
    scores["11. Quản lý tài nguyên tốt"] = {
        "score": res_score,
        "feedback": "Đã cấu hình assets trong pubspec.yaml." if has_assets else "Không tìm thấy cấu hình assets trong pubspec.yaml."
    }
    
    # 12. Performance
    perf_score = 9.0
    if len(analysis["heuristics"]["api_calls_in_build"]) > 0:
        perf_score -= 2.0
    scores["12. Hiệu năng cơ bản"] = {
        "score": perf_score,
        "feedback": "Điểm hiệu năng sơ bộ dựa trên các quy tắc không gọi API trong build."
    }
    
    # 13. Extensibility
    scores["13. Code có khả năng mở rộng"] = {
        "score": 7.5,
        "feedback": "Cần cấu trúc sạch hơn và hạn chế phụ thuộc chéo giữa các Widget."
    }
    
    # 14. Convention
    violations = len(analysis["stats"]["naming_violations"])
    conv_score = max(4.0, 10.0 - violations * 0.5)
    scores["14. Tuân thủ coding convention"] = {
        "score": conv_score,
        "feedback": f"Phát hiện {violations} vi phạm đặt tên (file/class)."
    }
    
    # 15. Testing
    scores["15. Có kiểm thử hoặc kiểm tra chức năng cơ bản"] = {
        "score": 6.0,
        "feedback": "Chưa phát hiện các file test tự động. Chấm dựa trên kiểm thử thủ công chức năng."
    }
    
    # Calculate weighted total
    total_score = 0.0
    for name, item in DEFAULT_RUBRIC.items():
        total_score += scores[name]["score"] * item["weight"]
        
    return {
        "overall_score": round(total_score, 2),
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
        
    # Standard important files
    targets = ['main.dart', 'pubspec.yaml']
    
    # Let's also grab a few other sample files from controllers/screens/models to stay under token limits
    for root, dirs, files in os.walk(lib_path):
        for file in files:
            if file.endswith('.dart') and len(file_contents) < 12:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                
                # Prioritize key parts
                is_key = any(k in file.lower() for k in ['controller', 'provider', 'bloc', 'model', 'screen', 'service', 'main'])
                if is_key or len(file_contents) < 5:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # Keep files reasonably sized
                            file_contents[rel_path] = "".join(lines[:150]) + ("\n... [Đã cắt bớt file]" if len(lines) > 150 else "")
                    except:
                        pass
                        
    # Add pubspec
    pub_path = os.path.join(project_path, 'pubspec.yaml')
    if os.path.exists(pub_path):
        try:
            with open(pub_path, 'r', encoding='utf-8') as f:
                file_contents['pubspec.yaml'] = f.read()
        except:
            pass
            
    return file_contents

def grade_project_with_gemini(project_path, api_key, analysis_report, custom_criteria_text=None):
    if not api_key:
        return fallback_heuristic_grade(analysis_report)
        
    try:
        genai.configure(api_key=api_key)
        
        # Prepare context of codebase
        key_files = get_key_files_content(project_path)
        codebase_summary = "\n\n".join([f"--- FILE: {path} ---\n{content}" for path, content in key_files.items()])
        
        criteria_str = custom_criteria_text
        if not criteria_str:
            # load default from criteria.md if we want, or use static description
            criteria_str = "Sử dụng 15 tiêu chí đánh giá trong rubric bao gồm: Cấu trúc project rõ ràng, Code dễ đọc, Tách UI thành các widget nhỏ, Tách logic khỏi UI, Quản lý state hợp lý, Xử lý navigation đúng, Quản lý dữ liệu bằng model, Xử lý lỗi và ngoại lệ, Giao diện responsive và không bị overflow, Tái sử dụng code, Quản lý tài nguyên tốt, Hiệu năng cơ bản, Code có khả năng mở rộng, Tuân thủ coding convention, Có kiểm thử hoặc kiểm tra chức năng cơ bản."

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
  "overall_score": <điểm tổng hợp từ 0.0 đến 10.0, được làm tròn đến 2 chữ số thập phân>,
  "criteria_breakdown": {{
     "1. Cấu trúc project rõ ràng": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét ngắn gọn>" }},
     "2. Code dễ đọc, dễ hiểu": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "3. Tách UI thành các widget nhỏ": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "4. Tách logic khỏi UI": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "5. Quản lý state hợp lý": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "6. Xử lý navigation đúng": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "7. Quản lý dữ liệu bằng model": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "8. Xử lý lỗi và ngoại lệ": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "9. Giao diện responsive và không bị overflow": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "10. Tái sử dụng code": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "11. Quản lý tài nguyên tốt": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "12. Hiệu năng cơ bản": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "13. Code có khả năng mở rộng": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "14. Tuân thủ coding convention": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }},
     "15. Có kiểm thử hoặc kiểm tra chức năng cơ bản": {{ "score": <0.0-10.0>, "feedback": "<Lời khuyên/nhận xét>" }}
  }},
  "summary": "<Tổng hợp điểm mạnh và điểm yếu lớn nhất của dự án>",
  "warnings": [
     "<Cảnh báo lỗi/Anti-pattern 1>",
     "<Cảnh báo lỗi/Anti-pattern 2>"
  ]
}}

LƯU Ý: 
- Tính toán điểm tổng hợp (overall_score) dựa trên trọng số sau:
  + Cấu trúc project: 10%
  + Chất lượng code: 10%
  + Tách widget: 10%
  + Tách logic khỏi UI: 10%
  + Quản lý state: 10%
  + Navigation: 8%
  + Model & dữ liệu: 8%
  + Xử lý lỗi: 8%
  + Responsive UI: 8%
  + Tái sử dụng: 6%
  + Hiệu năng cơ bản: 6%
  + Hoàn thiện & test: 6%
  + Quản lý tài nguyên: 6%
  + Code mở rộng: 6%
  + Tuân thủ convention: 6%
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
        res = fallback_heuristic_grade(analysis_report)
        res["summary"] = f"Lỗi gọi Gemini API ({str(e)}). Đã chuyển sang chế độ chấm tĩnh tự động."
        return res
