from flask import session
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from info import create_app, db

app = create_app("development")
# 使用manager管理app
manager = Manager(app)
# 引入数据库迁移，关联app与db，并添加迁移命令
Migrate(app, db)
manager.add_command('db', MigrateCommand)


@app.route("/")
def index():
    session["name1"] = "wjc1"
    session["name"] = "wjc"
    return "hello"


if __name__ == '__main__':
    manager.run()
