"""共享工具函数"""
import os
import json
from urllib.parse import unquote
from dotenv import load_dotenv


# 配置
PAGE_TIMEOUT = 60000


def extract_user_info_from_cookies(cookie_str):
    """从 Cookie 中提取用户信息用于设置 localStorage"""
    user_info = {}

    # 解析 lginfo cookie - 它是 URL 编码的 JSON
    for item in cookie_str.split(';'):
        item = item.strip()
        if item.startswith('lginfo='):
            lginfo_value = item[7:]  # Remove 'lginfo='
            lginfo_decoded = unquote(lginfo_value)
            # 尝试解析为 JSON
            try:
                user_info = json.loads(lginfo_decoded)
            except json.JSONDecodeError:
                # 如果不是 JSON，尝试解析 key=value&key=value 格式
                for pair in lginfo_decoded.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        user_info[k] = v
            break

    # 如果没有从 lginfo 获取到，尝试从 addinfo 获取
    if not user_info.get('uid'):
        for item in cookie_str.split(';'):
            item = item.strip()
            if item.startswith('addinfo='):
                # addinfo 格式: uid|username|phone|token
                parts = item[8:].split('|')
                if len(parts) >= 4:
                    user_info = {
                        'uid': int(parts[0]),
                        'username': parts[1],
                        'nickname': parts[1],
                        'bind_phone': parts[2],
                        'token': parts[3]
                    }
                break

    # 确保有 token
    if not user_info.get('token'):
        for item in cookie_str.split(';'):
            item = item.strip()
            if item.startswith('token='):
                user_info['token'] = item[6:]
                break

    return user_info


def init_localstorage(page, cookie_str):
    """在当前页面设置 localStorage 以确保 Vue 应用识别登录状态"""
    user_info = extract_user_info_from_cookies(cookie_str)

    if not user_info.get('uid'):
        print("警告: 无法从 Cookie 中提取用户信息")
        return False

    # 如果 user_info 已经是完整的 lginfo 格式，直接使用
    # 否则构建完整的 lginfo 对象
    if 'setPasswd' not in user_info:
        lginfo = {
            "uid": int(user_info.get('uid', 0)),
            "username": user_info.get('username', user_info.get('nickname', '')),
            "nickname": user_info.get('nickname', user_info.get('username', '')),
            "email": user_info.get('email', ''),
            "photo": user_info.get('photo', ''),
            "bind_phone": user_info.get('bind_phone', ''),
            "sex": int(user_info.get('sex', 0)),
            "token": user_info.get('token', ''),
            "setPasswd": 1,
            "bindWechat": user_info.get('bindWechat', False),
            "bindQq": user_info.get('bindQq', False),
            "bindSina": user_info.get('bindSina', False),
            "status": user_info.get('status', 1),
            "is_sign": user_info.get('is_sign', True),
            "user_level": user_info.get('user_level', 1),
            "isInUserWhitelist": user_info.get('isInUserWhitelist', False)
        }
    else:
        lginfo = user_info

    # Set localStorage
    lginfo_json = json.dumps(lginfo, ensure_ascii=False)
    page.evaluate(f'localStorage.setItem("lginfo", {json.dumps(lginfo_json)})')
    print(f"已设置 localStorage (uid: {lginfo.get('uid')})")
    return True


def get_all_cookies():
    """获取所有账号的 Cookie"""
    load_dotenv()  # 自动加载 .env 文件（本地测试用）

    cookies_list = []
    single = os.environ.get('ZAIMANHUA_COOKIE')
    if single:
        cookies_list.append(('默认账号', single))
    i = 1
    while True:
        cookie = os.environ.get(f'ZAIMANHUA_COOKIE_{i}')
        if cookie:
            cookies_list.append((f'账号 {i}', cookie))
            i += 1
        else:
            break
    return cookies_list


def parse_cookies(cookie_str):
    """解析 Cookie 字符串为 Playwright 格式"""
    cookies = []
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.zaimanhua.com',
                'path': '/'
            })
    return cookies


def claim_rewards(page):
    """在用户中心领取已完成任务的积分"""
    print("\n=== 领取积分任务 ===")
    try:
        # 访问用户中心
        print("访问用户中心...")
        page.goto('https://i.zaimanhua.com/', wait_until='domcontentloaded')
        page.wait_for_timeout(5000)

        # 查找所有可领取的按钮
        claim_buttons = page.query_selector_all(".okBtn")
        claimed_count = 0

        if claim_buttons:
            print(f"找到 {len(claim_buttons)} 个可领取的奖励")
            for i, btn in enumerate(claim_buttons):
                try:
                    btn_text = btn.inner_text()
                    print(f"  点击领取按钮 {i+1}: {btn_text}")
                    btn.click()
                    page.wait_for_timeout(1500)
                    claimed_count += 1
                except Exception as e:
                    print(f"  领取按钮 {i+1} 点击失败: {e}")

            print(f"成功领取 {claimed_count} 个奖励")
            return claimed_count > 0
        else:
            print("没有可领取的奖励")
            return True  # 没有奖励也算成功

    except Exception as e:
        print(f"领取积分失败: {e}")
        return False


def create_browser_context(playwright, cookie_str):
    """创建浏览器上下文"""
    cookies = parse_cookies(cookie_str)
    print(f"已解析 {len(cookies)} 个 Cookie")

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    context.add_cookies(cookies)
    page = context.new_page()
    page.set_default_timeout(PAGE_TIMEOUT)

    return browser, context, page
