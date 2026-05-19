"""Security utilities for password validation, 2FA, and auditing"""

from soporte_empresa.app import db
import re
import secrets
import qrcode
from io import BytesIO
import pyotp
from flask import request, current_app
import base64
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os


ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'pdf', 'txt', 'doc', 'docx', 
    'xlsx', 'csv', 'gif', 'bmp', 'zip'
}

DANGEROUS_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js',
    'jar', 'zip', 'rar', 'iso', 'dmg', 'app', 'deb', 'rpm',
    'sh', 'bash', 'ps1', 'psm1', 'msi', 'dll', 'so', 'dylib'
}

ALLOWED_MIMETYPES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/bmp',
    'application/pdf',
    'text/plain',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
    'application/zip'
}


class PasswordValidator:
    """Validate password strength according to NIST guidelines"""
    
    MIN_LENGTH = 8
    COMMON_PASSWORDS = {
        'password', '12345678', 'qwerty', 'abc123', '123456', 'password123',
        'admin', 'letmein', 'welcome', 'monkey', 'dragon', 'master'
    }
    
    @staticmethod
    def validate(password):
        """
        Validate password and return (is_valid, error_message)
        
        NIST SP 800-63B Guidelines:
        - Minimum 8 characters (longer passwords are better)
        - Check against common ones
        - Allow any printable characters
        """
        errors = []
        
        # Check minimum length
        if len(password) < PasswordValidator.MIN_LENGTH:
            errors.append(f'Password must be at least {PasswordValidator.MIN_LENGTH} characters')
        
        # Check against common passwords
        if password.lower() in PasswordValidator.COMMON_PASSWORDS:
            errors.append('Password is too common. Use a unique password')
        
        # Warn if no numbers
        if not re.search(r'\d', password):
            errors.append('Recommended: include at least one number')
        
        # Warn if no uppercase
        if not re.search(r'[A-Z]', password):
            errors.append('Recommended: include at least one uppercase letter')
        
        # Warn if no special chars
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            errors.append('Recommended: include special characters (!@#$%)', )
        
        if errors:
            return False, ' | '.join(errors)
        
        return True, 'Password is strong'


