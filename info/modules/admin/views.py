# 管理模块的视图
import time
from datetime import datetime, timedelta

from flask import render_template, request, current_app, session, redirect, url_for, g, jsonify, abort

from info import constants, db
from info.models import User, News, Category
from info.modules.admin import admin_blue
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET


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


@admin_blue.route("/logout")
def logout():
    """管理页面的退出登录"""
    session.pop("user_id", None)
    session.pop("mobile", None)
    session.pop("nick_name", None)
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))


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
        paginate = User.query.filter(User.is_admin != 1).paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
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


@admin_blue.route("/review_list")
def review_list():
    """新闻审核的视图"""
    # 获取当前是第几页
    page = request.args.get("page", 1)
    # 获取当前页面的查询参数
    keywords = request.args.get("keywords", None)
    # 校验数据
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 获取未审核通过的新闻信息并分好页
    news_list = []
    news_list_dict = []
    current_page = 1
    total_page = 1

    filters = [News.status != 0]
    # 将搜索条件放入filters中
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters)\
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    for news in news_list:
        news_list_dict.append(news.to_review_dict())
    # 准备传输数据
    data = {
        "news_list": news_list_dict,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_review.html", data=data)


@admin_blue.route("/news_review_detail/<int:news_id>")
def news_review_detail(news_id):
    """新闻审核的视图"""
    # 通过新闻id查找
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return render_template("admin/news_review_detail.html", data={"errmsg": "未查询到此条新闻信息"})
    data = {
        "news": news.to_dict()
    }
    return render_template("admin/news_review_detail.html", data=data)


@admin_blue.route("/news_review_action", methods=["POST"])
def news_review_action():
    """新闻审核通过与否的视图"""
    # 1.接收参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    # 2.校验参数
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ("accept", "reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 3.查询到当前新闻
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到数据")
    # 4.审核新闻
    if action == "accept":
        # 审核通过
        news.status = 0
    else:
        # 拒绝审核
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="请输入拒绝原因")
        news.status = -1
        news.reason = reason
    return jsonify(errno=RET.OK, errmsg="OK")


@admin_blue.route("/news_edit")
def news_edit():
    """新闻编辑列表的视图"""
    # 获取当前是第几页
    page = request.args.get("page", 1)
    # 获取当前页面的查询参数
    keywords = request.args.get("keywords", None)
    # 校验数据
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 获取未审核通过的新闻信息并分好页
    news_list = []
    news_list_dict = []
    current_page = 1
    total_page = 1

    filters = [News.status == 0]
    # 将搜索条件放入filters中
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters)\
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    for news in news_list:
        news_list_dict.append(news.to_basic_dict())
    # 准备传输数据
    data = {
        "news_list": news_list_dict,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_edit.html", data=data)


@admin_blue.route("/news_edit_detail", methods=["GET", "POST"])
def news_edit_detail():
    """新闻编辑页面"""
    if request.method == "GET":
        # get请求，回显新闻数据
        # 1.获取到要编辑新闻的id
        news_id = request.args.get("news_id", None)
        # 2.校验新闻的id
        if not news_id:
            abort(404)
        try:
            news_id = int(news_id)
        except Exception as e:
            current_app.logger.error(e)
            abort(404)
        # 3.查询到需要编辑的新闻信息
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            abort(404)
        # 如果没有查询到或者查询出错，则抛出404页面
        if not news:
            abort(404)
        # 4.查询分类数据
        categories = []
        try:
            categories = Category.query.all()
            categories.pop(0)
        except Exception as e:
            current_app.logger.error(e)
            abort(404)
        category_dict_list = []
        for category in categories:
            category_dict_list.append(category.to_dict())
        data = {
            "news": news.to_dict(),
            "categories": category_dict_list,

        }
        return render_template("admin/news_edit_detail.html", data=data)
    # post请求，提交修改
    # 1.取到提交的数据
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 2.判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    # 3.查询要修改的新闻对象
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 4.修改图片
    if index_image:
        # 4.1读取图片信息
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

        # 4.2将标题图片上传到七牛
        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    # 5.设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id
    # 6.保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 7.返回结果
    return jsonify(errno=RET.OK, errmsg="编辑成功")


@admin_blue.route("/news_type", methods=["GET", "POST"])
def news_type():
    """管理新闻分类的视图"""
    if request.method == "GET":
        # 查询分类数据
        categories = []
        try:
            categories = Category.query.all()
            categories.pop(0)
        except Exception as e:
            current_app.logger.error(e)
            abort(404)
        category_dict_list = []
        for category in categories:
            category_dict_list.append(category.to_dict())
        data = {
            "categories": category_dict_list
        }
        return render_template("admin/news_type.html", data=data)
    # 新增或编辑分类
    # 1.取参数
    category_name = request.json.get("category_name")
    category_id = request.json.get("category_id")
    # 2.校验参数
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    if category_id:
        # 修改新闻类型
        try:
            category_id = int(category_id)
        except Exception as e:
            current_app.logger.error()
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        if not category:
            current_app.logger.error()
            return jsonify(errno=RET.NODATA, errmsg="没有查询到相关数据")
        category.name = category_name
        try:
            db.session.add(category)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库插入失败")
        return jsonify(errno=RET.OK, errmsg="编辑分类成功")
    else:
        # 新增新闻分类
        category = Category()
        category.name = category_name
        try:
            db.session.add(category)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库插入失败")
        return jsonify(errno=RET.OK, errmsg="添加分类成功")

