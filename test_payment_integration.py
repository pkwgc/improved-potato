#!/usr/bin/env python3
"""
Test WeChat Payment Integration
"""

import sys
import os

def test_wechat_payment_integration():
    """Test WeChat payment integration import"""
    try:
        sys.path.append('/home/ubuntu/repos/improved-potato/wechat_ai_system')
        from wechat_payment_integration import register_wechat_payment_routes
        print('✓ WeChat payment integration import successful')
        return True
    except ImportError as e:
        print(f'✗ Import error: {e}')
        return False
    except Exception as e:
        print(f'✗ Other error: {e}')
        return False

def test_payment_params_generation():
    """Test payment parameter generation"""
    try:
        sys.path.append('/home/ubuntu/repos/improved-potato/wechat_ai_system')
        from order_processing import generate_wechat_payment_params
        params = generate_wechat_payment_params('TEST-001', 0.01, 'test_user')
        print('✓ Payment parameter generation successful')
        print(f'Generated params: {params}')
        return True
    except Exception as e:
        print(f'✗ Error: {e}')
        return False

if __name__ == "__main__":
    print("Testing WeChat Payment Integration...")
    test1 = test_wechat_payment_integration()
    test2 = test_payment_params_generation()
    
    if test1 and test2:
        print("✓ All integration tests passed")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
