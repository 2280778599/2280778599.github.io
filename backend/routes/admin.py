"""管理接口：需要管理员 JWT。"""

import json

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from decorators import admin_required
from extensions import db
from models import ALLOWED_METHODS, Api, TestRecord

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _parse_payload(data: dict) -> dict:
    """校验并归一化管理端提交的 API 数据。校验失败抛 ValueError。"""
    name = (data.get("name") or "").strip()
    method = (data.get("method") or "GET").strip().upper()
    path = (data.get("path") or "").strip()
    base_url = (data.get("base_url") or "").strip().rstrip("/")
    link = (data.get("link") or "").strip()
    description = (data.get("description") or "").strip()
    response_example = data.get("response_example") or ""

    if not name:
        raise ValueError("名称不能为空")
    if method not in ALLOWED_METHODS:
        raise ValueError(f"不支持的请求方法：{method}")
    if not path:
        raise ValueError("请求路径不能为空")
    if base_url and not base_url.startswith(("http://", "https://")):
        raise ValueError("基址需要以 http:// 或 https:// 开头")
    if link and not link.startswith(("http://", "https://")):
        raise ValueError("项目/参考链接需要以 http:// 或 https:// 开头")

    if isinstance(response_example, (dict, list)):
        response_example = json.dumps(response_example, ensure_ascii=False, indent=2)
    else:
        response_example = str(response_example).strip()
    if response_example:
        try:
            json.loads(response_example)
        except json.JSONDecodeError as exc:
            raise ValueError(f"响应示例不是合法的 JSON：{exc.msg}") from None

    return {
        "name": name,
        "method": method,
        "path": path if path.startswith("/") else f"/{path}",
        "base_url": base_url,
        "link": link,
        "category": (data.get("category") or "").strip() or "未分类",
        "description": description,
        "response_example": response_example,
        "is_enabled": bool(data.get("is_enabled", True)),
    }


@admin_bp.get("/apis")
@admin_required
def list_apis():
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    page_size = min(max(request.args.get("page_size", 100, type=int) or 100, 1), 200)
    keyword = (request.args.get("q") or "").strip()

    query = Api.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Api.name.like(like), Api.path.like(like), Api.category.like(like))
        )

    total = query.count()
    items = (
        query.order_by(Api.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return jsonify(
        {
            "items": [api.to_dict() for api in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@admin_bp.post("/apis")
@admin_required
def create_api():
    try:
        values = _parse_payload(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    api = Api(**values)
    db.session.add(api)
    db.session.commit()
    return jsonify({"message": "创建成功", "api": api.to_dict()}), 201


@admin_bp.get("/apis/<int:api_id>")
@admin_required
def get_api(api_id: int):
    api = db.session.get(Api, api_id)
    if api is None:
        return jsonify({"message": "API 不存在"}), 404
    return jsonify({"api": api.to_dict()})


@admin_bp.put("/apis/<int:api_id>")
@admin_required
def update_api(api_id: int):
    api = db.session.get(Api, api_id)
    if api is None:
        return jsonify({"message": "API 不存在"}), 404

    try:
        values = _parse_payload(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    for field, value in values.items():
        setattr(api, field, value)
    db.session.commit()
    return jsonify({"message": "已保存，前台将同步更新", "api": api.to_dict()})


@admin_bp.put("/apis/<int:api_id>/status")
@admin_required
def set_api_status(api_id: int):
    """上架 / 下架：把 API 在前台公开或隐藏。"""
    api = db.session.get(Api, api_id)
    if api is None:
        return jsonify({"message": "API 不存在"}), 404

    data = request.get_json(silent=True) or {}
    target = data.get("is_enabled")
    # 未显式指定则直接取反，方便前台一键切换
    api.is_enabled = (not api.is_enabled) if target is None else bool(target)
    db.session.commit()
    state = "已上架" if api.is_enabled else "已下架"
    return jsonify({"message": f"{state}，前台将同步更新", "api": api.to_dict()})


@admin_bp.delete("/apis/<int:api_id>")
@admin_required
def delete_api(api_id: int):
    api = db.session.get(Api, api_id)
    if api is None:
        return jsonify({"message": "API 不存在"}), 404

    db.session.delete(api)
    db.session.commit()
    return jsonify({"message": "删除成功"})


@admin_bp.delete("/apis/<int:api_id>/records")
@admin_required
def clear_records(api_id: int):
    api = db.session.get(Api, api_id)
    if api is None:
        return jsonify({"message": "API 不存在"}), 404

    deleted = TestRecord.query.filter_by(api_id=api.id).delete()
    db.session.commit()
    return jsonify({"message": f"已清空 {deleted} 条历史测试记录"})