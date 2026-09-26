from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from extensions import db
from models import User


def admin_required(view):
    """要求请求携带有效的管理员 JWT。

    注意：前端隐藏入口只是体验优化，真正的权限校验必须落在服务端。
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = db.session.get(User, int(get_jwt_identity()))
        if user is None:
            return jsonify({"message": "用户不存在"}), 401
        if not user.is_admin:
            return jsonify({"message": "需要管理员权限"}), 403
        return view(*args, **kwargs)

    return wrapper