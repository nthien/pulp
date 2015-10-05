import unittest

import mock

from pulp.client.commands.consumer import query as consumer_query
from pulp.client.commands.options import OPTION_CONSUMER_ID
from pulp.devel.unit import base


class InstantiationTests(unittest.TestCase):

    def setUp(self):
        self.mock_context = mock.MagicMock()

    def tearDown(self):
        self.mock_context = None

    def test_list(self):
        try:
            consumer_query.ConsumerListCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_search(self):
        try:
            consumer_query.ConsumerSearchCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_history(self):
        try:
            consumer_query.ConsumerHistoryCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))


class ListCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ListCommandTests, self).setUp()
        self.command = consumer_query.ConsumerListCommand(self.context)

    def test_structure(self):
        found_options = set(self.command.options)
        expected_options = set((consumer_query.OPTION_FIELDS, consumer_query.FLAG_BINDINGS,
                                consumer_query.FLAG_DETAILS))
        self.assertEqual(found_options, expected_options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'list')

    def test_list(self):
        self.server_mock.request.return_value = 200, []

        kwargs = {consumer_query.OPTION_FIELDS.keyword: None,
                  consumer_query.FLAG_BINDINGS.keyword: True,
                  consumer_query.FLAG_DETAILS.keyword: False}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'GET')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('bindings=True') > 0)
        self.assertTrue(url.find('details=False') > 0)

    def test_format_bindings(self):
        bindings = [
            {'repo_id': 'r1', 'deleted': False, 'consumer_actions': []},
            {'repo_id': 'r1', 'deleted': False, 'consumer_actions': []},
            {'repo_id': 'r2', 'deleted': False, 'consumer_actions': []},
            {'repo_id': 'r3', 'deleted': True, 'consumer_actions': []},
            {'repo_id': 'r4', 'deleted': False, 'consumer_actions': []},
            {'repo_id': 'r5', 'deleted': False, 'consumer_actions': ['1234']},
        ]
        consumer = {
            'bindings': bindings
        }

        # test
        self.command.format_bindings(consumer)

        # validation
        self.assertEqual(sorted(consumer['bindings']['confirmed']), ['r1', 'r2', 'r4'])
        self.assertEqual(sorted(consumer['bindings']['unconfirmed']), ['r3', 'r5'])

    def test_format_bindings_none(self):
        consumer = {
            'bindings': []
        }

        # test
        self.command.format_bindings(consumer)

        # validation
        self.assertEqual(sorted(consumer['bindings']), [])


class SearchCommandTests(base.PulpClientTests):

    def setUp(self):
        super(SearchCommandTests, self).setUp()
        self.command = consumer_query.ConsumerSearchCommand(self.context)

    def test_structure(self):
        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'search')

    def test_search(self):
        self.server_mock.request.return_value = 200, []

        kwargs = {}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'POST')


class HistoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(HistoryCommandTests, self).setUp()
        self.command = consumer_query.ConsumerHistoryCommand(self.context)

    def test_structure(self):
        found_options = set(self.command.options)
        expected_options = set((OPTION_CONSUMER_ID, consumer_query.OPTION_EVENT_TYPE,
                                consumer_query.OPTION_LIMIT, consumer_query.OPTION_SORT,
                                consumer_query.OPTION_START_DATE, consumer_query.OPTION_END_DATE))
        self.assertEqual(found_options, expected_options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'history')

    def test_history(self):
        self.server_mock.request.return_value = 200, []

        kwargs = {OPTION_CONSUMER_ID.keyword: 'test-consumer',
                  consumer_query.OPTION_EVENT_TYPE.keyword: None,
                  consumer_query.OPTION_LIMIT.keyword: '2',
                  consumer_query.OPTION_SORT.keyword: None,
                  consumer_query.OPTION_START_DATE.keyword: '2013-02-14',
                  consumer_query.OPTION_END_DATE.keyword: None}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'GET')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)
        self.assertTrue(url.find('event_type') < 0)
        self.assertTrue(url.find('limit=2') > 0)
        self.assertTrue(url.find('sort') < 0)
        self.assertTrue(url.find('start_date=2013-02-14') > 0)
        self.assertTrue(url.find('end_date') < 0)
