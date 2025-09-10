import logging


def create_logger(
    logger_level=logging.DEBUG,
    is_use_console_handler=False,
    console_handler_level=logging.WARNING,
    is_use_file_handler=False,
    file_handler_level=logging.DEBUG,
    log_path=None,
):
    '''日志记录器'''
    logger_instance = logging.getLogger()  # getLogger() 获取日志记录器

    logger_instance.setLevel(logger_level)  # setLevel() 设置日志级别

    formatter = logging.Formatter(
        '%(asctime)s - %(lineno)d - %(levelname)s - %(message)s'
    )  # Formatter() 定义日志消息的格式

    if is_use_file_handler:
        file_handler = logging.FileHandler(log_path, encoding='utf-8')  # FileHandler() 将日志消息输出到文件中
        file_handler.setLevel(file_handler_level)
        file_handler.setFormatter(formatter)
        logger_instance.addHandler(file_handler)

    if is_use_console_handler:
        console_handler = logging.StreamHandler()  # StreamHandler() 将日志消息输出到流
        console_handler.setLevel(console_handler_level)
        console_handler.setFormatter(formatter)
        logger_instance.addHandler(console_handler)

    return logger_instance
