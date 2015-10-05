import unittest

import mock

from pulp.server.db.model.repository import RepoContentUnit


REPOSITORY = 'pulp.server.db.model.repository'


class TestRepoContentUnit(unittest.TestCase):
    def setUp(self):
        self.unit = RepoContentUnit('repo1', 'unit1', 'rpm')

    def test_utc_in_iso8601(self):
        # make sure the ISO8601 serialization includes the UTC timezone
        self.assertTrue(
            self.unit.created.endswith('Z') or
            self.unit.created.endswith('+00:00'))


class TestRepoContentUnitInit(unittest.TestCase):

    def setUp(self):
        self.patch_a = mock.patch(REPOSITORY + '.Model.__init__')
        self.mock_Model__init__ = self.patch_a.start()

        self.patch_b = mock.patch(REPOSITORY + '.dateutils')
        self.mock_dateutils = self.patch_b.start()

        self.mock_repo_id = mock.Mock()
        self.mock_unit_id = mock.Mock()
        self.mock_unit_type_id = mock.Mock()
        self.repo_content_unit = RepoContentUnit(self.mock_repo_id, self.mock_unit_id,
                                                 self.mock_unit_type_id)

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()

    def test_repo_content_unit___init___calls_super___init__(self):
        self.mock_Model__init__.assert_called_once_with()

    def test_repo_content_unit___init___stores_repo_id(self):
        self.assertTrue(self.repo_content_unit.repo_id is self.mock_repo_id)

    def test_repo_content_unit___init___stores_unit_id(self):
        self.assertTrue(self.repo_content_unit.unit_id is self.mock_unit_id)

    def test_repo_content_unit___init___stores_unit_type_id(self):
        self.assertTrue(self.repo_content_unit.unit_type_id is self.mock_unit_type_id)

    def test_repo_content_unit___init___generates_8601_utc_timestamp(self):
        self.mock_dateutils.now_utc_timestamp.assert_called_once_with()
        utc_timestamp = self.mock_dateutils.now_utc_timestamp.return_value
        self.mock_dateutils.format_iso8601_utc_timestamp.assert_called_once_with(utc_timestamp)

    def test_repo_content_unit___init___stores_created(self):
        created = self.mock_dateutils.format_iso8601_utc_timestamp.return_value
        self.assertTrue(self.repo_content_unit.created is created)

    def test_repo_content_unit___init___stores_updated_equal_to_created(self):
        self.assertTrue(self.repo_content_unit.created is self.repo_content_unit.updated)
