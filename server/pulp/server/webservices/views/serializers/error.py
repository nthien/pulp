
"""
Pulp error serialization.
"""

import copy
import httplib

from pulp.server.webservices.http import request_method
from pulp.server.webservices.views.serializers import link


_ERROR_OBJ_SKEL = {
    '_href': None,
    'http_status': httplib.INTERNAL_SERVER_ERROR,
    'http_request_method': None,
    'error_message': None,
    'exception': None,
    'traceback': None,
}


def http_error_obj(http_status, msg=None):
    """
    Serialize an http error.
    @param http_status: valid http status number
    @type http_status: int
    @param msg: error message
    @type: str
    @return: serialized error
    @rtype: dict
    """
    error_obj = copy.copy(_ERROR_OBJ_SKEL)
    error_obj['http_request_method'] = request_method()
    error_obj['http_status'] = http_status
    error_obj['error_message'] = msg
    error_obj.update(link.current_link_obj())
    return error_obj
