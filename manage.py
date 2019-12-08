from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_session import Session

import redis

app = Flask(__name__)


class Config(object):
    """项目的配置"""
    DEBUG = True
    SECRET_KEY = "ADJKsad25*-dsof@$5098"
    # 配置mysql数据库
    SQLALCHEMY_DATABASE_URI = "mysql://root:940606@127.0.0.1:3306/information"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 配置redis数据库
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    # 配置session存储位置，存在redis中
    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    # 开启session签名
    SESSION_USER_SIGNER = True
    # 设置session需要过期，且过期时间为7天
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 86400*7


# 加载配置
app.config.from_object(Config)
# 初始化数据库
db = SQLAlchemy(app)
# 初始化redis存储对象
redis_store = redis.StrictRedis(host=app.config["REDIS_HOST"], port=app.config["REDIS_PORT"])
# 开启当前项目的CSRF保护
CSRFProtect(app)
# 设置session
Session(app)


@app.route("/")
def index():
    session["name1"] = "wjc1"
    session["name"] = "wjc"
    return "hello"


if __name__ == '__main__':
    app.run()
