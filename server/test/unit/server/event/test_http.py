import httplib
import time

# needed to create unserializable ID
from bson.objectid import ObjectId as _test_objid
import mock

from ... import base
from pulp.server.compat import json
from pulp.server.event import http
from pulp.server.event.data import Event


@mock.patch('pulp.server.event.data.task_serializer')
class TestHTTPNotifierTests(base.PulpServerTests):

    @mock.patch('pulp.server.event.http._create_connection')
    def test_handle_event(self, mock_create, mock_task_ser):
        # Setup
        notifier_config = {
            'url': 'https://localhost/api/',
            'username': 'admin',
            'password': 'admin',
        }

        event = Event('type-1', {'k1': 'v1'})

        mock_connection = mock.Mock()
        mock_response = mock.Mock()
        mock_task_ser.return_value = None

        mock_response.status = httplib.OK

        mock_connection.getresponse.return_value = mock_response
        mock_create.return_value = mock_connection

        # Test
        http.handle_event(notifier_config, event)
        time.sleep(.5)  # handle works in a thread so give it a bit to finish

        # Verify
        self.assertEqual(1, mock_create.call_count)
        self.assertEqual(1, mock_connection.request.call_count)

        request_args = mock_connection.request.call_args[0]
        self.assertEqual('POST', request_args[0])
        self.assertEqual('/api/', request_args[1])

        expected_body = {'event_type': event.event_type,
                         'payload': event.payload,
                         'call_report': None}

        request_kwargs = mock_connection.request.call_args[1]
        parsed_body = json.loads(request_kwargs['body'])
        self.assertEqual(parsed_body, expected_body)

        headers = request_kwargs['headers']
        self.assertTrue('Authorization' in headers)

    @mock.patch('pulp.server.event.http._create_connection')
    def test_handle_event_with_error(self, mock_create, mock_task_ser):
        # Setup
        notifier_config = {'url': 'https://localhost/api/'}
        mock_task_ser.return_value = 'serialized data!'

        event = Event('type-1', {'k1': 'v1'})

        mock_connection = mock.Mock()
        mock_response = mock.Mock()

        mock_response.status = httplib.NOT_FOUND

        mock_connection.getresponse.return_value = mock_response
        mock_create.return_value = mock_connection

        # Test
        http.handle_event(notifier_config, event)  # should not error
        time.sleep(.5)

        # Verify
        self.assertEqual(1, mock_create.call_count)
        self.assertEqual(1, mock_connection.request.call_count)

    # test bz 1099945
    @mock.patch('pulp.server.event.http._create_connection')
    def test_handle_event_with_serialize_error(self, mock_create, mock_task_ser):
        # Setup
        notifier_config = {'url': 'https://localhost/api/'}
        mock_task_ser.return_value = 'serialized data!'

        event = Event('type-1', {'k1': 'v1', '_id': _test_objid()})

        mock_connection = mock.Mock()
        mock_response = mock.Mock()

        mock_response.status = httplib.NOT_FOUND

        mock_connection.getresponse.return_value = mock_response
        mock_create.return_value = mock_connection

        # Test
        http.handle_event(notifier_config, event)  # should not throw TypeError

    @mock.patch('pulp.server.event.http._create_connection')
    def test_handle_event_missing_url(self, mock_create, mock_task_ser):
        # Test
        mock_task_ser.return_value = 'serialized data!'
        http.handle_event({}, Event('type-1', {}))  # should not error

        # Verify
        self.assertEqual(0, mock_create.call_count)

    @mock.patch('pulp.server.event.http._create_connection')
    def test_handle_event_unparsable_url(self, mock_create, mock_task_ser):
        # Test
        mock_task_ser.return_value = 'serialized data!'
        http.handle_event({'url': '!@#$%'}, Event('type-1', {}))  # should not error

        # Verify
        self.assertEqual(0, mock_create.call_count)

    def test_create_configuration(self, mock_task_ser):
        # Test HTTPS
        conn = http._create_connection('https', 'foo')
        self.assertTrue(isinstance(conn, httplib.HTTPSConnection))

        # Test HTTP
        conn = http._create_connection('http', 'foo')
        self.assertTrue(isinstance(conn, httplib.HTTPConnection))
