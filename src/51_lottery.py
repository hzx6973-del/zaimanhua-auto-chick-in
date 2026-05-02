"""2026 五一狂欢抽奖活动自动化模块（浏览器自动化版）

活动页面: https://activity.zaimanhua.com/51-lottery/
任务: 分享活动、阅读任务、祝福评论
完成后抽奖，打印抽奖结果

采用 Playwright 浏览器自动化，模拟真实用户操作
"""
import random
import time
import re

from utils import (
    extract_user_info_from_cookies,
    get_all_cookies,
    parse_cookies,
    validate_cookie,
)
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# 配置
BASE_URL = "https://activity.zaimanhua.com"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

BLESSINGS = [
    "五一快乐！劳动最光荣！",
    "节日快乐，愿所有辛劳都有回报！",
    "五一假期愉快，放松身心！",
    "劳动者最光荣，节日快乐！",
    "愿这个五一充满欢笑和美好！",
    "五一快乐，享受美好时光！",
    "致敬劳动者，五一快乐！",
    "假期愉快，充电满满再出发！",
    "五一快乐，好运连连！",
    "愿所有努力都不被辜负，节日快乐！",
    "五一放松，快乐加倍！",
    "劳动创造美好，节日快乐！",
    "五一快乐，幸福安康！",
    "享受假期，五一愉快！",
    "愿五一的阳光照亮你的每一天！",
]


def setup_browser_context(p, cookie_str: str):
    """初始化浏览器上下文并添加 Cookie"""
    cookies = parse_cookies(cookie_str)
    activity_cookies = [
        {"name": c["name"], "value": c["value"], "domain": "activity.zaimanhua.com", "path": "/"}
        for c in cookies
    ]
    main_cookies = [
        {"name": c["name"], "value": c["value"], "domain": ".zaimanhua.com", "path": "/"}
        for c in cookies
    ]

    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=MOBILE_UA,
        viewport={"width": 375, "height": 812},
    )
    context.add_cookies(activity_cookies + main_cookies)
    return browser, context


def get_task_status(page) -> list:
    """检查页面上的任务状态，返回未完成的任务索引列表 [0, 1, 2]"""
    page.goto(f"{BASE_URL}/51-lottery/", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)

    # 查找所有任务按钮
    # 使用多种选择器来找到所有任务按钮
    tasks = []
    try:
        # 首先尝试查找 .btn 类的按钮
        buttons = page.locator(".btn").all()
        if len(buttons) >= 3:
            for i, btn in enumerate(buttons[:3]):  # 只取前3个
                try:
                    text = btn.inner_text(timeout=2000).strip()
                    print(f"    任务按钮 {i+1}: 文本='{text}'")
                    if "去完成" in text:
                        tasks.append(i)
                except:
                    continue
        else:
            # 如果找不到足够的按钮，尝试其他选择器
            print(f"    只找到 {len(buttons)} 个按钮，尝试其他选择器...")

            # 尝试查找包含"去完成"或"已完成"的元素
            all_buttons = page.locator("button, div, span").all()
            task_idx = 0
            for elem in all_buttons:
                try:
                    text = elem.inner_text(timeout=1000).strip()
                    if text in ["去完成", "已完成"] and task_idx < 3:
                        print(f"    任务按钮 {task_idx+1}: 文本='{text}'")
                        if text == "去完成":
                            tasks.append(task_idx)
                        task_idx += 1
                except:
                    continue
    except Exception as e:
        print(f"  [x] 获取任务状态异常: {e}")

    return tasks


def click_task_button(page, task_idx: int) -> bool:
    """点击指定索引的任务按钮"""
    try:
        # 获取所有按钮，找到第 task_idx 个包含"去完成"的按钮
        buttons = page.locator(".btn").all()
        unfinished_btns = []
        for btn in buttons:
            try:
                text = btn.inner_text(timeout=2000).strip()
                if "去完成" in text:
                    unfinished_btns.append(btn)
            except:
                continue

        if task_idx < len(unfinished_btns):
            unfinished_btns[task_idx].click(timeout=5000)
            return True
        else:
            print(f"  [x] 找不到任务按钮索引 {task_idx}")
            return False
    except Exception as e:
        print(f"  [x] 点击任务按钮异常: {e}")
        return False


