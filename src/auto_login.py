"""自动登录模块 - Cookie失效时的备用方案

当配置的Cookie失效时，使用账号密码自动登录获取新Cookie
支持多账号配置:
- ZAIMANHUA_USERNAME / ZAIMANHUA_PASSWORD: 默认账号
- ZAIMANHUA_USERNAME_1 / ZAIMANHUA_PASSWORD_1: 账号1
- ZAIMANHUA_USERNAME_2 / ZAIMANHUA_PASSWORD_2: 账号2
...
"""
import os
import time
from playwright.sync_api import sync_playwright


def get_login_credentials(index=None):
    """从环境变量获取登录凭据
    
    Args:
        index: 账号索引，None表示默认账号，1/2/3...表示对应账号
        
    Returns:
        (username, password) 或 (None, None)
    """
    if index is None or index == 0:
        username = os.environ.get('ZAIMANHUA_USERNAME')
        password = os.environ.get('ZAIMANHUA_PASSWORD')
    else:
        username = os.environ.get(f'ZAIMANHUA_USERNAME_{index}')
        password = os.environ.get(f'ZAIMANHUA_PASSWORD_{index}')
    
    if not username or not password:
        return None, None
    
    return username, password


def get_all_login_credentials():
    """获取所有配置的登录凭据
    
    Returns:
        list: [(label, username, password), ...]
    """
    credentials_list = []
    
    # 默认账号
    username, password = get_login_credentials(None)
    if username and password:
        credentials_list.append(('默认账号', username, password))
    
    # 多账号
    i = 1
    while True:
        username, password = get_login_credentials(i)
        if username and password:
            credentials_list.append((f'账号 {i}', username, password))
            i += 1
        else:
            break
    
    return credentials_list


def login_and_get_cookie(username, password):
    """使用Playwright自动登录并获取Cookie
    
    Args:
        username: 用户名/手机/邮箱
        password: 密码
        
    Returns:
        cookie_str: 登录后的cookie字符串，失败返回None
    """
    print(f"\n=== 自动登录 ===")
    print(f"  账号: {username}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # 访问登录页面
            print("  访问登录页面...")
            page.goto('https://i.zaimanhua.com/login', wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            
            # 输入用户名
            print("  输入用户名...")
            username_input = page.locator('#form_item_username').first
            if not username_input.is_visible(timeout=5000):
                print("  [x] 未找到用户名输入框")
                browser.close()
                return None
            
            username_input.fill(username)
            page.wait_for_timeout(500)
            
            # 输入密码
            print("  输入密码...")
            password_input = page.locator('#form_item_passwd').first
            if not password_input.is_visible(timeout=5000):
                print("  [x] 未找到密码输入框")
                browser.close()
                return None
            
            password_input.fill(password)
            page.wait_for_timeout(500)
            
            # 点击登录按钮
            print("  点击登录按钮...")
            login_btn = page.locator('button.login-form-button').first
            if not login_btn.is_visible(timeout=5000):
                print("  [x] 未找到登录按钮")
                browser.close()
                return None
            
            # 等待按钮可用（disabled属性消失）
            page.wait_for_timeout(1000)
            login_btn.click(timeout=10000)
            
            # 等待登录完成（页面跳转或出现用户信息）
            print("  等待登录完成...")
            page.wait_for_timeout(5000)
            
            # 检查是否登录成功
            current_url = page.url
            print(f"  当前URL: {current_url}")
            
            # 如果URL包含login，可能登录失败
            if 'login' in current_url:
                # 检查是否有错误提示
                error_selectors = [
                    '.ant-form-item-explain-error',
                    '.ant-message-error',
                    '.error-message',
                    '[class*="error"]'
                ]
                for selector in error_selectors:
                    try:
                        error_elem = page.locator(selector).first
                        if error_elem.is_visible(timeout=2000):
                            error_text = error_elem.inner_text(timeout=2000)
                            print(f"  [x] 登录失败: {error_text}")
                            browser.close()
                            return None
                    except:
                        pass
                
                print("  [x] 登录失败，仍在登录页面")
                browser.close()
                return None
            
            # 获取Cookie
            print("  获取Cookie...")
            cookies = context.cookies()
            
            # 构建cookie字符串
            cookie_parts = []
            for cookie in cookies:
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                if name and value:
                    cookie_parts.append(f"{name}={value}")
            
            cookie_str = '; '.join(cookie_parts)
            
            if not cookie_str:
                print("  [x] 未获取到Cookie")
                browser.close()
                return None
            
            # 验证获取的Cookie是否有效
            print("  验证Cookie有效性...")
            from utils import validate_cookie
            is_valid, error_msg = validate_cookie(cookie_str)
            
            if is_valid:
                print(f"  [v] 自动登录成功，获取到有效Cookie (长度: {len(cookie_str)})")
                browser.close()
                return cookie_str
            else:
                print(f"  [x] 获取的Cookie无效: {error_msg}")
                browser.close()
                return None
                
    except Exception as e:
        print(f"  [x] 自动登录异常: {e}")
        return None


def get_valid_cookie(original_cookie_str, account_name="", account_index=None):
    """获取有效的Cookie，如果原Cookie失效或未配置则尝试自动登录
    
    Args:
        original_cookie_str: 原始配置的Cookie（可为空）
        account_name: 账号名称（用于日志）
        account_index: 账号索引，用于获取对应的多账号凭据
        
    Returns:
        (cookie_str, is_auto_login): 有效的cookie字符串和是否通过自动登录获取
    """
    from utils import validate_cookie
    
    print(f"\n{'='*50}")
    if account_name:
        print(f"账号: {account_name}")
    
    # 如果有原始Cookie，先验证
    if original_cookie_str and original_cookie_str.strip():
        print("验证Cookie有效性...")
        is_valid, error_msg = validate_cookie(original_cookie_str)
        
        if is_valid:
            print("  [v] Cookie有效，直接使用")
            return original_cookie_str, False
        
        print(f"  [!] Cookie无效: {error_msg}")
    else:
        print("未配置Cookie，尝试自动登录...")
    
    # 尝试自动登录（使用对应索引的账号密码）
    print("  尝试自动登录获取新Cookie...")
    username, password = get_login_credentials(account_index)
    
    if not username or not password:
        print("  [x] 未配置自动登录凭据")
        return None, False
    
    new_cookie = login_and_get_cookie(username, password)
    
    if new_cookie:
        return new_cookie, True
    else:
        print("  [x] 自动登录失败，无法获取有效Cookie")
        return None, False


if __name__ == '__main__':
    # 测试自动登录
    cookie, is_auto = get_valid_cookie("", "测试账号")
    if cookie:
        print(f"\n获取到Cookie: {cookie[:100]}...")
        print(f"是否自动登录: {is_auto}")
    else:
        print("\n无法获取有效Cookie")
