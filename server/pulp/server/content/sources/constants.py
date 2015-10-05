from pulp.common.config import parse_bool


URL = 'url'

ENABLED = 'enabled'
NAME = 'name'
TYPE = 'type'
BASE_URL = 'base_url'
PATHS = 'paths'
PRIORITY = 'priority'
EXPIRES = 'expires'

MAX_CONCURRENT = 'max_concurrent'
MAX_SPEED = 'max_speed'
SSL_VALIDATION = 'ssl_validation'
SSL_CA_CERT = 'ssl_ca_cert'
SSL_CLIENT_KEY = 'ssl_client_key'
SSL_CLIENT_CERT = 'ssl_client_cert'
PROXY_URL = 'proxy_url'
PROXY_PORT = 'proxy_port'
PROXY_USERID = 'proxy_username'
PROXY_PASSWORD = 'proxy_password'
BASIC_AUTH_USERID = 'basic_auth_username'
BASIC_AUTH_PASSWORD = 'basic_auth_password'
HEADERS = 'headers'

# format: <property>, <nectar-property>, <conversion-function>
NECTAR_PROPERTIES = (
    (MAX_CONCURRENT, 'max_concurrent', int),
    (MAX_SPEED, 'max_speed', int),
    (SSL_VALIDATION, 'ssl_validation', parse_bool),
    (SSL_CA_CERT, 'ssl_ca_cert_path', str),
    (SSL_CLIENT_KEY, 'ssl_client_key_path', str),
    (SSL_CLIENT_CERT, 'ssl_client_cert_path', str),
    (PROXY_URL, 'proxy_url', str),
    (PROXY_PORT, 'proxy_port', int),
    (PROXY_USERID, 'proxy_username', str),
    (PROXY_PASSWORD, 'proxy_password', str),
    (BASIC_AUTH_USERID, 'basic_auth_username', str),
    (BASIC_AUTH_PASSWORD, 'basic_auth_password', str),
    (HEADERS, 'headers', str),
)

SOURCE_ID = 'source_id'
TYPE_ID = 'type_id'
UNIT_KEY = 'unit_key'
DESTINATION = 'destination'
