from sourcelyzer.crypto import verify_hash
from sourcelyzer.crypto import gen_auth_token
from sourcelyzer.crypto import InvalidHash
from sourcelyzer.crypto import verify_auth_token
import cherrypy

class Command():
    pass

class LoginCommand(Command):
    
    def __init__(self, user):
        """Login Command

        Provides a simple system to establish a session with a
        client. Expects a user sqlalchemy orm object.

        Logging in performed by POSTing username / password. In return
        you get user id, username, and an auth token that must be sent
        with every future request.

        Throws a 401 if username or password is incorrect.
        """
        self.user = user

    @cherrypy.tools.json_out()
    @cherrypy.expose
    def default(self, username, password):
        if cherrypy.request.method != 'POST':
            cherrypy.response.headers['Allow'] = 'POST'
            raise cherrypy.HTTPError(405)

        db = cherrypy.request.db

        user = db.query(self.user).filter(self.user.username == username).first()

        if not user:
            raise cherrypy.HTTPError(401)

        try:
            verify_hash(user.password, password)
        except InvalidHash:
            raise cherrypy.HTTPError(401)

        token = gen_auth_token(user.username, user.password, user.id, cherrypy.session.id)

        cherrypy.session['user'] = {
            'id': user.id,
            'username': user.username,
            'token': token,
            'auth': True
        }

        return {
            'session': cherrypy.session.id,
            'token': token
        }


class SessionCommand(Command):
    def __init__(self, user):
        """Session Command

        Checks to see if session is valid.

        POST to this command with a session cookie and an auth token
        in the Authorization header to see if the session is valid
        and authenticted.

        Returns a 401 if there is no session id, no auth token, or
        any of these items are invalid
        """
        self.user = user

    @cherrypy.expose
    def default(self):
        if cherrypy.request.method != 'POST':
            cherrypy.response.headers['Allow'] = 'POST'
            raise cherrypy.HTTPError(405)
        if 'user' not in cherrypy.session:
            raise cherrypy.HTTPError(401, 'User not in session')

        if not cherrypy.session['user']['auth']:
            raise cherrypy.HTTPError(401, 'Session not authenticated')

        user = cherrypy.request.db.query(self.user).filter(self.user.username == cherrypy.session['user']['username']).first()

        if not user:
            raise cherrypy.HTTPError(401, 'Invalid User')

        verify_auth_token(cherrypy.request.headers['Authorization'], cherrypy.session['user']['username'], user.password, user.id, cherrypy.session.id)

        cherrypy.response.status = 204

