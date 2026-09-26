"""公开接口：无需登录即可访问，只读 + 在线调试。"""

import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

import requests
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from extensions import db
from models import ALLOWED_METHODS, Api, TestRecord

public_bp = Blueprint("public", __name__, url_prefix="/api/public")

# 代理转发时带上的标记，用于阻断调试接口自引用造成的无限递归
PROXY_MARKER_HEADER = "X-QQAPI-Proxy"


def _enabled_api(api_id: int):
    """公开侧只能看到已启用的 API。"""
    return Api.query.filter_by(id=api_id, is_enabled=True).first()


def _assert_public_host(hostname: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError("无法解析目标域名") from None

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("出于安全考虑，已禁止调试请求访问内网地址")


def _validate_target(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅支持 http / https 协议的调试请求")
    if not parsed.hostname:
        raise ValueError("目标地址无效，请检查请求路径")
    if not current_app.config.get("PROXY_ALLOW_PRIVATE", True):
        _assert_public_host(parsed.hostname, parsed.port or 0)
    return url


@public_bp.get("/apis")
def list_apis():
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    page_size = min(max(request.args.get("page_size", 50, type=int) or 50, 1), 100)
    keyword = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    method = (request.args.get("method") or "").strip().upper()

    query = Api.query.filter_by(is_enabled=True)
    if keyword:
        like = f"%{keyword}%"
        # 顶部搜索框：支持按 API 名称或分类搜索
        query = query.filter(
            or_(Api.name.like(like), Api.category.like(like), Api.description.like(like))
        )
    if category:
        query = query.filter(Api.category == category)
    if method:
        query = query.filter(Api.method == method)

    total = query.count()
    items = (
        query.order_by(Api.category.asc(), Api.name.asc())
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


@public_bp.get("/apis/<int:api_id>")
def get_api(api_id: int):
    api = _enabled_api(api_id)
    if api is None:
        return jsonify({"message": "API 不存在或已停用"}), 404
    return jsonify({"api": api.to_dict()})


@public_bp.get("/apis/<int:api_id>/records")
def list_records(api_id: int):
    api = _enabled_api(api_id)
    if api is None:
        return jsonify({"message": "API 不存在或已停用"}), 404

    limit = current_app.config["TEST_RECORD_LIMIT"]
    records = (
        TestRecord.query.filter_by(api_id=api.id)
        .order_by(TestRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"items": [record.to_dict() for record in records]})


@public_bp.get("/categories")
def list_categories():
    rows = (
        db.session.query(Api.category)
        .filter(Api.is_enabled.is_(True))
        .distinct()
        .all()
    )
    categories = sorted({(row[0] or "未分类") for row in rows})
    return jsonify({"items": categories})


@public_bp.post("/apis/<int:api_id>/test")
def test_api(api_id: int):
    """在线调试：服务端代为发起真实请求，返回真实响应并记录到历史测试记录。"""
    if request.headers.get(PROXY_MARKER_HEADER):
        return jsonify({"message": "不允许对调试接口本身发起嵌套调试"}), 400

    api = _enabled_api(api_id)
    if api is None:
        return jsonify({"message": "API 不存在或已停用"}), 404

    data = request.get_json(silent=True) or {}
    method = (data.get("method") or api.method or "GET").strip().upper()
    target = (data.get("url") or api.full_url or "").strip()
    params = data.get("params") or {}
    body = data.get("body")

    if method not in ALLOWED_METHODS:
        return jsonify({"message": f"不支持的请求方法：{method}"}), 400
    if not isinstance(params, dict):
        return jsonify({"message": "查询参数需要是 JSON 对象"}), 400
    if body is not None and not isinstance(body, (dict, list)):
        return jsonify({"message": "请求体需要是 JSON 对象或数组"}), 400

    try:
        _validate_target(target)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    max_bytes = current_app.config["PROXY_MAX_RESPONSE_BYTES"]
    timeout = current_app.config["PROXY_TIMEOUT"]
    send_body = body if method in {"POST", "PUT", "PATCH", "DELETE"} else None

    started = time.perf_counter()
    status_code = None
    success = False
    error = ""
    response_body = ""
    truncated = False
    try:
        resp = requests.request(
            method,
            target,
            params=params or None,
            json=send_body,
            headers={PROXY_MARKER_HEADER: "1"},
            timeout=timeout,
            allow_redirects=False,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        status_code = resp.status_code
        success = 200 <= resp.status_code < 400
        raw = resp.text
        truncated = len(raw) > max_bytes
        response_body = raw[:max_bytes]
    except requests.RequestException as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        error = f"请求失败：{exc.__class__.__name__}"

    record = TestRecord(
        api_id=api.id,
        method=method,
        target_url=target,
        request_payload=json.dumps(
            {"params": params, "body": send_body}, ensure_ascii=False
        ),
        status_code=status_code,
        success=success,
        duration_ms=duration_ms,
        response_body=response_body,
        error=error,
        client_ip=request.remote_addr or "",
    )
    db.session.add(record)
    db.session.commit()

    return jsonify(
        {
            "request": {"method": method, "url": target, "params": params, "body": send_body},
            "response": {
                "status_code": status_code,
                "success": success,
                "duration_ms": duration_ms,
                "error": error,
                "body": response_body,
                "truncated": truncated,
            },
            "record": record.to_dict(),
        }
    )