import hashlib
import hmac
import secrets


# OWASP khuyến nghị tối thiểu 600.000 vòng cho PBKDF2-HMAC-SHA256. Hash cũ (300.000 vòng) vẫn đăng nhập được
# vì số vòng được lưu ngay trong chuỗi hash; hash mới luôn dùng số vòng bên dưới.
ROUNDS = 600000


def hash_password(password):
    if len(password) < 12:
        raise ValueError("Mật khẩu cần ít nhất 12 ký tự.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ROUNDS).hex()
    return f"pbkdf2_sha256${ROUNDS}${salt}${digest}"


def check_password(password, encoded):
    try:
        algorithm, rounds, salt, digest = encoded.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return algorithm == "pbkdf2_sha256" and hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


_DUMMY = hash_password("không-bao-giờ-khớp-0123456789")


def burn_password_check(password):
    """Tốn thời gian như một lần kiểm tra thật, để không lộ tài khoản nào tồn tại qua độ trễ phản hồi."""
    check_password(password, _DUMMY)
