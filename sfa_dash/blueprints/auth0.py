from functools import partial


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack
from flask import url_for, redirect, current_app, session, Response
from flask.globals import LocalProxy, _lookup_app_object
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized
from jose import jwt, jwk
from six.moves.urllib.parse import urlencode


oauth_request_session = LocalProxy(partial(_lookup_app_object, 'auth0_oauth'))
current_user = LocalProxy(lambda: session.get('user', ''))


def make_auth0_blueprint(
        app,
        base_url,
        scope=None,
        storage=None):
    scope = scope or ['openid', 'email', 'profile', 'offline_access']
    auth0_bp = OAuth2ConsumerBlueprint(
        'auth0', __name__,
        base_url=base_url,
        token_url=f'{base_url}/oauth/token',
        auto_refresh_url=f'{base_url}/oauth/token',
        authorization_url=f'{base_url}/authorize',
        authorization_url_params={
            'audience': 'https://api.solarforecastarbiter.org'},
        redirect_to='.callback_handling',
        scope=scope,
        storage=storage,
    )
    auth0_bp.from_config['client_id'] = 'AUTH0_OAUTH_CLIENT_ID'
    auth0_bp.from_config['client_secret'] = 'AUTH0_OAUTH_CLIENT_SECRET'
    auth0_bp.from_config['jwt_key'] = 'AUTH0_OAUTH_JWT_KEY'

    @auth0_bp.before_app_request
    def set_applocal_session():
        ctx = stack.top
        ctx.auth0_oauth = auth0_bp.session  # this is a requests Session

    @oauth_authorized.connect_via(auth0_bp)
    def logged_in(blueprint, token):
        # must set the user first before getting or storing any tokens
        try:
            idtoken = jwt.decode(token['id_token'],
                                 key=blueprint.jwt_key,
                                 audience=blueprint.client_id)
        except (jwt.JWTError,
                jwk.JWKError,
                jwt.ExpiredSignatureError,
                jwt.JWTClaimsError,
                AttributeError):
            return Response('OAuth login failed', 401)
        # set session as permanent and expire after
        # not used for config[PERMANENT_SESSION_LIFETIME]
        session.permanent = True
        session['user'] = idtoken['sub'].split('|')[1]
        session['userinfo'] = {'name': idtoken['name']}

    @auth0_bp.route('/callback')
    def callback_handling():
        return redirect(session.get('redirect_path', url_for('index')))

    @app.route('/logout')
    def logout():
        del auth0_bp.token  # delete token
        session.clear()  # clear cookie
        params = {'returnTo': url_for('index',
                                      _external=True),
                  'client_id': current_app.config['AUTH0_OAUTH_CLIENT_ID']}
        return redirect(
            current_app.config['AUTH0_OAUTH_BASE_URL'] + '/v2/logout?'
            + urlencode(params))

    app.register_blueprint(auth0_bp, url_prefix='/login')
    return app
