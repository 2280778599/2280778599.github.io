from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

# 在线调试允许转发的请求方法
ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")


class User(db.Model):
    """平台用户。is_admin=True 的用户才能访问管理接口。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_admin": bool(self.is_admin),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Api(db.Model):
    """被平台收录的一个 API 条目，由管理员维护。"""

    __tablename__ = "apis"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    method = db.Column(db.String(10), nullable=False, default="GET")
    path = db.Column(db.String(255), nullable=False)
    base_url = db.Column(db.String(255), default="")
    # 给用户看的项目 / 参考链接，与 base_url（在线调试转发目标）不是一回事
    link = db.Column(db.String(500), default="")
    category = db.Column(db.String(64), default="未分类", index=True)
    description = db.Column(db.Text, default="")
    response_example = db.Column(db.Text, default="")
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    records = db.relationship(
        "TestRecord", backref="api", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def full_url(self) -> str:
        base = (self.base_url or "").strip().rstrip("/")
        path = (self.path or "").strip()
        if base:
            return f"{base}/{path.lstrip('/')}"
        return path

    def to_dict(self, with_example: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "method": self.method,
            "path": self.path,
            "base_url": self.base_url or "",
            "link": self.link or "",
            "category": self.category or "未分类",
            "description": self.description or "",
            "is_enabled": bool(self.is_enabled),
            "full_url": self.full_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if with_example:
            data["response_example"] = self.response_example or ""
        return data


class TestRecord(db.Model):
    """一次在线调试的执行记录，用于在前台展示历史测试记录。"""

    __tablename__ = "test_records"

    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, db.ForeignKey("apis.id"), nullable=False, index=True)
    method = db.Column(db.String(10), nullable=False)
    target_url = db.Column(db.String(500), nullable=False)
    request_payload = db.Column(db.Text, default="")
    status_code = db.Column(db.Integer)
    success = db.Column(db.Boolean, default=False, nullable=False)
    duration_ms = db.Column(db.Integer, default=0)
    response_body = db.Column(db.Text, default="")
    error = db.Column(db.String(255), default="")
    client_ip = db.Column(db.String(64), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self, with_body: bool = False) -> dict:
        data = {
            "id": self.id,
            "api_id": self.api_id,
            "method": self.method,
            "target_url": self.target_url,
            "status_code": self.status_code,
            "success": bool(self.success),
            "duration_ms": self.duration_ms or 0,
            "error": self.error or "",
            "client_ip": self.client_ip or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if with_body:
            data["request_payload"] = self.request_payload or ""
            data["response_body"] = self.response_body or ""
        return data