from . import index_blu
from flask import render_template, current_app


@index_blu.route("/")
def index():
    """网站首页"""
    return render_template("news/index.html")


@index_blu.route('/favicon.ico')
def favicon():
    """加载网页图标"""
    # 使用send_static_file来加载静态文件
    return current_app.send_static_file("news/favicon.ico")
