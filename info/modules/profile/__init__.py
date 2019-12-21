# 与用户个人信息相关的模块
from flask import Blueprint

profile_blue = Blueprint("profile", __name__, url_prefix="/user")

from . import views