def do_share_task(page, task_idx: int = 0) -> bool:
    """完成分享任务：点击去完成 -> 点击复制按钮"""
    try:
        print("  [分享任务] 点击'去完成'...")
        if not click_task_button(page, task_idx):
            return False
        page.wait_for_timeout(2000)

        # 点击复制按钮
        print("  [分享任务] 点击复制按钮...")
        copy_btn = page.locator("img.copyBtn").first
        if not copy_btn.is_visible(timeout=3000):
            # 尝试其他选择器
            copy_btn = page.locator("img[src*='copy']").first
        if not copy_btn.is_visible(timeout=3000):
            # 尝试查找包含"复制"文本的按钮
            copy_btn = page.locator("button, div, span").filter(has_text="复制").first
        if not copy_btn.is_visible(timeout=3000):
            # 尝试点击弹窗中的任意按钮
            copy_btn = page.locator(".popup button, .modal button, .dialog button").first

        if copy_btn and copy_btn.is_visible(timeout=3000):
            copy_btn.click(timeout=3000)
            page.wait_for_timeout(2000)
            print("  [v] 分享任务完成")
            return True
        else:
            print("  [x] 未找到复制按钮，尝试关闭弹窗...")
            # 尝试按 ESC 关闭弹窗
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            return True  # 即使没找到按钮也视为完成
    except Exception as e:
        print(f"  [x] 分享任务异常: {e}")
        return False


