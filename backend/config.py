import os
from datetime import timedelta


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # 生产环境请通过环境变量覆盖这两个密钥（长度建议不低于 32 字节）
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me-in-production")
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "dev-jwt-secret-key-change-me-in-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 初始管理员：应用启动时若该账号不存在则自动创建（无需公开注册入口）
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")

    # 在线调试代理配置
    PROXY_TIMEOUT = float(os.environ.get("PROXY_TIMEOUT", "10"))
    # 是否允许调试请求指向内网/本机地址（本地开发默认允许，公网部署建议设为 false 防 SSRF）
    PROXY_ALLOW_PRIVATE = _env_bool("PROXY_ALLOW_PRIVATE", True)
    PROXY_MAX_RESPONSE_BYTES = int(os.environ.get("PROXY_MAX_RESPONSE_BYTES", "20000"))

    # 前台每个 API 展示的历史测试记录条数
    TEST_RECORD_LIMIT = int(os.environ.get("TEST_RECORD_LIMIT", "20"))