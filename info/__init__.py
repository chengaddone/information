import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from redis import StrictRedis

from config import config

# 初始化数据库
db = SQLAlchemy()
redis_store = None  # type: StrictRedis


def setup_log(config_name):
    """设置日志"""
    # 设置日志记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)  # 调试级别
    # 创建日志记录器，指明日志保存的路径、日志文件的大小和保存日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*10, backupCount=10)
    # 创建日志记录的格式、日志等级、输入日志信息的文件名、行数、日志信息
    formatter = logging.Formatter("%(levelname)s %(filename)s:%(lineno)d %(message)s")
    # 为创建的日志记录器设置记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    # 配置日志
    setup_log(config_name)
    # 创建flask对象
    app = Flask(__name__)
    # 加载配置
    app.config.from_object(config[config_name])
    # 数据库与app绑定
    db.init_app(app)
    # 初始化redis存储对象
    global redis_store
    redis_store = StrictRedis(host=config[config_name].REDIS_HOST,
                              port=config[config_name].REDIS_PORT,
                              decode_responses=True)
    # 开启当前项目的CSRF保护
    CSRFProtect(app)
    @app.after_request
    def after_request(response):
        """每次前端请求之后响应之前生成随机的CSRF值,并放在响应的cookie中，下次请求会将之带回"""
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response
    # 添加模板过滤器，方法是do_index_class，名称是indexClass
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, "indexClass")
    # 设置session
    Session(app)

    # 注册蓝图
    from info.modules.index import index_blue
    app.register_blueprint(index_blue)
    from info.modules.passport import passport_blue
    app.register_blueprint(passport_blue)
    from info.modules.news import news_blue
    app.register_blueprint(news_blue)

    return app
