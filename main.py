import sys
from PySide6.QtWidgets import QApplication
from src.mcp_host_app.core import Config
from src.mcp_host_app.gui import MainWindow


if __name__ == '__main__':
    config = Config()

    app = QApplication() # QApplication 图形应用的强制性控制核心，初始化底层资源，启动事件循环，驱动程序的响应，运行，退出
    main_window = MainWindow(config)
    main_window.show() # show() 将控件在屏幕上显示
    sys.exit(app.exec()) # exit() 终止程序运行 exec() 启动并管理应用程序的事件循环