class TOTPManager:
    """Manage Time-based One-Time Passwords (2FA)"""
    
    @staticmethod
    def generate_secret():
        """Generate a new TOTP secret (base32 encoded)"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp(secret):
        """Create TOTP object from secret"""
        return pyotp.TOTP(secret)
    
    @staticmethod
    def get_provisioning_uri(secret, name, issuer="Soporte Tecnico"):
        """
        Get provisioning URI for QR code
        name should be username/email
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=name, issuer_name=issuer)
    
    @staticmethod
    def get_qr_code_svg(provisioning_uri):
        """Generate QR code as SVG (no PIL dependency)"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes
    
    @staticmethod
    def verify_token(secret, token):
        """Verify a TOTP token (allows for time drift)"""
        try:
            totp = pyotp.TOTP(secret)
            # Allow time drift of ±30 seconds (1 time step)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
    
    @staticmethod
    def generate_backup_codes(count=10):
        """Generate backup codes for account recovery"""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        return codes
    
    @staticmethod
    def verify_backup_code(codes_str, code):
        """Verify a backup code and remove it from the list"""
        if not codes_str:
            return False
        
        codes = codes_str.split(',')
        if code.upper() in codes:
            # Remove used code
            codes.remove(code.upper())
            return True, ','.join(codes)
        
        return False, codes_str


class FileSecurityValidator:
    """Validate uploaded files for security threats"""
    
    MAGIC_NUMBERS = {
        b'\xFF\xD8\xFF': 'jpeg',           # JPEG
        b'\x89\x50\x4E\x47': 'png',        # PNG
        b'\x47\x49\x46': 'gif',            # GIF
        b'\x42\x4D': 'bmp',                # BMP
        b'\x25\x50\x44\x46': 'pdf',        # PDF
        b'\x50\x4B\x03\x04': 'zip',        # ZIP
        b'\x1F\x8B\x08': 'gzip',           # GZIP
    }
    
    @staticmethod
    def validate(file_storage):
        """
        Validate a file for security issues
        Returns: (is_valid, error_message, file_type)
        """
        if not file_storage or not file_storage.filename:
            return False, 'No file provided', None
        
        filename = secure_filename(file_storage.filename)
        if not filename:
            return False, 'Invalid filename', None
        
        # Check file extension
        file_ext = filename.rsplit('.', 1)[-1].lower()
        
        if file_ext in DANGEROUS_EXTENSIONS:
            return False, f'File type .{file_ext} is not allowed', None
        
        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f'File type .{file_ext} not in whitelist', None
        
        # Read file header for MIME type detection
        file_storage.seek(0)
        file_header = file_storage.read(512)
        file_storage.seek(0)
        
        if not file_header:
            return False, 'Empty file', None
        
        # Check magic numbers (file signatures)
        detected_type = FileSecurityValidator._detect_mime_type(file_header, filename)
        
        if detected_type not in ALLOWED_MIMETYPES:
            return False, f'File MIME type {detected_type} not allowed. Expected: {ALLOWED_EXTENSIONS}', None
        
        # Size check (max 20MB)
        file_storage.seek(0, 2)  # Seek to end
        file_size = file_storage.tell()
        file_storage.seek(0)  # Reset
        
        if file_size > 20 * 1024 * 1024:
            return False, 'File exceeds 20MB limit', None
        
        if file_size == 0:
            return False, 'Empty file', None
        
        return True, 'File is safe', detected_type
    
    @staticmethod
    def _detect_mime_type(file_header, filename):
        """Detect MIME type from file header and extension"""
        file_ext = filename.rsplit('.', 1)[-1].lower()
        
        # Try magic number detection
        for magic_num, file_type in FileSecurityValidator.MAGIC_NUMBERS.items():
            if file_header.startswith(magic_num):
                return f'application/{file_type}' if file_type != 'jpeg' else 'image/jpeg'
        
        # Fallback to extension-based detection
        mime_map = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'zip': 'application/zip',
        }
        
        return mime_map.get(file_ext, 'application/octet-stream')
    
    @staticmethod
    def scan_for_malware(file_path):
        """
        Scan file for malware (simple heuristic check)
        In production, integrate with ClamAV or VirusTotal
        
        For now: Check for suspicious content in text files
        """
        suspicious_patterns = [
            b'powershell',
            b'cmd.exe',
            b'/bin/bash',
            b'wget ',
            b'curl ',
            b'eval(',
            b'exec(',
            b'system(',
        ]
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024)  # First 1MB
                
                for pattern in suspicious_patterns:
                    if pattern in content.lower():
                        return False, f'Suspicious pattern detected: {pattern.decode()}'
            
            return True, 'File passed malware scan'
        except Exception as e:
            return False, f'Error scanning file: {str(e)}'


class AuditHelper:
    """Helper functions for security auditing"""
    
    @staticmethod
    def get_client_ip():
        """Get client IP address (handles proxies)"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return request.remote_addr or '0.0.0.0'
    
    @staticmethod
    def get_user_agent():
        """Get user agent string"""
        return request.headers.get('User-Agent', 'Unknown')[:500]
    
    @staticmethod
    def log_login_attempt(user, success, ip_address=None, user_agent=None):
        """Log a login attempt (success or failure)"""
        from soporte_empresa.app.models import AuditLog
        
        if ip_address is None:
            ip_address = AuditHelper.get_client_ip()
        if user_agent is None:
            user_agent = AuditHelper.get_user_agent()
        
        AuditLog.log_action(
            user_id=user.id if user else None,
            action='login',
            resource_type='user',
            resource_id=user.id if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status='success' if success else 'failure'
        )
    
    @staticmethod
    def log_password_change(user_id, ip_address=None, user_agent=None):
        """Log a password change"""
        from soporte_empresa.app.models import AuditLog
        
        if ip_address is None:
            ip_address = AuditHelper.get_client_ip()
        if user_agent is None:
            user_agent = AuditHelper.get_user_agent()
        
        AuditLog.log_action(
            user_id=user_id,
            action='password_change',
            resource_type='user',
            resource_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_2fa_setup(user_id, enabled, ip_address=None, user_agent=None):
        """Log 2FA setup/disable"""
        from soporte_empresa.app.models import AuditLog
        
        if ip_address is None:
            ip_address = AuditHelper.get_client_ip()
        if user_agent is None:
            user_agent = AuditHelper.get_user_agent()
        
        AuditLog.log_action(
            user_id=user_id,
            action='2fa_' + ('enabled' if enabled else 'disabled'),
            resource_type='user',
            resource_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_ticket_action(user_id, action, ticket_id, ip_address=None, user_agent=None):
        """Log ticket-related actions"""
        from soporte_empresa.app.models import AuditLog
        
        if ip_address is None:
            ip_address = AuditHelper.get_client_ip()
        if user_agent is None:
            user_agent = AuditHelper.get_user_agent()
        
        AuditLog.log_action(
            user_id=user_id,
            action=f'ticket_{action}',
            resource_type='ticket',
            resource_id=ticket_id,
            ip_address=ip_address,
            user_agent=user_agent
        )


class EncryptionManager:
    """Encrypt/decrypt sensitive data like API tokens"""
    
    @staticmethod
    def get_cipher():
        """Get Fernet cipher for encryption"""
        try:
            # Use SECRET_KEY for encryption key (derived from Flask config)
            secret = current_app.config.get('SECRET_KEY', 'default-insecure-key')
            
            # Ensure key is exactly 32 bytes for Fernet
            if isinstance(secret, str):
                secret = secret.encode('utf-8')
            
            # If key is not 32 bytes, hash it
            if len(secret) != 32:
                import hashlib
                secret = hashlib.sha256(secret).digest()
            
            # Base64 encode for Fernet
            key = base64.urlsafe_b64encode(secret)
            return Fernet(key)
        except Exception as e:
            raise RuntimeError(f'Failed to initialize encryption: {e}')
    
    @staticmethod
    def encrypt(data):
        """Encrypt string data"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            cipher = EncryptionManager.get_cipher()
            encrypted = cipher.encrypt(data)
            return encrypted.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f'Encryption failed: {e}')
    
    @staticmethod
    def decrypt(encrypted_data):
        """Decrypt string data"""
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode('utf-8')
            
            cipher = EncryptionManager.get_cipher()
            decrypted = cipher.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f'Decryption failed: {e}')

