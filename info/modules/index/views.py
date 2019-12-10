from . import index_blue
from flask import render_template, current_app


@index_blue.route("/")
def index():
    """网站首页"""
    return render_template("news/index.html")


@index_blue.route('/favicon.ico')
def favicon():
    """加载网页图标"""
    # 使用send_static_file来加载静态文件
    return current_app.send_static_file("news/favicon.ico")
