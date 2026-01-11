import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# 配置
MAX_RETRIES = 3
PAGE_TIMEOUT = 60000  # 60秒


def get_all_cookies():
    """获取所有账号的 Cookie"""
    load_dotenv()  # 自动加载 .env 文件（本地测试用）

    cookies_list = []

    # 兼容单账号配置
    single = os.environ.get('ZAIMANHUA_COOKIE')
    if single:
        cookies_list.append(('默认账号', single))

    # 支持多账号配置 ZAIMANHUA_COOKIE_1, _2, _3...
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


def checkin_once(cookie_str):
    """执行一次签到尝试"""
    cookies = parse_cookies(cookie_str)
    print(f"已解析 {len(cookies)} 个 Cookie")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 使用真实浏览器 User-Agent
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 添加 Cookie
        context.add_cookies(cookies)

        page = context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT)

        try:
            # 访问页面，增加超时时间
            page.goto('https://i.zaimanhua.com/', timeout=PAGE_TIMEOUT)

            # 等待页面加载
            page.wait_for_load_state('networkidle', timeout=PAGE_TIMEOUT)
            print(f"页面标题: {page.title()}")

            # 等待签到按钮出现
            page.wait_for_selector('.ant-btn-primary', timeout=10000)

            # 获取按钮信息
            button = page.locator('.ant-btn-primary').first
            button_text = button.inner_text()
            is_disabled = button.is_disabled()

            print(f"按钮文字: {button_text}")
            print(f"按钮禁用状态: {is_disabled}")

            if is_disabled:
                # 检查是否已签到（按钮禁用可能意味着已签到）
                if "已签到" in button_text or "已领取" in button_text:
                    print("今天已经签到过了！")
                    result = True
                else:
                    # 可能是未登录状态，尝试用 JavaScript 强制点击
                    print("按钮被禁用，尝试使用 JavaScript 点击...")
                    page.evaluate("document.querySelector('.ant-btn-primary').click()")
                    page.wait_for_timeout(2000)
                    print("JavaScript 点击完成")
                    result = True
            else:
                # 按钮可用，正常点击
                button.click()
                page.wait_for_timeout(2000)
                print("签到成功！")
                result = True

        except Exception as e:
            print(f"签到失败: {e}")
            # 保存截图用于调试
            try:
                page.screenshot(path="error_screenshot.png")
                print("已保存错误截图: error_screenshot.png")
            except:
                pass
            result = False
        finally:
            browser.close()

        return result


def checkin(cookie_str):
    """执行签到，带重试机制"""
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"尝试第 {attempt}/{MAX_RETRIES} 次...")
        try:
            if checkin_once(cookie_str):
                return True
        except Exception as e:
            print(f"第 {attempt} 次尝试出错: {e}")

        if attempt < MAX_RETRIES:
            wait_time = attempt * 10  # 递增等待时间
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

    print(f"已重试 {MAX_RETRIES} 次，签到失败")
    return False


def main():
    """主函数，支持多账号签到"""
    cookies_list = get_all_cookies()

    if not cookies_list:
        print("Error: 未配置任何账号 Cookie")
        print("请设置 ZAIMANHUA_COOKIE 或 ZAIMANHUA_COOKIE_1, ZAIMANHUA_COOKIE_2 等环境变量")
        return False

    print(f"共发现 {len(cookies_list)} 个账号")

    all_success = True
    for name, cookie_str in cookies_list:
        print(f"\n{'='*40}")
        print(f"正在签到: {name}")
        print('='*40)
        success = checkin(cookie_str)
        if not success:
            all_success = False

    print(f"\n{'='*40}")
    if all_success:
        print("所有账号签到完成！")
    else:
        print("部分账号签到失败，请检查日志")

    return all_success


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
