from mock import patch, Mock, call

from pulp.agent.lib.report import ContentReport
from pulp.common.constants import PRIMARY_ID
from pulp.server.content.sources.model import DownloadReport, DownloadDetails

from base import ClientTests, Response
from pulp_node.extensions.admin.commands import *
from pulp_node.extensions.admin.rendering import ProgressTracker
from pulp_node.error import *
from pulp_node.reports import RepositoryReport
from pulp_node.handlers.reports import SummaryReport


NODE_ID = 'test.redhat.com'
REPOSITORY_ID = 'test_repository'
MAX_BANDWIDTH = 12345
MAX_CONCURRENCY = 54321

REPO_ENABLED_CHECK = 'pulp_node.extensions.admin.commands.repository_enabled'
NODE_ACTIVATED_CHECK = 'pulp_node.extensions.admin.commands.node_activated'

CONSUMER_LIST_API = 'pulp.bindings.consumer.ConsumerAPI.consumers'
NODE_ACTIVATE_API = 'pulp.bindings.consumer.ConsumerAPI.update'
NODE_UPDATE_API = 'pulp.bindings.consumer.ConsumerContentAPI.update'
REPO_LIST_API = 'pulp.bindings.repository.RepositoryAPI.repositories'
DISTRIBUTORS_API = 'pulp.bindings.repository.RepositoryDistributorAPI.distributors'
PUBLISH_API = 'pulp.bindings.repository.RepositoryActionsAPI.publish'
REPO_ENABLE_API = 'pulp.bindings.repository.RepositoryDistributorAPI.create'
REPO_DISABLE_API = 'pulp.bindings.repository.RepositoryDistributorAPI.delete'
BIND_API = 'pulp.bindings.consumer.BindingsAPI.bind'
UNBIND_API = 'pulp.bindings.consumer.BindingsAPI.unbind'
POLLING_API = 'pulp.client.commands.polling.PollingCommand.poll'



CONSUMERS_ONLY = [
    {'notes': {}}
]

CONSUMERS_AND_NODES = [
    {'notes': {}},
    {'notes': {constants.NODE_NOTE_KEY: True}}
]

NODES_WITH_BINDINGS = [
    {
        'notes': {constants.NODE_NOTE_KEY: True},
        'bindings': [
            {
                'repo_id': 'r1',
                'type_id': constants.HTTP_DISTRIBUTOR,
                'binding_config': {constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY}
            }
        ]
    },
    {
        'notes': {constants.NODE_NOTE_KEY: True},
        'bindings': [
            {
                'repo_id': 'r2',
                'type_id': constants.HTTP_DISTRIBUTOR,
                'binding_config': {constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY},
            },
            {
                'repo_id': 'r3',
                'type_id': 'other',
                'binding_config': {},  # not node binding
            },
            {
                'repo_id': 'r4',
                'type_id': 'other',
                'binding_config': {},  # not node binding

            },
        ]
    },
]

ALL_REPOSITORIES = [{'id': REPOSITORY_ID}, ]

NON_NODES_DISTRIBUTORS_ONLY = [
    {'id': 1, 'distributor_type_id': 1},
    {'id': 2, 'distributor_type_id': 2},
]

MIXED_DISTRIBUTORS = [
    {'id': 1, 'distributor_type_id': 1},
    {'id': 2, 'distributor_type_id': 2},
    {'id': 3, 'distributor_type_id': constants.HTTP_DISTRIBUTOR},
    {'id': 4, 'distributor_type_id': constants.HTTP_DISTRIBUTOR},
]

UPDATE_REPORT = {
    'succeeded': True,
    'details': {
        'errors':[],
        'repositories': [
            RepositoryReport('repo_1', RepositoryReport.ADDED)
        ]
    }
}


