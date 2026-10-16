"""
TradeWin — 独立桌面应用入口 (Windows/macOS)。

双击 tradewin.exe 或 python tradewin.py 启动：
  FastAPI 后端在后台线程运行 → WebView 窗口加载 trade_chat.html。
不依赖外部浏览器。
"""

import multiprocessing
import sys
import threading
import time
import urllib.request

import uvicorn


def main():
    # 1. Bootstrap（路径、版本检查、env 加载、skills 同步）
    from trade.bootstrap import setup
    setup()

    # 2. 创建 FastAPI app
    from trade.app import create_app, serve_trade_chat

    host = "127.0.0.1"
    port = 9119

    app = create_app()
    serve_trade_chat(app)

    # 3. 启动 uvicorn 在后台线程
    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": host, "port": port, "log_level": "warning"},
        daemon=True,
    )
    server_thread.start()

    # 4. 等待后端就绪
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/status", timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    else:
        print("Error: 后端启动超时")
        sys.exit(1)

    # 5. 打开 WebView 窗口
    import webview

    url = f"http://{host}:{port}/trade"
    webview.create_window(
        "Smart Trade AI",
        url,
        width=1280,
        height=900,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start()
    sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
