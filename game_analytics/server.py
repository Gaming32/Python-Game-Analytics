import argparse

import flask
from flask import Flask, request

module_name = 'game_analytics.server'
app = Flask(module_name)


def documentation_response(func):
    resp = flask.make_response()
    resp.status_code = 400
    if func.__doc__ is not None:
        resp.data = func.__doc__
        resp.content_type = 'text/markdown'
    return resp


@app.route('/push', methods=['GET', 'POST'])
def push():
    """
# Documentation for `/push`
    """
    if request.method == 'GET':
        return documentation_response(push)


class ServerConfig(dict):
    _slots_ = ['host', 'port', 'debug', 'flask_options']

    host: str = '::'
    port: int = 26259 # "ANALY" typed on a phone keypad
    debug: bool = False
    flask_options: dict = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for item in self.__class__._slots_:
            self.setdefault(item, getattr(self.__class__, item))

    def __setattr__(self, k, v):
        self[k] = v
        super().__setattr__(k, v)

    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(f'{self.__class__.__qualname__!r} object has no attribute {k!r}')


global_config: ServerConfig = ServerConfig()


def _fix_config(config: ServerConfig):
    if config.flask_options is None:
        config.flask_options = {}


def run_server(config: ServerConfig = global_config):
    _fix_config(config)
    global global_config
    global_config = config
    print(config)
    app.run(host=config.host, port=config.port, debug=config.debug, **config.flask_options)


def main():
    parser = argparse.ArgumentParser(f'python -m {module_name}')
    parser.add_argument('host', metavar='HOST', nargs='?', default=ServerConfig.host)
    parser.add_argument('-p', '--port', metavar='PORT', default=ServerConfig.port, type=int)
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()

    config = ServerConfig(host=args.host, port=args.port, debug=args.debug)
    run_server(config)


if __name__ == '__main__':
    main()
