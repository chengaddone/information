# 管理模块的视图
import time
from datetime import datetime, timedelta

from flask import render_template, request, current_app, session, redirect, url_for, g

from info import constants
from info.models import User
from info.modules.admin import admin_blue
from info.utils.common import user_login_data


@admin_blue.route("/login", methods=["GET", "POST"])
def login():
    """管理端页面登录"""
    if request.method == "GET":
        # 获取登录页面
        # 判断当前是否有登录信息，如果有，直接重定向到index页面
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        if user_id and is_admin:
            return redirect(url_for("admin.index"))
        return render_template("admin/login.html")
    # 登录操作
    # 1.获取登录参数
    username = request.form.get("username")
    password = request.form.get("password")
    # 2.校验参数
    if not all([username, password]):
        return render_template("admin/login.html", errmsg="用户名密码不能为空")
    # 3.查询当前用户
    try:
        user = User.query.filter(User.mobile == username, User.is_admin == 1).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="无效的用户名")
    if not user:
        return render_template("admin/login.html", errmsg="无效的用户名")
    # 4.校验密码
    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="用户名密码错误")
    # 5.密码校验通过，将信息保存到session中
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    session["is_admin"] = True

    return redirect(url_for("admin.index"))


@admin_blue.route("/index")
@user_login_data
def index():
    user = g.user
    data = {
        "user": user.to_dict()
    }
    return render_template("admin/index.html", data=data)


@admin_blue.route("/user_count")
def user_count():
    """管理端的用户数据展示视图"""
    # 总人数
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin != 1).count()
    except Exception as e:
        current_app.logger.error(e)
    # 月新增用户
    mon_count = 0
    t = time.localtime()
    begin_mon_date = datetime.strptime(('%d-%02d-01' % (t.tm_year, t.tm_mon)), "%Y-%m-%d")
    try:
        mon_count = User.query.filter(User.is_admin != 1, User.create_time >= begin_mon_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 日新增用户
    day_count = 0
    begin_day_date = datetime.strptime(('%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)), "%Y-%m-%d")
    try:
        day_count = User.query.filter(User.is_admin != 1, User.create_time >= begin_day_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 折线图数据
    active_time = []
    active_count = []
    # 取到当前这一天的开始时间数据
    today_date = datetime.strptime(('%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)), "%Y-%m-%d")  # 今天的00:00:00
    # 循环取今天以前一个月每一天活跃的用户数量
    for i in range(0, 31):
        begin_date = today_date - timedelta(days=i)
        end_date = begin_date + timedelta(days=1)
        count = User.query.filter(User.is_admin != 1, User.last_login >= begin_date, User.last_login < end_date).count()
        active_count.append(count)
        active_time.append(begin_date.strftime('%Y-%m-%d'))
    # 反转数组，让最近的一天显示在最右边
    active_time.reverse()
    active_count.reverse()
    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_time": active_time,
        "active_count": active_count
    }

    return render_template("admin/user_count.html", data=data)


@admin_blue.route("/user_list")
def user_list():
    """
    用户管理页面视图
    """
    # 获取当前是第几页
    page = request.args.get("page", 1)
    # 校验数据
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 获取用户列表信息并分好页
    users = []
    user_list_dict = []
    current_page = 1
    total_page = 1
    try:
        paginate = User.query.filter(User.is_admin != 1).paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT)
        users = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    for user in users:
        user_list_dict.append(user.to_admin_dict())
    # 准备传输数据
    data = {
        "users": user_list_dict,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/user_list.html", data=data)
