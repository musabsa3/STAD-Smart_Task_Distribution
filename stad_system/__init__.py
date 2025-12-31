import pymysql

# Django 6 requires mysqlclient >= 2.2.1; tell it we're compatible
pymysql.__version__ = "2.2.7"
pymysql.version_info = (2, 2, 7, "final", 0)

pymysql.install_as_MySQLdb()
