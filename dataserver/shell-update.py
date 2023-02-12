from application import server
from application.routes import shell_update, shell_fetch, shell_autotrim, shell_cleanup

with server.app_context():
    shell_update()
    shell_fetch()
    shell_autotrim()
    shell_cleanup()
