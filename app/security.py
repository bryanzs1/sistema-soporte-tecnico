"""Security utilities for password validation, 2FA, and auditing"""

import re
import secrets
import qrcode
from io import BytesIO
import pyotp
from flask import request


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
        from app.models import AuditLog
        
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
        from app.models import AuditLog
        
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
        from app.models import AuditLog
        
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
        from app.models import AuditLog
        
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
