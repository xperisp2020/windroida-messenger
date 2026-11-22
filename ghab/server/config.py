"""تنظیمات یک‌جا. همه مسیرها و عددها از اینجا می‌آیند."""
import os
import secrets
import stat
import subprocess
import tempfile

VERSION = '2.4.3'
PORT = int(os.environ.get('GHAB_PORT', 8084))
WD_PORT = int(os.environ.get('WD_WEB_PORT', 8081))  # پیام‌رسان ویندروید؛ برای باز کردن چت کاربر به جای دایرکت اینجا
# ثبت‌نام، ورود با رمز و بازیابی رمز وجود ندارند (مگر GHAB_PASSWORD_AUTH=1 فقط برای آزمایش)؛ تنها راه ورود لینک «قاب» تو منوی ویندروید
# است. وب‌پنل ادمین حذف شده؛ ادمینی فقط از دیتاشیت ویندروید.
PASSWORD_AUTH = os.environ.get('GHAB_PASSWORD_AUTH', '0') == '1'  # پیش‌فرض خاموش: ساخت حساب و ورود فقط از ویندروید
SSO_SECRET = os.environ.get('GHAB_SSO_SECRET', '').strip()
if SSO_SECRET and len(SSO_SECRET.encode('utf-8')) < 32:
    raise RuntimeError('GHAB_SSO_SECRET must contain at least 32 bytes of secret material')
MIN_FREE_MB = int(os.environ.get('GHAB_MIN_FREE_MB', 500))  # کمتر از این فضای خالی: آپلود جدید رد می‌شود
MAX_UPLOAD_MB = 600  # سقف ایمنی؛ ویدیوها بعد از آپلود خودکار فشرده می‌شوند
BACKUP = os.environ.get('GHAB_BACKUP', '0') == '1'  # پشتیبان خودکار قبل از ارتقای دیتابیس (پیش‌فرض خاموش تا دیسک پر نشود)
EXTRA_RENDITIONS = os.environ.get('GHAB_EXTRA_RENDITIONS', '0') == '1'  # نسخه کم‌حجم ویدیو و عکس ۷۲۰ (فضای بیشتر می‌خورد)
COMPRESS_VIDEO = os.environ.get('GHAB_COMPRESS', '1') != '0'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get('GHAB_DATA') or os.path.join(BASE_DIR, 'data')  # همه چیزِ کاربر فقط اینجاست
DB_PATH = os.path.join(DATA_DIR, 'ghab.db')
USERS_DIR = os.path.join(DATA_DIR, 'users')      # users/<username>/{posts,stories,avatar}/
CERT_DIR = os.path.join(DATA_DIR, 'certs')
LOG_DIR = os.path.join(DATA_DIR, 'logs')
BEHIND_PROXY = os.environ.get('GHAB_PLAIN', '0') == '1'  # HTTP ساده پشت پروکسی HTTPS (Cloudflare Tunnel / Caddy)
BACKUP_DIR = os.path.join(DATA_DIR, 'backups')   # قبل از هر آپدیتِ دیتابیس خودکار پر می‌شود
MIGRATIONS_DIR = os.path.join(BASE_DIR, 'migrations')
WEB_DIR = os.path.join(BASE_DIR, 'web')
STATIC_DIR = os.path.join(WEB_DIR, 'static')


def ensure_dirs():
    for d in (DATA_DIR, USERS_DIR, CERT_DIR, BACKUP_DIR, LOG_DIR):
        os.makedirs(d, exist_ok=True)


def _restrict_session_secret(path):
    if os.path.islink(path):
        raise PermissionError(f'refusing symlink for session secret: {path}')
    if os.name == 'posix':
        os.chmod(path, 0o600)
        mode = stat.S_IMODE(os.stat(path).st_mode)
        if mode != 0o600:
            raise PermissionError(f'session secret permissions are {mode:o}, expected 600: {path}')
    elif os.name == 'nt':
        account = subprocess.run(['whoami'], check=True, capture_output=True, text=True).stdout.strip()
        subprocess.run(['icacls', path, '/reset'], check=True, capture_output=True, text=True)
        subprocess.run(['icacls', path, '/inheritance:r', '/grant:r', f'{account}:(F)'],
                       check=True, capture_output=True, text=True)


def _write_session_secret(path, value):
    """Atomically write a session secret with restrictive permissions before secret bytes are written."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.session-secret-', suffix='.tmp', dir=directory)
    try:
        if os.name == 'posix':
            os.fchmod(fd, 0o600)
        elif os.name == 'nt':
            _restrict_session_secret(tmp)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        if os.name == 'posix' and stat.S_IMODE(os.stat(tmp).st_mode) != 0o600:
            raise PermissionError(f'temporary session secret is not mode 600: {tmp}')
        os.replace(tmp, path)
        _restrict_session_secret(path)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def secret_key():
    p = os.path.join(DATA_DIR, 'secret.key')
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.islink(p):
        raise PermissionError(f'refusing symlink for session secret: {p}')
    if not os.path.exists(p):
        _write_session_secret(p, secrets.token_hex(32))
    _restrict_session_secret(p)
    with open(p, encoding='utf-8') as f:
        value = f.read().strip()
    if len(value) < 32:
        raise RuntimeError('Ghab session secret is missing or too short')
    return value
