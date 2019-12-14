from info import constants
from info.models import User, News
from info.utils.response_code import RET
from . import index_blue
from flask import render_template, current_app, session, request, jsonify


@index_blue.route("/")
def index():
    """
    显示网站首页
    1.如果用户已经登录，将登录信息传到模板中
    :return:
    """
    user_id = session.get("user_id", None)
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)

    # 右侧新闻排行
    news_list = []
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    news_dict_list = []
    # 将模型类转换为dict，准备传给前端
    for new in news_list:
        news_dict_list.append(new.to_basic_dict())
    data = {
        "user": user.to_dict() if user else None,
        "news_dict_list": news_dict_list
    }
    return render_template("news/index.html", data=data)


@index_blue.route('/favicon.ico')
def favicon():
    """加载网页图标"""
    # 使用send_static_file来加载静态文件
    return current_app.send_static_file("news/favicon.ico")


@index_blue.route("/news_list", methods=["GET"])
def new_list():
    """
    获取首页新闻列表
    :return:
    """
    # 1.获取参数
    # 新闻分类的id
    cid = request.args.get("cid", "1")
    page = request.args.get("page", "1")
    per_page = request.args.get("per_page", "10")
    # 2.校验参数
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 3.查询数据
    filters = []
    if cid != 1:
        filters.append(News.category_id == cid)
    # 查询并分好页
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据库查询错误")
    # 取到当前页的条目
    news = paginate.items
    # 获取总页数
    total_page = paginate.pages
    # 获取当前页
    current_page = paginate.page
    # 将新闻对象转为字典列表样式
    news_dict_list = []
    for new in news:
        news_dict_list.append(new.to_basic_dict())
    # 4.准备传输数据
    data = {
        "newsDictList": news_dict_list,
        "totalPage": total_page,
        "currentPage": current_page
    }
    # 5.返回响应
    return jsonify(errno=RET.OK, errmsg="ok", data=data)