class TestListCommands(ClientTests):

    @patch(CONSUMER_LIST_API, return_value=Response(200, CONSUMERS_ONLY))
    def test_list_nodes_no_nodes(self, mock_binding):
        # Test
        command = NodeListCommand(self.context)
        command.run(fields=None)
        # Verify
        mock_binding.assert_called_with(bindings=False, details=False)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 4)
        self.assertTrue('Child Nodes' in lines[1])

    @patch(CONSUMER_LIST_API, return_value=Response(200, CONSUMERS_AND_NODES))
    def test_list_nodes(self, mock_binding):
        # Test
        command = NodeListCommand(self.context)
        command.run(fields=None)
        # Verify
        mock_binding.assert_called_with(bindings=False, details=False)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 9)
        self.assertTrue(NODE_LIST_TITLE in lines[1])

    @patch(CONSUMER_LIST_API, return_value=Response(200, NODES_WITH_BINDINGS))
    def test_list_nodes_with_bindings(self, mock_binding):
        # Test
        command = NodeListCommand(self.context)
        command.run(fields=None)
        # Verify
        mock_binding.assert_called_with(bindings=False, details=False)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 16)
        self.assertTrue(NODE_LIST_TITLE in lines[1])

    @patch(REPO_LIST_API, return_value=Response(200, ALL_REPOSITORIES))
    @patch(DISTRIBUTORS_API, return_value=Response(200, NON_NODES_DISTRIBUTORS_ONLY))
    def test_list_repos_disabled_only(self, mock_binding, *unused):
        # Test
        command = NodeListRepositoriesCommand(self.context)
        command.run(details=True, summary=False)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 4)
        self.assertTrue(REPO_LIST_TITLE in lines[1])

    @patch(REPO_LIST_API, return_value=Response(200, ALL_REPOSITORIES))
    @patch(DISTRIBUTORS_API, return_value=Response(200, MIXED_DISTRIBUTORS))
    def test_list_repos_with_enabled(self, mock_binding, *unused):
        # Test
        command = NodeListRepositoriesCommand(self.context)
        command.run(details=True, summary=False)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 9)
        self.assertTrue(REPO_LIST_TITLE in lines[1])


