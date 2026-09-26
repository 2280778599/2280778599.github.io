import os
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError

from config import Config
from extensions import db, jwt

DEFAULT_ADMIN_PASSWORD = "admin123"

# 前端静态资源所在目录（仓库根目录）及允许对外暴露的顶层条目。
# 白名单之外的路径一律 404，避免把 backend/ 源码和运行期生成的 SQLite 数据库暴露出去。
FRONTEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_ENTRIES = {"index.html", "detail.html", "admin.html", "css", "js"}


def _bootstrap_admin(app: Flask) -> None:
    """按环境变量确保存在一个管理员账号（平台不提供公开注册）。"""
    from models import User

    username = app.config["ADMIN_USERNAME"]
    password = app.config["ADMIN_PASSWORD"]
    email = app.config["ADMIN_EMAIL"]

    admin = User.query.filter_by(username=username).first()
    if admin is not None:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            app.logger.warning("已将已有账号 %s 提升为管理员", username)
        return

    admin = User(username=username, email=email, is_admin=True)
    admin.set_password(password)
    db.session.add(admin)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        app.logger.error("初始管理员创建失败：邮箱 %s 已被其它账号占用", email)
        return

    app.logger.warning("已创建初始管理员账号：%s", username)
    if password == DEFAULT_ADMIN_PASSWORD:
        app.logger.warning(
            "当前管理员使用的是默认密码，请通过环境变量 ADMIN_PASSWORD 修改后再上线"
        )


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 必须在注册蓝图前导入模型，确保建表时能识别
    from models import Api, TestRecord, User  # noqa: F401
    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # ---- 前端静态资源托管（与 /api/* 同源，无需额外的前端服务器）----
    @app.get("/")
    def frontend_index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def frontend_assets(filename: str):
        if filename.split("/", 1)[0] not in FRONTEND_ENTRIES:
            abort(404)
        return send_from_directory(FRONTEND_DIR, filename)

    @app.errorhandler(404)
    def not_found(_error):
        # 接口请求仍返回 JSON；页面请求回落到首页，但保留 404 状态码
        if request.path.startswith("/api/"):
            return jsonify({"message": "接口或资源不存在"}), 404
        return send_from_directory(FRONTEND_DIR, "index.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"message": "请求方法不被允许"}), 405

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"message": "服务器内部错误"}), 500

    # 统一 JWT 错误响应格式
    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify({"message": "缺少访问令牌，请先登录"}), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify({"message": "访问令牌无效"}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"message": "登录已过期，请重新登录"}), 401

    with app.app_context():
        db.create_all()
        _bootstrap_admin(app)

    return app


app = create_app()

if __name__ == "__main__":
    # 本地开发用；线上由 gunicorn 启动，不会走到这里
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)