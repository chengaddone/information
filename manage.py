from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from info import create_app, db, models
from info.models import User

app = create_app("development")
# 使用manager管理app
manager = Manager(app)
# 引入数据库迁移，关联app与db，并添加迁移命令
Migrate(app, db)
manager.add_command('db', MigrateCommand)


# 创建管理员账户的命令
@manager.option('-u', '-username', dest="username")
@manager.option('-p', '-password', dest="password")
def createsuperuser(username, password):
    if not all([username, password]):
        print("参数不足")
    user = User()
    user.nick_name = username
    user.mobile = username
    user.password = password
    user.is_admin = True

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(e)
    print("创建管理员成功")


if __name__ == '__main__':
    print(app.url_map)
    manager.run()
