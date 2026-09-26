from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    """管理员登录。平台不提供公开注册，账号由环境变量初始化。"""
    data = request.get_json(silent=True) or {}
    account = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not account or not password:
        return jsonify({"message": "请输入用户名和密码"}), 400

    user = User.query.filter(
        (User.username == account) | (User.email == account.lower())
    ).first()
    if user is None or not user.check_password(password):
        return jsonify({"message": "用户名或密码错误"}), 401
    if not user.is_admin:
        return jsonify({"message": "该账号没有管理权限"}), 403

    # Flask-JWT-Extended 4.x 要求 identity 为字符串
    token = create_access_token(identity=str(user.id))
    return jsonify({"message": "登录成功", "token": token, "user": user.to_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"message": "用户不存在"}), 401
    return jsonify({"user": user.to_dict()})