class TestPublishCommand(ClientTests):

    @patch(REPO_ENABLED_CHECK, return_value=True)
    @patch('pulp.client.commands.polling.PollingCommand.rejected')
    @patch('pulp.client.commands.polling.PollingCommand.poll')
    @patch(PUBLISH_API, return_value=Response(200, {}))
    def test_publish(self, mock_binding, *unused):
        # Test
        command = NodeRepoPublishCommand(self.context)
        keywords = {OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        mock_binding.assert_called_with(REPOSITORY_ID, constants.HTTP_DISTRIBUTOR, {})


    @patch(REPO_ENABLED_CHECK, return_value=False)
    @patch('pulp.client.commands.polling.PollingCommand.rejected')
    @patch('pulp.client.commands.polling.PollingCommand.poll')
    @patch(PUBLISH_API, return_value=Response(200, {}))
    def test_publish_not_enabled(self, mock_binding, *unused):
        # Test
        command = NodeRepoPublishCommand(self.context)
        keywords = {OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertFalse(mock_binding.called)


class TestActivationCommands(ClientTests):

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_activate(self, mock_binding, *unused):
        # Test
        command = NodeActivateCommand(self.context)
        keywords = {
            OPTION_CONSUMER_ID.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY
        }
        command.run(**keywords)
        # Verify
        delta = {
            'notes': {
                constants.NODE_NOTE_KEY: True,
                constants.STRATEGY_NOTE_KEY: constants.DEFAULT_STRATEGY
            }
        }
        self.assertTrue(OPTION_CONSUMER_ID in command.options)
        mock_binding.assert_called_with(NODE_ID, delta)

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_activate_already_activated(self, mock_binding, *unused):
        # Setup
        command = NodeActivateCommand(self.context)
        keywords = {
            OPTION_CONSUMER_ID.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY
        }
        command.run(**keywords)
        # Verify
        self.assertFalse(mock_binding.called)

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate(self, mock_binding, mock_activated):
        # Test
        command = NodeDeactivateCommand(self.context)
        keywords = {NODE_ID_OPTION.keyword: NODE_ID}
        command.run(**keywords)
        # Verify
        delta = {'notes': {constants.NODE_NOTE_KEY: None, constants.STRATEGY_NOTE_KEY: None}}
        self.assertTrue(NODE_ID_OPTION in command.options)
        mock_activated.assert_called_with(self.context, NODE_ID)
        mock_binding.assert_called_with(NODE_ID, delta)

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate_not_activated(self, mock_binding, mock_activated):
        # Test
        command = NodeDeactivateCommand(self.context)
        keywords = {NODE_ID_OPTION.keyword: NODE_ID}
        command.run(**keywords)
        # Verify
        self.assertTrue(NODE_ID_OPTION in command.options)
        mock_activated.assert_called_with(self.context, NODE_ID)
        self.assertFalse(mock_binding.called)


class TestEnableCommands(ClientTests):

    @patch(REPO_ENABLED_CHECK, return_value=False)
    @patch(REPO_ENABLE_API, return_value=(200, {}))
    def test_enable(self, mock_binding, *unused):
        # Test
        command = NodeRepoEnableCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            AUTO_PUBLISH_OPTION.keyword: 'true',
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(AUTO_PUBLISH_OPTION in command.options)
        mock_binding.assert_called_with(REPOSITORY_ID,  constants.HTTP_DISTRIBUTOR, {},
                                        True, constants.HTTP_DISTRIBUTOR)

    @patch(REPO_ENABLED_CHECK, return_value=False)
    @patch(REPO_ENABLE_API, return_value=(200, {}))
    def test_enable_no_auto_publish(self, mock_binding, *unused):
        # Test
        command = NodeRepoEnableCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            AUTO_PUBLISH_OPTION.keyword: 'false',
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(AUTO_PUBLISH_OPTION in command.options)
        mock_binding.assert_called_with(REPOSITORY_ID,  constants.HTTP_DISTRIBUTOR, {},
                                        False, constants.HTTP_DISTRIBUTOR)

    @patch(REPO_ENABLED_CHECK, return_value=True)
    @patch(REPO_ENABLE_API, return_value=(200, {}))
    def test_enable(self, mock_binding, *unused):
        # Test
        command = NodeRepoEnableCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            AUTO_PUBLISH_OPTION.keyword: 'true',
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(AUTO_PUBLISH_OPTION in command.options)
        self.assertFalse(mock_binding.called)

    @patch(REPO_ENABLED_CHECK, return_value=True)
    @patch(REPO_DISABLE_API, return_value=(200, {}))
    def test_disable(self, mock_binding, *unused):
        # Test
        command = NodeRepoDisableCommand(self.context)
        keywords = {OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        mock_binding.assert_called_with(REPOSITORY_ID,  constants.HTTP_DISTRIBUTOR)


class TestBindCommands(ClientTests):

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertTrue(STRATEGY_OPTION in command.options)
        mock_binding.assert_called_with(
            NODE_ID,
            REPOSITORY_ID,
            constants.HTTP_DISTRIBUTOR,
            notify_agent=False,
            binding_config={constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY})

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind_with_strategy(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertTrue(STRATEGY_OPTION in command.options)
        mock_binding.assert_called_with(
            NODE_ID,
            REPOSITORY_ID,
            constants.HTTP_DISTRIBUTOR,
            notify_agent=False,
            binding_config={constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY})

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind_not_activated(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertTrue(STRATEGY_OPTION in command.options)
        self.assertFalse(mock_binding.called)

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(UNBIND_API, return_value=Response(200, {}))
    def test_unbind(self, mock_binding, *unused):
        # Test
        command = NodeUnbindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(NODE_ID_OPTION in command.options)
        mock_binding.assert_called_with(NODE_ID, REPOSITORY_ID, constants.HTTP_DISTRIBUTOR)


class TestUpdateCommands(ClientTests):

    @patch(POLLING_API)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(NODE_UPDATE_API, return_value=Response(202, {}))
    def test_update(self, mock_update, mock_activated, *unused):
        # Test
        command = NodeUpdateCommand(self.context)
        keywords = {
            NODE_ID_OPTION.keyword: NODE_ID,
            MAX_BANDWIDTH_OPTION.keyword: MAX_BANDWIDTH,
            MAX_CONCURRENCY_OPTION.keyword: MAX_CONCURRENCY
        }
        command.run(**keywords)
        # Verify
        units = [dict(type_id='node', unit_key=None)]
        options = {
            constants.MAX_DOWNLOAD_BANDWIDTH_KEYWORD: MAX_BANDWIDTH,
            constants.MAX_DOWNLOAD_CONCURRENCY_KEYWORD: MAX_CONCURRENCY,
        }
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertTrue(MAX_BANDWIDTH_OPTION in command.options)
        self.assertTrue(MAX_CONCURRENCY_OPTION in command.options)
        mock_update.assert_called_with(NODE_ID, units=units, options=options)
        mock_activated.assert_called_with(self.context, NODE_ID)


class TestRenderers(ClientTests):

    def test_update_rendering(self):
        repo_ids = ['repo_%d' % n for n in range(0, 3)]
        handler_report = ContentReport()
        summary_report = SummaryReport()
        summary_report.setup([{'repo_id': r} for r in repo_ids])
        for r in summary_report.repository.values():
            r.action = RepositoryReport.ADDED
            download_report = DownloadReport()
            download_report.downloads[PRIMARY_ID] = DownloadDetails()
            download_report.downloads['content-world'] = DownloadDetails()
            r.sources = download_report.dict()
        handler_report.set_succeeded(details=summary_report.dict())
        renderer = UpdateRenderer(self.context.prompt, handler_report.dict())
        renderer.render()
        self.assertEqual(len(self.recorder.lines), 59)

    def test_update_rendering_with_errors(self):
        repo_ids = ['repo_%d' % n for n in range(0, 3)]
        handler_report = ContentReport()
        summary_report = SummaryReport()
        summary_report.setup([{'repo_id': r} for r in repo_ids])
        for r in summary_report.repository.values():
            r.action = RepositoryReport.ADDED
        summary_report.errors.append(
            UnitDownloadError('http://abc/x.rpm', repo_ids[0], dict(response_code=401)))
        handler_report.set_failed(details=summary_report.dict())
        renderer = UpdateRenderer(self.context.prompt, handler_report.dict())
        renderer.render()
        self.assertEqual(len(self.recorder.lines), 48)

    def test_update_rendering_with_message(self):
        handler_report = ContentReport()
        handler_report.set_failed(details=dict(message='Authorization Failed'))
        renderer = UpdateRenderer(self.context.prompt, handler_report.dict())
        renderer.render()
        self.assertEqual(len(self.recorder.lines), 4)


class TestProgressTracking(ClientTests):

    def test_display_none(self):
        fake_prompt = Mock()
        tracker = ProgressTracker(fake_prompt)
        tracker.display(None)

    def test_display_no_report(self):
        fake_prompt = Mock()
        tracker = ProgressTracker(fake_prompt)
        tracker.display({})

    def test_display_no_snapshot(self):
        reports = [
            {'repo_id': 1, 'state': 'merging'},
            {'repo_id': 2, 'state': 'merging'},
            {'repo_id': 3, 'state': 'merging'},
        ]
        report = {
            'progress': reports
        }
        mock_prompt = Mock()
        snapshot = [(r, Mock()) for r in reports]
        mock_prompt.create_progress_bar.side_effect = [s[1] for s in snapshot]
        tracker = ProgressTracker(mock_prompt)
        tracker._render = Mock()
        tracker.display(report)
        self.assertEqual(tracker.snapshot, snapshot)
        tracker._render.assert_has_calls([call(r, pb) for r, pb in snapshot])
        mock_prompt.write.assert_has_calls(
            [
                call('\n'),
                call('(1/3) Repository: 1'),
                call('\n'),
                call('(2/3) Repository: 2'),
                call('\n'),
                call('(3/3) Repository: 3')
            ]
        )

    def test_display_with_snapshot(self):
        reports = [
            {'repo_id': 1, 'state': 'import_finished'},
            {'repo_id': 2, 'state': 'import_finished'},
            {'repo_id': 3, 'state': 'import_finished'},
            {'repo_id': 4, 'state': 'import_finished'},
            {'repo_id': 5, 'state': 'import_finished'},
            {'repo_id': 6, 'state': 'merging'},
        ]
        report = {
            'progress': reports
        }
        mock_prompt = Mock()
        snapshot = [(r, Mock()) for r in reports]
        mock_prompt.create_progress_bar.side_effect = [s[1] for s in snapshot[3:]]
        tracker = ProgressTracker(mock_prompt)
        tracker.snapshot = snapshot[:3]
        tracker._render = Mock()
        tracker.display(report)
        self.assertEqual(tracker.snapshot, snapshot)
        tracker._render.assert_has_calls([call(r, pb) for r, pb in snapshot[3:]])
        mock_prompt.write.assert_has_calls(
            [
                call('\n'),
                call('(4/6) Repository: 4'),
                call('\n'),
                call('(5/6) Repository: 5'),
                call('\n'),
                call('(6/6) Repository: 6')
            ]
        )

    def test_find(self):
        reports = [
            {'repo_id': 1, 'state': 'merging'},
            {'repo_id': 2, 'state': 'merging'},
            {'repo_id': 3, 'state': 'merging'},
        ]
        self.assertEqual(ProgressTracker._find(2, reports), reports[1])

    def test_render(self):
        report = {
            'repo_id': 1,
            'state': 'adding_units',
            'unit_add': {
                'total': 10,
                'completed': 5,
                'details': 'http://redhat.com/foo/bar.unit'
            }
        }
        progress_bar = Mock()
        ProgressTracker._render(report, progress_bar)
        progress_bar.render.assert_called_with(5, 10, 'Step: Adding Units\n(5/10) Add unit: bar.unit')

    def test_render_not_adding_units(self):
        report = {
            'repo_id': 1,
            'state': 'merging',
            'unit_add': {
                'total': 10,
                'completed': 5,
                'details': ''
            }
        }
        progress_bar = Mock()
        ProgressTracker._render(report, progress_bar)
        progress_bar.render.assert_called_with(5, 10, None)

    def test_render_zero_total_and_finished(self):
        report = {
            'repo_id': 1,
            'state': 'import_finished',
            'unit_add': {
                'total': 0,
                'completed': 0,
                'details': ''
            }
        }
        progress_bar = Mock()
        ProgressTracker._render(report, progress_bar)
        progress_bar.render.assert_called_with(1, 1)

    def test_render_zero_total_and_not_finished(self):
        report = {
            'repo_id': 1,
            'state': 'merging',
            'unit_add': {
                'total': 0,
                'completed': 0,
                'details': ''
            }
        }
        progress_bar = Mock()
        ProgressTracker._render(report, progress_bar)
        progress_bar.render.assert_called_with(0.01, 1)
