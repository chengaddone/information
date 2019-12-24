# 新闻详情的视图
from flask import render_template, current_app, g, abort, request, jsonify

from info import constants, db
from info.models import News, Comment, CommentLike
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
        is_comment_like = None
        try:
            is_comment_like = CommentLike.query.filter(CommentLike.user_id == user.id,
                                                       CommentLike.comment_id == comment.id).first()
        except Exception as e:
            # current_app.logger.error(e)
            pass
        comment_dict = comment.to_dict()
        if is_comment_like:
            comment_dict["is_like"] = True
        else:
            comment_dict["is_like"] = False
        comment_dict_list.append(comment_dict)
    # 是否有关注新闻作者
    is_followed = False
    # 当当前新闻有作者，而且当前登录用户已关注过这个用户，则设置为True
    if news.user and user:
        if news.user in user.followers:
            is_followed = True
    data = {
        "user": user.to_dict() if user else None,
        "news_dict_list": news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "comments": comment_dict_list,
        "si_followers": is_followed
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
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
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


@news_blue.route("/comment_like", methods=["POST"])
@user_login_data
def comment_like():
    """
    评论点赞
    :return: json
    """
    # 1.用户登录信息
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 2.获取数据
    json_data = request.json
    comment_id = json_data.get("comment_id")
    action = json_data.get("action")  # 前端请求的动作，点赞或者是取消点赞
    # 3.校验参数
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 4.找到需要点赞的评论模型
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论不存在")
    # 5.创建评论点赞的模型
    if action == "add":
        # 查询该评论是否已经被点赞
        comment_like_model = CommentLike.query.filter(CommentLike.user_id == user.id,
                                                      CommentLike.comment_id == comment_id).first()
        if not comment_like_model:
            # 点赞评论，生成点赞模型并存储进数据库
            comment_like_model = CommentLike()
            comment_like_model.user_id = user.id
            comment_like_model.comment_id = comment_id
            db.session.add(comment_like_model)
            comment.like_count += 1
    else:
        # 取消评论的点赞
        comment_like_model = CommentLike.query.filter(CommentLike.user_id == user.id,
                                                      CommentLike.comment_id == comment_id).first()
        if comment_like_model:
            db.session.delete(comment_like_model)
            comment.like_count -= 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库操作错误")
    return jsonify(errno=RET.OK, errmsg="操作成功")
