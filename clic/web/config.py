SQLALCHEMY_DATABASE_URI = "postgresql://clic-dickens:charles@localhost/db_annotation"
DEBUG = False
DEBUG_TB_INTERCEPT_REDIRECTS = False
# when testing = True, the login_required decorator is disabled.
TESTING = False
# FIXME not very secret here
SECRET_KEY = "qdfmkqjfmqksjfdmk"
MAIL_SERVER = 'smtp.qsdfqsdfqskjdfmlqsjdfmlkjjqsdf.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'username'
MAIL_PASSWORD = 'password'
# SECURITY_PASSWORD_HASH = "bcrypt"
# SECURITY_PASSWORD_SALT = "AasdsSDLKJFDasdflasdlfjhLJKHDlsdfjkhLKJ"
# https://pythonhosted.org/Flask-Security/models.html
SECURITY_POST_LOGIN_VIEW = "/annotation"
SECURITY_REGISTERABLE = True
SECURITY_REGISTER_URL = "/charlesdickens"
SECURITY_POST_REGISTER_VIEW = "/annotation"
SECURITY_TRACKABLE = False
SECURITY_RECOVERABLE = False
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CONFIRMABLE = False  # TODO
