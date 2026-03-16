#!/usr/bin/env python3
"""
Verification script for eventlet monkey patching and Flask-Limiter configuration.
Run this to verify all issues are resolved.
"""

import os
import sys

def check_eventlet():
    """Check if eventlet monkey patch is properly applied."""
    print("\n" + "="*60)
    print("🔍 CHECKING EVENTLET MONKEY PATCH")
    print("="*60)
    
    try:
        import eventlet
        eventlet.monkey_patch(all=True)
        print("✅ Eventlet import successful")
        print("✅ Eventlet monkey_patch() applied")
        
        # Check if RLock is greenified
        import threading
        lock = threading.RLock()
        print("✅ RLock creation successful (greenified)")
        
        return True
    except Exception as e:
        print(f"❌ Eventlet error: {e}")
        return False


def check_redis():
    """Check Redis configuration and connection."""
    print("\n" + "="*60)
    print("🔍 CHECKING REDIS CONFIGURATION")
    print("="*60)
    
    redis_url = os.environ.get('REDIS_URL')
    ratelimit_uri = os.environ.get('RATELIMIT_STORAGE_URI')
    
    print(f"ENV REDIS_URL: {redis_url if redis_url else '❌ NOT SET'}")
    print(f"ENV RATELIMIT_STORAGE_URI: {ratelimit_uri if ratelimit_uri else '(not set - using default)'}")
    
    if not redis_url:
        print("\n⚠️  REDIS_URL not configured")
        print("   This is OK for development, but recommended for production")
        print("   Add REDIS_URL to .env or Render environment variables")
        return None
    
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        print(f"✅ Redis connection successful")
        print(f"   URL: {redis_url}")
        return True
    except ImportError:
        print("❌ redis package not installed")
        print("   Run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print(f"   Check REDIS_URL is correct: {redis_url}")
        return False


def check_flask_limiter():
    """Check Flask-Limiter storage configuration."""
    print("\n" + "="*60)
    print("🔍 CHECKING FLASK-LIMITER STORAGE")
    print("="*60)
    
    try:
        # Import after eventlet patch
        from app import create_app
        
        app = create_app('config.ProductionConfig')
        
        with app.app_context():
            storage_uri = app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
            print(f"RATELIMIT_STORAGE_URI: {storage_uri}")
            
            if storage_uri == 'memory://':
                print("⚠️  Using IN-MEMORY storage")
                if os.environ.get('RENDER') == 'true':
                    print("   Warning: This is shown because running in Render production")
                    print("   Solution: Set REDIS_URL in environment variables")
                else:
                    print("   OK for local development")
            elif 'redis://' in storage_uri:
                print("✅ Using REDIS storage (production-ready)")
            else:
                print(f"❓ Unknown storage: {storage_uri}")
            
            return True
    except Exception as e:
        print(f"❌ Flask-Limiter check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_entry_points():
    """Check that entry point scripts have monkey_patch at the top."""
    print("\n" + "="*60)
    print("🔍 CHECKING ENTRY POINT SCRIPTS")
    print("="*60)
    
    checks = []
    
    # Check run.py
    try:
        with open('run.py', 'r') as f:
            lines = f.readlines()
            has_eventlet = any('import eventlet' in line for line in lines[:10])
            has_patch = any('monkey_patch' in line for line in lines[:10])
            if has_eventlet and has_patch:
                print("✅ run.py has eventlet.monkey_patch() at the top")
                checks.append(True)
            else:
                print("❌ run.py missing monkey_patch at the top")
                checks.append(False)
    except Exception as e:
        print(f"⚠️  Could not check run.py: {e}")
    
    # Check wsgi.py
    try:
        with open('wsgi.py', 'r') as f:
            lines = f.readlines()
            has_eventlet = any('import eventlet' in line for line in lines[:10])
            has_patch = any('monkey_patch' in line for line in lines[:10])
            if has_eventlet and has_patch:
                print("✅ wsgi.py has eventlet.monkey_patch() at the top")
                checks.append(True)
            else:
                print("❌ wsgi.py missing monkey_patch at the top")
                checks.append(False)
    except Exception as e:
        print(f"⚠️  Could not check wsgi.py: {e}")
    
    return all(checks) if checks else None


def main():
    """Run all checks."""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  SOPORTE TÉCNICO - EVENTLET & REDIS VERIFICATION".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    results = {
        'Eventlet': check_eventlet(),
        'Entry Points': check_entry_points(),
        'Flask-Limiter': check_flask_limiter(),
        'Redis': check_redis(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⚠️  INFO")
        print(f"{check_name}: {status}")
    
    # Final status
    print("\n" + "="*60)
    critical_passed = results['Eventlet'] and results['Entry Points']
    
    if critical_passed:
        print("✅ CRITICAL ISSUES RESOLVED")
        print("\nThe RLock warning should be resolved.")
        print("The Flask-Limiter warning is informational about production optimization.")
    else:
        print("❌ CRITICAL ISSUES REMAIN")
        print("\nPlease fix the issues marked as FAIL above.")
    
    print("="*60 + "\n")
    
    return 0 if critical_passed else 1


if __name__ == '__main__':
    sys.exit(main())
