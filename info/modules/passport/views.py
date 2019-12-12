import random
import re

from info import redis_store, constants
from info.constants import IMAGE_CODE_REDIS_EXPIRES
from info.thirdlibs.yuntongxun.sms import CCP
from info.utils.response_code import RET

from . import passport_blue
from flask import request, abort, current_app, make_response, jsonify
from info.utils.captcha.captcha import captcha


@passport_blue.route("/image_code")
def get_image_code():
    """
    生成图片验证码的视图
    1.取到传入的参数
    2.判断参数是否有值
    3.生成图片验证码文字内容到redis
    4.返回验证码图片
    :return: image
    """
    # 1.取到传入的参数，前端访问的url为/image_code?imageCodeId=xxx
    image_code_id = request.args.get("imageCodeId", None)
    # 2.判断参数是否有值，如果没有值则主动抛出403异常
    if not image_code_id:
        return abort(403)
    # 3.生成图片验证码，并将文字内容到redis
    name, text, image = captcha.generate_captcha()
    try:
        redis_store.setex("ImageCodeId_"+image_code_id, IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        abort(500)
    # 4.将图片验证码返回
    response = make_response(image)
    # 设置返回头，使浏览器更智能的识别图片信息
    response.headers["Content-Type"] = "image/jpg"
    return response


@passport_blue.route("/sms_code", method=["POST"])
def send_sms_code():
    """
    发送短信验证码视图
    1.获取参数：手机号，图片验证码，图片验证码的编号
    2.校验参数：参数是否符合规则，判断是否有值
    3.校验图片验证码内容，校验不成功，返回验证码错误
    4.生成手机验证码，发送短信验证码
    5.告知发送结果
    :return: json
    """
    # 1.获取前端的参数，包括用户输入手机号，图片验证码和生成的图片验证码编号，数据以json的格式发送
    params_dic = request.json
    mobile = params_dic.get("mobile")
    image_code = params_dic.get("image_code")
    image_code_id = params_dic.get("image_code_id")
    # 2.校验参数是否都有值，以及校验手机号是否正确
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    if not re.match('1[35678]\\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式不正确")
    # 3.从redis中取出图片验证码的内容
    try:
        real_image_code = redis_store.get("ImageCodeId_"+image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg="图片验证码已过期")
    # 4.校验图片验证码
    if real_image_code.upper() != image_code.upper():
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")
    # 5.通过验证，生成短信验证码内容（随机数），将内容存入redis
    sms_code_str = "%06d" % random.randint(0, 999999)
    current_app.logger.debug("短信验证码内容：{}".format(sms_code_str))
    try:
        redis_store.set("SMS_"+mobile, sms_code_str, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(errno=RET.DBERR, errmsg="验证码生成保存失败")
    # 6.发送短信
    result = CCP().send_template_sms(mobile, [sms_code_str, constants.SMS_CODE_REDIS_EXPIRES/60], "1")
    if result != 0:
        return jsonify(errno=RET.THIRDERR, errmsg="第三方平台错误，短信发送失败")
    # 7.告知发送结果
    return jsonify(errno=RET.OK, errmsg="发送成功")
