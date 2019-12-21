# 个人信息相关的视图
from . import profile_blue
from flask import render_template, g, redirect, request, jsonify

from info.utils.common import user_login_data
from ...utils.response_code import RET


@profile_blue.route("/info")
@user_login_data
def user_info():
    user = g.user
    if not user:
        # 没有登录重定向到首页
        return redirect("/")
    data = {
        "user": user.to_dict()
    }
    return render_template("news/user.html", data=data)


@profile_blue.route("/base_info", methods=["GET", "POST"])
@user_login_data
def base_info():
    """
    用户的基本信息
    :return: template
    """
    user = g.user
    if request.method == "GET":
        return render_template("news/user_base_info.html", data={"user": user.to_dict()})
    else:
        # 修改用户数据
        # 1.取到传入的参数
        json_data = request.json
        nick_name = json_data.get("nick_name")
        signature = json_data.get("signature")
        gender = json_data.get("gender")
        # 2.校验参数
        if not all([nick_name, gender, signature]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        if gender not in ["MAN", "WOMAN"]:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        # 3.给用户信息设置值
        user.signature = signature
        user.nick_name = nick_name
        user.gender = gender
        # 4.添加到数据库，因为已经设置过默认提交，所以可以不用手动提交

        return jsonify(errno=RET.OK, errmsg="OK")


@profile_blue.route("/pic_info", methods=["GET", "POST"])
@user_login_data
def pic_info():
    """
    图片上传与现显示的视图
    """
    user = g.user
    if request.method == "GET":
        return render_template("news/user_pic_info.html", data={"user": user.to_dict()})
