# 新闻详情的视图
from flask import render_template, current_app, g, abort, request, jsonify

from info import constants, db
from info.models import News, Comment
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blue


@news_blue.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    """
    新闻详情
    :return: json
    """
    user = g.user
    # 右侧新闻排行
    news_list = []
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    # 查询新闻数据
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        abort(404)
    # 更新新闻的点击次数
    news.clicks += 1
    # 收藏的逻辑
    is_collected = False
    if user:
        if news in user.collection_news:
            is_collected = True
    # 查询新闻的评论数据
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
    comment_dict_list = []
    for comment in comments:
        comment_dict = comment.to_dict()
        comment_dict_list.append(comment_dict)
    data = {
        "user": user.to_dict() if user else None,
        "news_dict_list": news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "comments": comment_dict_list
    }
    return render_template("news/detail.html", data=data)


@news_blue.route("/news_collect", methods=["POST"])
@user_login_data
def collect_news():
    """
    收藏新闻
    1.接收参数
    2.校验参数
    :return: json
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 1.接收参数
    json_data = request.json
    news_id = json_data.get("news_id")
    action = json_data.get("action")
    # 2.校验参数
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 3.查询到要收藏的新闻,看新闻是否存在
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")
    # 4.收藏与取消收藏
    if action == "cancel_collect":
        # 取消收藏
        if news in user.collection_news:
            user.collection_news.remove(news)
    else:
        # 收藏
        if news not in user.collection_news:
            user.collection_news.append(news)
    return jsonify(errno=RET.OK, errmsg="操作成功")


@news_blue.route("/news_comment", methods=["POST"])
@user_login_data
def comment_news():
    """
    新闻评论或者回复指定评论的视图
    :return: json
    """
    # 1.用户登录信息
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 2.获取数据
    json_data = request.json
    news_id = json_data.get("news_id")
    comment_content = json_data.get("comment_content")
    parent_id = json_data.get("parent_id")
    # 3.校验参数
    if not all([news_id, comment_content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="参数错误")
    # 查询到要评论的新闻,看新闻是否存在
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")
    # 4.初始化评论模型
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_content
    if parent_id:
        comment.parent_id = parent_id
    # 5.添加到数据库
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库写入错误")
    # 6.返回响应
    data = comment.to_dict()
    return jsonify(errno=RET.OK, errmsg="评论成功", data=data)