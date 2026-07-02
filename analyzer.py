import os
import re
import yaml

def check_naming_convention(name, type_):
    if type_ == 'file':
        # snake_case
        return bool(re.match(r'^[a-z0-9_]+\.dart$', name))
    elif type_ == 'class':
        # PascalCase
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
    elif type_ == 'variable' or type_ == 'method':
        # camelCase
        return bool(re.match(r'^[a-z][a-zA-Z0-9]*$', name))
    return True

def analyze_flutter_project(project_path):
    report = {
        "structure": {
            "has_lib": False,
            "has_features": False,
            "has_core": False,
            "has_models": False,
            "has_services": False,
            "has_widgets": False,
            "has_screens": False,
            "folder_structure_score": 0,
            "details": []
        },
        "stats": {
            "total_dart_files": 0,
            "total_lines_of_code": 0,
            "large_files": [],
            "naming_violations": []
        },
        "heuristics": {
            "api_calls_in_build": [],
            "raw_map_usages": [],
            "state_management": [],
            "error_handling_count": 0,
            "navigation_patterns": [],
            "responsive_widgets_used": [],
            "const_usage_count": 0,
            "has_pubspec": False,
            "pubspec_details": {}
        }
    }

    lib_path = os.path.join(project_path, "lib")
    pubspec_path = os.path.join(project_path, "pubspec.yaml")

    if not os.path.exists(project_path):
        return {"error": "Project path does not exist."}

    # 1. Pubspec analysis
    if os.path.exists(pubspec_path):
        report["heuristics"]["has_pubspec"] = True
        try:
            with open(pubspec_path, 'r', encoding='utf-8') as f:
                pub_data = yaml.safe_load(f)
                deps = pub_data.get('dependencies', {})
                dev_deps = pub_data.get('dev_dependencies', {})
                flutter_section = pub_data.get('flutter', {})
                
                report["heuristics"]["pubspec_details"] = {
                    "name": pub_data.get('name', 'unknown'),
                    "dependencies": list(deps.keys()) if deps else [],
                    "has_assets": 'assets' in flutter_section,
                    "assets": flutter_section.get('assets', []) if 'assets' in flutter_section else []
                }
                
                # Check state management
                state_mgrs = ['provider', 'flutter_bloc', 'riverpod', 'flutter_riverpod', 'get', 'mobx']
                for sm in state_mgrs:
                    if sm in deps:
                        report["heuristics"]["state_management"].append(sm)
        except Exception as e:
            report["heuristics"]["pubspec_details"] = {"error": f"Failed to parse pubspec: {str(e)}"}

    if not os.path.exists(lib_path):
        report["structure"]["details"].append("Thư mục 'lib' không tồn tại. Đây không phải dự án Flutter chuẩn.")
        return report

    report["structure"]["has_lib"] = True
    
    # Check folder structure
    subdirs = [d for d in os.listdir(lib_path) if os.path.isdir(os.path.join(lib_path, d))]
    
    if "features" in subdirs:
        report["structure"]["has_features"] = True
    if "core" in subdirs:
        report["structure"]["has_core"] = True
    if "models" in subdirs or any("model" in d.lower() for d in subdirs):
        report["structure"]["has_models"] = True
    if "services" in subdirs or any("service" in d.lower() or "repository" in d.lower() for d in subdirs):
        report["structure"]["has_services"] = True
    if "widgets" in subdirs or any("widget" in d.lower() for d in subdirs):
        report["structure"]["has_widgets"] = True
    if "screens" in subdirs or any("screen" in d.lower() or "page" in d.lower() for d in subdirs):
        report["structure"]["has_screens"] = True

    # Calculate structure score
    struct_score = 0
    if report["structure"]["has_features"] or report["structure"]["has_core"]:
        struct_score += 40
        report["structure"]["details"].append("Dự án tổ chức theo cấu trúc Clean Architecture hoặc Feature-first tốt.")
    else:
        # Check standard flat patterns
        hits = 0
        if report["structure"]["has_models"]: hits += 1
        if report["structure"]["has_services"]: hits += 1
        if report["structure"]["has_screens"]: hits += 1
        if report["structure"]["has_widgets"]: hits += 1
        struct_score += hits * 20
        if hits >= 3:
            report["structure"]["details"].append("Dự án tổ chức thư mục cơ bản theo lớp (models, screens, widgets).")
        else:
            report["structure"]["details"].append("Cấu trúc thư mục đơn giản, thiếu tổ chức phân lớp rõ ràng.")
            
    report["structure"]["folder_structure_score"] = min(100, struct_score + 10) # base 10 points for having lib

    # 2. Travel through lib/ and analyze files
    for root, dirs, files in os.walk(lib_path):
        for file in files:
            if file.endswith(".dart"):
                report["stats"]["total_dart_files"] += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)

                # Check file name convention (snake_case)
                if not check_naming_convention(file, 'file'):
                    report["stats"]["naming_violations"].append({
                        "file": rel_path,
                        "error": f"Tên file '{file}' không tuân thủ snake_case."
                    })

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        num_lines = len(lines)
                        report["stats"]["total_lines_of_code"] += num_lines

                        if num_lines > 300:
                            report["stats"]["large_files"].append({
                                "file": rel_path,
                                "lines": num_lines,
                                "message": f"File quá dài ({num_lines} dòng), cần cân nhắc tách nhỏ widget hoặc logic."
                            })

                        # Read full content for regex analysis
                        content = "".join(lines)

                        # Check for API calls in build methods
                        # Regex to look for async HTTP, API fetches or state changes in build methods
                        # Usually, build methods look like Widget build(BuildContext context) { ... }
                        build_blocks = re.findall(r'Widget\s+build\s*\(\s*BuildContext\s+context\s*\)\s*\{([\s\S]*?)\}', content)
                        for block in build_blocks:
                            if any(api_keyword in block for api_keyword in ['.get(', '.post(', 'http.get', 'dio.get', 'fetch', 'apiService']):
                                report["heuristics"]["api_calls_in_build"].append({
                                    "file": rel_path,
                                    "message": "Phát hiện gọi API trực tiếp trong hàm build() hoặc khởi tạo widget trong build()."
                                })
                            if 'setState(' in block:
                                # Standard, but look if it's nested or causing rebuild loop
                                pass

                        # Check for heavy raw map usage instead of models
                        # Looking for patterns like data['name'] or item['title'] inside .dart UI files
                        if 'Screen' in file or 'Widget' in file:
                            map_accesses = re.findall(r'\b[a-zA-Z0-9_]+\[[\'"][a-zA-Z0-9_]+[\'"]\]', content)
                            if len(map_accesses) > 5:
                                report["heuristics"]["raw_map_usages"].append({
                                    "file": rel_path,
                                    "count": len(map_accesses),
                                    "message": f"Sử dụng Map thô quá nhiều ({len(map_accesses)} lần) trong UI. Nên chuyển sang sử dụng Class Model."
                                })

                        # Count error handling try-catch
                        report["heuristics"]["error_handling_count"] += len(re.findall(r'\btry\s*\{', content))

                        # Count const usages
                        report["heuristics"]["const_usage_count"] += len(re.findall(r'\bconst\s+[A-Z]', content))

                        # Check navigation
                        if 'Navigator.' in content or 'context.push' in content or 'context.go' in content:
                            report["heuristics"]["navigation_patterns"].append(rel_path)

                        # Check responsive / layout widgets
                        responsive_widgets = ['Expanded', 'Flexible', 'LayoutBuilder', 'MediaQuery', 'SingleChildScrollView', 'ListView.builder']
                        for rw in responsive_widgets:
                            if rw in content:
                                if rw not in report["heuristics"]["responsive_widgets_used"]:
                                    report["heuristics"]["responsive_widgets_used"].append(rw)

                        # Check Class name convention
                        class_names = re.findall(r'\bclass\s+([a-zA-Z0-9_]+)\b', content)
                        for cn in class_names:
                            if not check_naming_convention(cn, 'class'):
                                report["stats"]["naming_violations"].append({
                                    "file": rel_path,
                                    "error": f"Tên class '{cn}' không tuân thủ PascalCase."
                                })

                except Exception as e:
                    # Ignore file reading errors
                    pass

    return report