def do_read_task(page, task_idx: int = 0) -> bool:
    """完成阅读任务：点击去完成 -> 访问漫画详情页面阅读（参考往期活动）"""
    try:
        print("  [阅读任务] 点击'去完成'...")
        if not click_task_button(page, task_idx):
            return False

        # 等待一段时间，看是否有弹窗或页面跳转
        print("  [阅读任务] 等待页面响应...")
        page.wait_for_timeout(5000)

        # 检查当前页面URL
        current_url = page.url
        print(f"  [阅读任务] 当前页面: {current_url}")

        # 访问活动页面推荐的漫画（从活动页面获取的链接）
        print("  [阅读任务] 访问漫画详情页面...")
        page.goto("https://zt.zaimanhua.com/details?id=592", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # 查找并点击阅读按钮
        read_btn = page.locator(".readBtn, .read-btn, [class*='read']").first
        if read_btn.is_visible(timeout=5000):
            print(f"  [阅读任务] 找到阅读按钮: {read_btn.inner_text(timeout=2000).strip()[:20]}")
            read_btn.click(timeout=3000)
            page.wait_for_timeout(8000)
            print(f"  [阅读任务] 已打开漫画阅读页面: {page.url}")

            # 在漫画页面停留并滚动，模拟阅读
            print("  [阅读任务] 模拟阅读...")
            for _ in range(5):
                page.keyboard.press("PageDown")
                page.wait_for_timeout(3000)

            # 额外等待，确保服务器记录阅读行为
            page.wait_for_timeout(10000)
        else:
            print("  [阅读任务] 未找到阅读按钮，尝试直接访问漫画页面...")
            # 备用方案：直接访问漫画阅读页面
            page.goto("https://m.zaimanhua.com/pages/comic/detail?id=52749", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(10000)

        print("  [v] 阅读漫画任务完成")
        return True
    except Exception as e:
        print(f"  [x] 阅读任务异常: {e}")
        return False


def do_comment_task(page, task_idx: int = 0) -> bool:
    """完成评论任务：输入祝福语 -> 点击发布"""
    try:
        print("  [评论任务] 点击'去完成'...")
        if not click_task_button(page, task_idx):
            return False
        page.wait_for_timeout(2000)

        # 输入祝福语
        blessing = random.choice(BLESSINGS)
        print(f"  [评论任务] 输入祝福语: {blessing}")

        input_box = page.locator("input.comment-input").first
        if not input_box.is_visible(timeout=3000):
            # 尝试其他选择器
            input_box = page.locator("input[placeholder*='评论']").first

        if input_box.is_visible(timeout=3000):
            input_box.fill(blessing)
            page.wait_for_timeout(1000)

            # 点击发布按钮
            submit_btn = page.locator("text=发布").first
            if submit_btn.is_visible(timeout=3000):
                submit_btn.click(timeout=3000)
                page.wait_for_timeout(2000)
                print("  [v] 评论任务完成")
                return True
            else:
                print("  [x] 未找到发布按钮")
                return False
        else:
            print("  [x] 未找到评论输入框")
            return False
    except Exception as e:
        print(f"  [x] 评论任务异常: {e}")
        return False


def get_draw_count(page) -> int:
    """获取当前抽奖次数"""
    try:
        # 刷新页面获取最新状态
        page.goto(f"{BASE_URL}/51-lottery/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # 查找抽奖次数元素
        count_elem = page.locator(".draw-count").first
        if count_elem.is_visible(timeout=5000):
            text = count_elem.inner_text(timeout=2000)
            print(f"    抽奖次数文本: {text}")
            # 提取数字
            match = re.search(r"\d+", text)
            if match:
                return int(match.group())

        return 0
    except Exception as e:
        print(f"  [x] 获取抽奖次数异常: {e}")
        return 0


def close_win_prize(page):
    """关闭抽奖结果弹窗"""
    print("    [debug] 关闭弹窗...")
    closed = False

    # 方法1: 尝试点击确定按钮
    try:
        ok_btn = page.locator(".okBtn").first
        if ok_btn.is_visible(timeout=2000):
            ok_btn.click(timeout=3000)
            page.wait_for_timeout(2000)
            print("    [debug] 已点击 okBtn 关闭弹窗")
            closed = True
    except:
        pass

    # 方法2: 按 ESC 键
    if not closed:
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            closed = True
        except:
            pass

    # 方法3: 点击页面空白处
    if not closed:
        try:
            page.click("body", timeout=3000)
            page.wait_for_timeout(1000)
            closed = True
        except:
            pass

    # 等待弹窗完全消失
    page.wait_for_timeout(2000)
    return closed


def read_prize_records(page):
    """读取中奖记录"""
    try:
        # 点击"我的中奖记录"按钮
        print("    点击'我的中奖记录'...")
        record_btn = page.locator("img[src*='zjjl']").first
        if not record_btn.is_visible(timeout=3000):
            print("    [x] 未找到中奖记录按钮")
            return

        record_btn.click(timeout=3000)
        page.wait_for_timeout(2000)
        print("    [v] 已打开中奖记录")

        # 读取中奖记录列表
        records = []

        # 直接读取所有 span1 和 time 元素
        span1_elems = page.locator(".span1").all()
        time_elems = page.locator(".time").all()

        # 只读取与 span1 数量相同的 time 元素（前面的是中奖记录，后面的是评论时间）
        for i, span1 in enumerate(span1_elems):
            try:
                prize_text = span1.inner_text(timeout=1000).strip()
                # 提取奖品名称（去掉"获得: "前缀）
                prize_name = prize_text.replace("获得: ", "")
                time_text = time_elems[i].inner_text(timeout=1000).strip() if i < len(time_elems) else ""
                records.append(f"{time_text}获得: {prize_name}")
            except:
                continue

        # 打印中奖记录
        if records:
            print("    中奖记录:")
            for record in records:
                print(f"      {record}")
        else:
            print("    暂无中奖记录")

        # 关闭弹窗
        close_win_prize(page)

    except Exception as e:
        print(f"    [x] 读取中奖记录异常: {e}")


def do_drawing(page, index: int, total: int) -> str:
    """执行一次抽奖，返回奖品名称"""
    try:
        print(f"    第 {index}/{total} 次抽奖...")

        # 先确保没有弹窗遮挡
        close_win_prize(page)

        # 点击抽奖指针
        pointer = page.locator("img[src*='pointerText']").first
        if not pointer.is_visible(timeout=3000):
            # 尝试其他选择器
            pointer = page.locator("img[style*='width: 60px']").first

        if pointer.is_visible(timeout=3000):
            pointer.click(timeout=3000)
            print("    已点击抽奖指针，等待结果...")
        else:
            print("  [x] 未找到抽奖指针")
            return "未知"

        # 等待结果弹窗出现 - 等待转盘停止后 <p data-v-e77f7682="">恭喜您获得：</p> 出现
        print("    等待转盘停止，弹窗出现...")
        prize_name = "未知奖品"

        # 方法1: 轮询检测（每100ms检查一次，最多15秒）
        print("    [debug] 开始轮询检测弹窗...")
        for check in range(150):  # 最多15秒
            page.wait_for_timeout(100)

            # 检查1: p[data-v-e77f7682]:has-text("恭喜您获得：")
            try:
                congrats_p = page.locator('p[data-v-e77f7682]:has-text("恭喜您获得：")').first
                if congrats_p.is_visible(timeout=100):
                    print("    [debug] 找到 '恭喜您获得：' 元素")
                    parent = congrats_p.locator("..")
                    prize_span = parent.locator('span[data-v-e77f7682]').first
                    if prize_span.is_visible(timeout=1000):
                        prize_name = prize_span.inner_text(timeout=1000).strip()
                        print(f"    [debug] 奖品名称: {prize_name}")
                        break
            except:
                pass

            # 检查2: winPrize 弹窗
            if prize_name == "未知奖品":
                try:
                    win_prize = page.locator(".winPrize").first
                    if win_prize.is_visible(timeout=100):
                        prize_text = win_prize.inner_text(timeout=1000)
                        if "恭喜您获得：" in prize_text:
                            lines = [line.strip() for line in prize_text.split("\n") if line.strip()]
                            for i, line in enumerate(lines):
                                if "恭喜您获得：" in line and i + 1 < len(lines):
                                    prize_name = lines[i + 1]
                                    break
                        break
                except:
                    pass

            # 检查3: text=恭喜您获得：
            if prize_name == "未知奖品":
                try:
                    congrats = page.locator("text=恭喜您获得：").first
                    if congrats.is_visible(timeout=100):
                        parent = congrats.locator("..")
                        parent_text = parent.inner_text(timeout=1000)
                        if "恭喜您获得：" in parent_text:
                            lines = [line.strip() for line in parent_text.split("\n") if line.strip()]
                            for i, line in enumerate(lines):
                                if "恭喜您获得：" in line and i + 1 < len(lines):
                                    prize_name = lines[i + 1]
                                    break
                        break
                except:
                    pass

        # 方法4: 如果还是没找到，尝试查找所有 span[data-v-e77f7682]
        if prize_name == "未知奖品":
            print("    [debug] 尝试查找 span 元素...")
            try:
                span_elems = page.locator("span[data-v-e77f7682]").all()
                for span in span_elems:
                    text = span.inner_text(timeout=1000).strip()
                    if text and text not in ["", "恭喜您获得："]:
                        if any(keyword in text for keyword in ["积分", "VIP", "会员", "福袋", "实体书", "谢谢参与"]):
                            prize_name = text
                            break
            except:
                pass

        # 方法5: 获取 body 全部文本
        if prize_name == "未知奖品":
            print("    [debug] 尝试获取body文本...")
            try:
                body_text = page.locator("body").inner_text(timeout=2000)
                if "恭喜您获得：" in body_text:
                    lines = [line.strip() for line in body_text.split("\n") if line.strip()]
                    for i, line in enumerate(lines):
                        if "恭喜您获得：" in line and i + 1 < len(lines):
                            next_line = lines[i + 1]
                            if next_line and next_line != "恭喜您获得：":
                                prize_name = next_line
                                break
            except Exception as e:
                print(f"    [debug] 获取页面文本异常: {e}")

        print(f"    [v] 抽奖结果: {prize_name}")

        # 关闭弹窗
        close_win_prize(page)

        return prize_name
    except Exception as e:
        print(f"    [x] 抽奖异常: {e}")
        return "未知"


def run_51_lottery(cookie_str: str, account_name: str):
    """单账号五一活动流程（浏览器自动化版）"""
    print(f"\n  === 开始五一狂欢抽奖活动 ===")

    # 提取用户信息
    user_info = extract_user_info_from_cookies(cookie_str)
    nickname = user_info.get("nickname") or user_info.get("username") or "未知"
    print(f"  用户: {nickname}")

    with sync_playwright() as p:
        browser, context = setup_browser_context(p, cookie_str)
        page = context.new_page()

        try:
            # 1. 访问活动页面并检查任务状态
            print("\n  [1] 访问活动页面，检查任务状态...")
            unfinished_tasks = get_task_status(page)

            if not unfinished_tasks:
                print("  [v] 所有任务已完成")
            else:
                print(f"  未完成任务索引: {unfinished_tasks}")

            # 2. 按顺序完成所有任务（如果已完成则跳过）
            print("\n  [2] 执行任务...")

            # 分享任务
            page.goto(f"{BASE_URL}/51-lottery/", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            share_btn = page.locator(".btn").filter(has_text="去完成").first
            if share_btn.is_visible(timeout=3000):
                do_share_task(page, 0)
                time.sleep(3)
            else:
                print("  [分享任务] 已完成或不可用")

            # 阅读任务
            page.goto(f"{BASE_URL}/51-lottery/", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            read_btn = page.locator(".btn").filter(has_text="去完成").first
            if read_btn.is_visible(timeout=3000):
                do_read_task(page, 0)
                time.sleep(3)
            else:
                print("  [阅读任务] 已完成或不可用")

            # 评论任务
            page.goto(f"{BASE_URL}/51-lottery/", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            comment_btn = page.locator(".btn").filter(has_text="去完成").first
            if comment_btn.is_visible(timeout=3000):
                do_comment_task(page, 0)
                time.sleep(3)
            else:
                print("  [评论任务] 已完成或不可用")

            # 3. 重新检查任务状态，等待服务器同步
            print("\n  [3] 等待服务器同步状态...")
            max_retries = 5
            draw_count = 0
            for retry in range(max_retries):
                page.goto(f"{BASE_URL}/51-lottery/", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)

                # 检查是否还有未完成任务
                unfinished = get_task_status(page)
                if unfinished:
                    print(f"  还有未完成任务: {unfinished}，等待同步...")
                    time.sleep(5)
                    continue

                # 获取抽奖次数
                count_elem = page.locator(".draw-count").first
                if count_elem.is_visible(timeout=5000):
                    text = count_elem.inner_text(timeout=2000)
                    match = re.search(r"\d+", text)
                    if match:
                        draw_count = int(match.group())
                        print(f"  当前抽奖次数: {draw_count}")
                        if draw_count > 0:
                            break
                        else:
                            print("  抽奖次数为0，继续等待...")

                time.sleep(5)

            if draw_count <= 0:
                print("  [!] 没有可用的抽奖次数，可能今日已抽完或需要等待")
                return True

            # 4. 执行抽奖
            print(f"\n  [4] 开始抽奖（共 {draw_count} 次）...")
            prizes = []
            for i in range(draw_count):
                prize = do_drawing(page, i + 1, draw_count)
                prizes.append(prize)
                if i < draw_count - 1:
                    time.sleep(2)

            # 5. 打印结果汇总
            print(f"\n  [v] 抽奖完成，共 {draw_count} 次")
            print("  获奖清单:")
            for idx, prize in enumerate(prizes, 1):
                print(f"    第 {idx} 次: {prize}")

            # 6. 读取中奖记录
            print(f"\n  [6] 读取中奖记录...")
            read_prize_records(page)

            print(f"\n  === 五一活动结束 ===")
            return True

        except Exception as e:
            print(f"  [x] 活动执行异常: {e}")
            return False
        finally:
            browser.close()


def main():
    """主函数"""
    print("=== 2026 五一狂欢抽奖活动自动化 ===\n")

    cookies_list = get_all_cookies()
    if not cookies_list:
        print("错误: 请设置 ZAIMANHUA_COOKIE 环境变量")
        return False

    all_success = True
    for index, (account_name, cookie_str) in enumerate(cookies_list):
        print(f"\n{'=' * 50}")
        print(f"账号: {account_name}")
        print("=" * 50)

        # 验证 Cookie 有效性，如果失效尝试自动登录
        # 使用对应的账号索引获取对应的多账号凭据
        from auto_login import get_valid_cookie
        valid_cookie, is_auto_login = get_valid_cookie(cookie_str, account_name, account_index=index if index > 0 else None)
        
        if not valid_cookie:
            print(f"  [ERROR] 无法获取有效Cookie")
            all_success = False
            continue
        
        if is_auto_login:
            print(f"  [v] 使用自动登录获取的新Cookie")
            cookie_str = valid_cookie
        else:
            print(f"  [v] 使用配置的Cookie")

        success = run_51_lottery(cookie_str, account_name)
        if not success:
            all_success = False

    return all_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
