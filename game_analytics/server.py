import argparse
import json
import os
import numbers
import secrets

from game_analytics.semidbm_shelve import open as sopen

import flask
from flask import Flask, jsonify, request

module_name = 'game_analytics.server'
app = Flask(module_name)


config_data_types = {
    'string': str,
    'number': numbers.Number,
    'boolean': bool,
    'null': type(None),
    'object': dict,
    'array': list,

    'any': object,

    'int': int,
    'float': float,
}


def documentation_response(func, message=None, status=400):
    resp = flask.make_response()
    resp.status_code = status
    doc = ''
    if message is not None:
        doc += f'\n<span style="color:darkred">{message}</span>\n\n\n'
    if func.__doc__ is not None:
        doc += func.__doc__
        doc += '\n'
    resp.data = doc
    resp.content_type = 'text/markdown'
    return resp


def push_profile(user_id: str, data: dict):
    profile = app.config['db']['users'].get(user_id)
    if profile is None:
        return documentation_response(push, f'User id `{user_id}` does not exist', 404)
    field = data.get('field')
    if field is None:
        return documentation_response(push, '`field` key must be included for `profile` endpoint')
    value = data.get('value')
    if value is None:
        return documentation_response(push, '`value` key must be included for `profile` endpoint')
    if not verify_profile_field(field, value):
        return documentation_response(push, f'invalid type for field `{field}` in `profile` endpoint`')
    profile[field] = value
    app.config['db']['users'][user_id] = profile


push_endpoints = {
    'profile': push_profile
}


@app.route('/push', methods=['GET', 'POST'])
def push():
    """
# Documentation for `/push`

This URL should be POSTed to with a JSON object.
This object should contain a key called "endpoint" defining where the data should be stored.
    """
    if request.method == 'GET':
        return documentation_response(push)

    if request.json is None:
        return documentation_response(push, 'Content-Type must be application/json')
    user_id = request.json.get('id')
    if not isinstance(user_id, str):
        return documentation_response(push, f'User id required. (`id` key)')
    endpoint = request.json.get('endpoint', 'profile')
    func = push_endpoints.get(endpoint, None)
    if func is None:
        return documentation_response(push, f'Invalid endpoint: {endpoint}')
    result = func(user_id, request.json)
    if result is None:
        return '', 204
    return result


def pull_profile(user_id: str, data: dict):
    profile = app.config['db']['users'].get(user_id)
    if profile is None:
        return documentation_response(pull, f'User id `{user_id}` does not exist', 404)
    return profile


pull_endpoints = {
    'profile': pull_profile
}


@app.route('/pull', methods=['GET', 'POST'])
def pull():
    """
# Documentation for `/pull`

This URL should be POSTed to with a JSON object.
This object should contain a key called "endpoint" defining where the data should be stored.
    """
    if request.method == 'GET':
        return documentation_response(pull)

    if request.json is None:
        return documentation_response(pull, 'Content-Type must be application/json')
    user_id = request.json.get('id')
    if not isinstance(user_id, str):
        return documentation_response(pull, f'User id required. (`id` key)')
    endpoint = request.json.get('endpoint', 'profile')
    func = pull_endpoints.get(endpoint, None)
    if func is None:
        return documentation_response(pull, f'Invalid endpoint: {endpoint}')
    result = func(user_id, request.json)
    if result is None:
        return '', 204
    return result


def verify_profile_field(field_name, value):
    field_types = app.config['config'].analytics_config['profiles']['fields']
    if field_name not in field_types:
        return False
    if not isinstance(value, config_data_types[field_types[field_name]]):
        return False
    return True


def verify_profile(profile: dict):
    field_names = app.config['config'].analytics_config['profiles']['fields']
    return all(f in profile for f in field_names) \
       and all(verify_profile_field(*f) for f in profile.items())


@app.route('/new-profile', methods=['GET', 'POST'])
def new_profile():
    if request.method == 'GET':
        return documentation_response(new_profile)

    if request.json is None:
        return documentation_response(new_profile, 'Content-Type must be application/json')
    if not verify_profile(request.json):
        field_names = app.config['config'].analytics_config['profiles']['fields']
        required_fields = "\n\nRequired fields:{}\n".format(''.join(f'\n  + {f}: {t}' for (f, t) in field_names.items()))
        return documentation_response(new_profile, f'Profile contains invalid fields or some fields are missing{required_fields}')
    created_profile = dict(request.json)
    user_id = secrets.token_urlsafe()
    app.config['db']['users'][user_id] = created_profile
    response = dict(created_profile)
    response['id'] = user_id
    return jsonify(response), 201


@app.route('/brew-coffee')
def brew_coffee():
    return "Game analytics servers don't make coffee, sorry.", 418


class ServerConfig(dict):
    host: str = '::'
    port: int = 26259 # "ANALY" typed on a phone keypad
    debug: bool = False
    flask_options: dict = None
    root: str = ''
    analytics_config: dict = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for item in self.__class__.__annotations__:
            if item not in self:
                value = getattr(self.__class__, item)
            else:
                value = self[item]
            setattr(self, item, value)

    def __setattr__(self, k, v):
        self[k] = v
        super().__setattr__(k, v)

    def __getattr__(self, k):
        if k in self:
            return self[k]
        elif hasattr(ServerConfig, k):
            return getattr(ServerConfig, k)
        raise AttributeError(f'{self.__class__.__qualname__!r} object has no attribute {k!r}')

    def get_file_path(self, path):
        return os.path.join(self.root, path)


global_config: ServerConfig = ServerConfig()


def _fix_config(config: ServerConfig):
    if config.flask_options is None:
        config.flask_options = {}
    if config.analytics_config is None:
        config.analytics_config = {}


def run_server(config: ServerConfig = None):
    if config is None:
        config = ServerConfig()
    _fix_config(config)
    app.config['config'] = config
    app.config['db'] = {}
    app.config['db']['users'] = sopen(config.get_file_path('userdb'))
    app.run(host=config.host, port=config.port, debug=config.debug, **config.flask_options)


def main():
    parser = argparse.ArgumentParser(f'python -m {module_name}')
    parser.add_argument('config', metavar='CONFIG_FILE', type=argparse.FileType('r'))
    parser.add_argument('host', metavar='HOST', nargs='?', default=ServerConfig.host)
    parser.add_argument('-p', '--port', metavar='PORT', default=ServerConfig.port, type=int)
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()

    with args.config:
        config_data = json.load(args.config)
    root = os.path.dirname(args.config.name)
    root = os.path.join(root, config_data.get('root', ''))
    config = ServerConfig(host=args.host, port=args.port, debug=args.debug, root=root, analytics_config=config_data)
    run_server(config)


if __name__ == '__main__':
    main()
