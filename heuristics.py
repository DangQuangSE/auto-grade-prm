from typing import Any, Dict, Optional

from rubric import DEFAULT_CRITERIA_TEXT, parse_rubric


def get_heuristic_score_for_key(key: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    if key == "structure":
        struct_score = analysis["structure"]["folder_structure_score"] / 10.0
        details = analysis["structure"].get("details") or []
        return {
            "score": struct_score,
            "feedback": f"Folder structure score is {struct_score * 10:.0f}%. {'; '.join(details)}",
            "suggestion": "Tổ chức lib/ theo feature-first hoặc layer-first: lib/core (constants, themes, routes), lib/features/<ten_feature>/{screens,widgets,models}. Ví dụ: lib/features/product/{screens/product_list_screen.dart, widgets/product_card.dart, models/product.dart}.",
        }

    if key == "readability":
        large_files_count = len(analysis["stats"]["large_files"])
        score = max(4.0, 10.0 - min(3.0, large_files_count * 1.0))
        large_file_names = ", ".join(f["file"] for f in analysis["stats"]["large_files"][:3])
        return {
            "score": score,
            "feedback": f"Found {large_files_count} large files over 300 lines" + (f" ({large_file_names}...)" if large_file_names else "") + ".",
            "suggestion": "Đặt tên biến/hàm có ý nghĩa và tách các file dài thành nhiều file nhỏ theo trách nhiệm. Ví dụ: thay `var x = getData();` bằng `final productList = getProductList();`, và tách phần xử lý dài trong build() ra hàm/widget riêng.",
        }

    if key == "widgets":
        score = 9.0
        offending_files = []
        for large_file in analysis["stats"]["large_files"]:
            path = large_file["file"].lower()
            if "screen" in path or "widget" in path:
                score -= 1.0
                offending_files.append(large_file["file"])
        return {
            "score": max(5.0, score),
            "feedback": "Large screen/widget files may need decomposition into smaller widgets." + (f" Files: {', '.join(offending_files[:3])}." if offending_files else ""),
            "suggestion": "Tách build() dài thành các widget con có tên rõ ràng, ví dụ ProductDetailScreen -> ProductImage, ProductInfo, PriceSection, QuantitySelector, AddToCartButton, mỗi widget là một class StatelessWidget/StatefulWidget riêng trong widgets/.",
        }

    if key == "logic":
        violations = analysis["heuristics"]["api_calls_in_build"]
        violation_files = ", ".join(v["file"] for v in violations[:3])
        return {
            "score": max(4.0, 7.0 - len(violations) * 3.0),
            "feedback": f"Found {len(violations)} possible API calls inside build methods" + (f" ({violation_files})." if violation_files else "."),
            "suggestion": "Chuyển lời gọi API ra khỏi build(): gọi trong initState()/provider/controller, lưu kết quả vào state, và để build() chỉ đọc state để hiển thị. Ví dụ dùng FutureBuilder hoặc gọi fetch trong initState() thay vì trực tiếp trong build().",
        }

    if key == "state":
        managers = analysis["heuristics"]["state_management"]
        return {
            "score": 9.0 if managers else 6.0,
            "feedback": f"Detected state management: {', '.join(managers)}" if managers else "No common state management package detected.",
            "suggestion": "Nếu chỉ dùng setState() cho project nhiều màn hình, cân nhắc thêm Provider/Riverpod/Bloc để quản lý state loading/success/error/empty tập trung thay vì biến global rải rác.",
        }

    if key == "navigation":
        count = len(analysis["heuristics"]["navigation_patterns"])
        return {
            "score": 8.5 if count else 6.0,
            "feedback": f"Detected navigation usage in {count} files.",
            "suggestion": "Định nghĩa route tập trung (ví dụ AppRoutes với các hằng số route name) và dùng Navigator.pushNamed(context, AppRoutes.productDetail, arguments: productId) thay vì hard-code chuỗi route rải rác.",
        }

    if key == "models":
        has_models = analysis["structure"]["has_models"]
        return {
            "score": 9.0 if has_models else 6.0,
            "feedback": "Model structure detected." if has_models else "No clear model folder or model structure detected.",
            "suggestion": "Tạo class model cho các entity chính (Product, User, CartItem) với factory fromJson, thay vì truy cập trực tiếp product['name']. Ví dụ: `class Product { final String name; factory Product.fromJson(Map<String, dynamic> json) => Product(name: json['name']); }`.",
        }

    if key == "errors":
        count = analysis["heuristics"]["error_handling_count"]
        return {
            "score": min(10.0, 5.0 + count * 0.5),
            "feedback": f"Detected {count} try/catch blocks.",
            "suggestion": "Bọc các lời gọi API/parse dữ liệu trong try-catch và hiển thị thông báo lỗi thân thiện, ví dụ: `try { final products = await productService.getProducts(); } catch (e) { showErrorMessage('Không thể tải danh sách sản phẩm'); }`.",
        }

    if key == "responsive":
        widgets = analysis["heuristics"]["responsive_widgets_used"]
        return {
            "score": min(10.0, 5.0 + len(widgets) * 1.5),
            "feedback": f"Responsive/layout widgets used: {', '.join(widgets) if widgets else 'none detected'}.",
            "suggestion": "Bọc nội dung có thể tràn màn hình bằng SingleChildScrollView/Expanded/Flexible, và dùng ListView.builder cho danh sách dài thay vì Column cứng để tránh lỗi RenderFlex overflowed.",
        }

    if key == "resources":
        has_assets = analysis["heuristics"]["pubspec_details"].get("has_assets", False)
        return {
            "score": 9.0 if has_assets else 6.0,
            "feedback": "Assets are configured in pubspec.yaml." if has_assets else "No assets configuration detected in pubspec.yaml.",
            "suggestion": "Khai báo assets rõ ràng trong pubspec.yaml và gom URL API/endpoint vào một file cấu hình riêng (ví dụ lib/core/constants/api_endpoints.dart) thay vì hard-code rải rác trong code.",
        }

    if key == "performance":
        violations = len(analysis["heuristics"]["api_calls_in_build"])
        return {
            "score": max(5.0, 9.0 - violations * 2.0),
            "feedback": "Performance risk increases when API calls or heavy work happen in build methods.",
            "suggestion": "Dùng ListView.builder() cho danh sách dài, thêm const cho các widget không đổi, và tránh gọi API lặp lại trong build() để giảm rebuild không cần thiết.",
        }

    if key == "convention":
        violations = analysis["stats"]["naming_violations"]
        violation_examples = "; ".join(v["error"] for v in violations[:3])
        return {
            "score": max(4.0, 10.0 - len(violations) * 0.5),
            "feedback": f"Detected {len(violations)} naming convention issues." + (f" Examples: {violation_examples}." if violation_examples else ""),
            "suggestion": "Đổi tên file theo snake_case (product_detail_screen.dart), class theo PascalCase (ProductCard), biến/hàm theo camelCase (getProducts()), và chạy `dart format .` để chuẩn hóa toàn bộ code.",
        }

    if key == "testing":
        return {
            "score": 6.0,
            "feedback": "Static analysis cannot fully verify unit/widget tests; review test coverage manually.",
            "suggestion": "Thêm ít nhất vài unit test cho logic quan trọng (service/repository) và widget test cho các màn hình chính bằng flutter_test, hoặc ghi lại kết quả kiểm thử thủ công cho các chức năng chính (thêm/sửa/xóa, validate form, navigation).",
        }

    if key == "reusability":
        return {
            "score": 7.5,
            "feedback": "Review repeated widgets, constants, and shared utilities for reuse opportunities.",
            "suggestion": "Tạo các file dùng chung như AppStrings, AppColors, AppRoutes, AppSizes cho hằng số, và tách widget lặp lại (ví dụ button, card) thành widget dùng chung trong lib/core/widgets hoặc lib/shared.",
        }

    if key == "extensibility":
        return {
            "score": 7.5,
            "feedback": "Extensibility depends on clear module boundaries and separation of responsibilities.",
            "suggestion": "Giữ ranh giới rõ giữa các feature (mỗi feature tự chứa screens/widgets/models/service riêng) để thêm màn hình hoặc API mới không phải sửa nhiều nơi khác nhau.",
        }

    return {"score": 7.0, "feedback": "General heuristic evaluation.", "suggestion": "Xem lại thủ công tiêu chí này vì không có heuristic tự động tương ứng."}


def fallback_heuristic_grade(
    analysis: Dict[str, Any],
    parsed_rubric: Optional[Dict[str, Dict[str, Any]]] = None,
    provider_error: Optional[str] = None,
) -> Dict[str, Any]:
    rubric_to_use = parsed_rubric or parse_rubric(DEFAULT_CRITERIA_TEXT)
    scores = {}
    total_score = 0.0
    total_weight = 0.0

    for name, item in rubric_to_use.items():
        result = get_heuristic_score_for_key(item["key"], analysis)
        scores[name] = result
        total_score += result["score"] * item["weight"]
        total_weight += item["weight"]

    final_score = (total_score / total_weight) if total_weight > 0 else 0.0
    warnings = list(analysis["heuristics"]["api_calls_in_build"]) + list(analysis["stats"]["naming_violations"])
    if provider_error:
        warnings.insert(0, f"AI provider failed; default-template heuristic fallback was used. Error: {provider_error}")

    report = {
        "overall_score": round(final_score, 2),
        "criteria_breakdown": scores,
        "summary": "Automatic heuristic grading was used. Configure OpenRouter successfully for AI-based rubric review.",
        "warnings": warnings,
        "provider": "openrouter",
        "model": None,
        "grading_mode": "heuristic",
    }
    if provider_error:
        report["provider_error"] = provider_error

    return report
