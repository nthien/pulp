"""
This module contains tests for the pulp.server.managers.repo.unit_association_query module.
"""
import copy
import datetime
import math
import unittest

import mock

from .... import base
from pulp.common import dateutils
from pulp.plugins.types import database, model
from pulp.server.db.model.criteria import Criteria, UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit
import pulp.server.managers.content.cud as content_cud_manager
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo.unit_association as association_manager
import pulp.server.managers.repo.unit_association_query as association_query_manager


TYPE_DEF_ALPHA = model.TypeDefinition('alpha', 'Alpha', 'Test Type Alpha',
                                      ['key_1'], ['search_1'], [])
TYPE_DEF_BETA = model.TypeDefinition('beta', 'Beta', 'Test Type Beta',
                                     ['key_1'], [], [])
TYPE_DEF_GAMMA = model.TypeDefinition('gamma', 'Gamma', 'Test Type Gamma',
                                      ['key_1'], [], [])
TYPE_DEF_DELTA = model.TypeDefinition('delta', 'Delta', 'Test Type Delta',
                                      ['key_1'], [], [])
TYPE_DEF_EPSILON = model.TypeDefinition('epsilon', 'Epsilon', 'Test Type Epsilon',
                                        ['key_1'], [], [])

_QUERY_TYPES = [TYPE_DEF_ALPHA, TYPE_DEF_BETA, TYPE_DEF_GAMMA, TYPE_DEF_DELTA, TYPE_DEF_EPSILON]


class RepoUnitAssociationQueryManagerTests(unittest.TestCase):
    """
    Tests for the RepoUnitAssociationQueryManager class.
    """
    def test__merged_units_unique_units_doesnt_change_args(self):
        """
        We had a bug[0] where it was discovered that _merged_units_unique_units() was altering
        its associations_lookup parameter, which led to large memory usage. This test asserts that
        its parameters are not altered.

        [0] https://bugzilla.redhat.com/show_bug.cgi?id=1093870
        """
        associations_lookup = {
            'rpm': {'some_id': [{'some': 'unit'}], 'some_other_id': [{'some': 'unit'}]}
        }
        associated_units = [
            {'_content_type_id': 'rpm', '_id': 'some_id'},
            {'_content_type_id': 'rpm', '_id': 'some_other_id'},
        ]
        # Let's keep a copy of each data structure, so we can ensure that this method didn't change
        # them
        associations_lookup_copy = copy.deepcopy(associations_lookup)
        associated_units_copy = copy.deepcopy(associated_units)

        # Let's run the generator by passing it to list()
        return_value = list(
            association_query_manager.RepoUnitAssociationQueryManager._merged_units_unique_units(
                associations_lookup, associated_units))

        # Now let's ensure that the data structures have not changed
        self.assertEqual(associations_lookup, associations_lookup_copy)
        self.assertEqual(associated_units, associated_units_copy)

        # Assert that the return value is correct
        expected_return_value = [
            {'some': 'unit', 'metadata': {'_id': 'some_id', '_content_type_id': 'rpm'}},
            {'some': 'unit', 'metadata': {'_id': 'some_other_id', '_content_type_id': 'rpm'}}
        ]
        self.assertEqual(return_value, expected_return_value)


class UnitAssociationQueryTests(base.PulpServerTests):

    def clean(self):
        super(UnitAssociationQueryTests, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()

    def setUp(self):
        super(UnitAssociationQueryTests, self).setUp()
        database.update_database(_QUERY_TYPES)
        self.manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.association_manager = association_manager.RepoUnitAssociationManager()
        self.content_manager = content_cud_manager.ContentManager()
        self._populate()

    def tearDown(self):
        super(UnitAssociationQueryTests, self).tearDown()
        manager_factory.reset()

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    def _populate(self, _):
        """
        Populates the database with units and associations with the
        following properties:

        - Units are from types: alpha, beta, gamma
        - Each unit has metadata:
          - key_1 - unique per unit per type (is the unit ID)
          - md_1 - unique per unit in a given type (simple counter)
          - md_2 - 0 or 1 depending on when it was added
          - md_3 - number of characters in the unit ID
        - All associations will have created/updated dates in ascending
          order according to alphabetical order

        - Alpha Units
          - Only associated once with repo-1
          - Association owner is type importer with ID test-importer
        - Beta Units
          - Only associated once with repo-1
          - Only associated once with repo-2 as well
          - Association owner is type user with ID admin
        - Gamma Units
          - Each associated twice with repo-1
          - One association is type importer with ID test-importer-2
          - One association is type user with ID admin-2
          - The user-created associations are older than the importer ones
        - Delta Units
          - Only associated with repo-2
          - Association owner is type importer with ID test-importer
        - Epsilon Units
          - Exist in the database but not associations
        """

        # -- test data --------

        self.units = {
            'alpha': ['aardvark', 'anthill', 'apple'],
            'beta': ['ball', 'balloon', 'bat', 'boardwalk'],
            'gamma': ['garden', 'gnome'],
            'delta': ['dog', 'dragon']
        }

        #   Generate timestamps 1 day apart in ascending order relative to now.
        #   The last entry is 1 day before now. Timestamps are already in iso8601.
        #     timestamps[x] < timestamps[x+1]
        now = datetime.datetime.now()
        self.timestamps = []
        for i in range(10, 0, -1):
            ts = now - datetime.timedelta(i)
            self.timestamps.append(dateutils.format_iso8601_datetime(ts))

        #   Assertions based on the test data
        self.repo_1_count = reduce(lambda x, y: x + len(self.units[y]), ['alpha', 'beta', 'gamma'],
                                   0)
        self.repo_2_count = reduce(lambda x, y: x + len(self.units[y]), ['beta', 'delta'], 0)

        for type_id, unit_ids in self.units.items():
            unit_ids.sort()
            for i, unit_id in enumerate(unit_ids):
                metadata = {'key_1': unit_id, 'md_1': i, 'md_2': i % 2, 'md_3': len(unit_id)}
                self.content_manager.add_content_unit(type_id, unit_id, metadata)

        def make_association(repo_id, type_id, unit_id, index):
            """
            Utility to perform standard association test data stuff such as
            setting the created/updated timestamps.
            """

            association_collection = RepoContentUnit.get_collection()
            self.association_manager.associate_unit_by_id(repo_id, type_id, unit_id)
            a = association_collection.find_one({'repo_id': repo_id, 'unit_type_id': type_id,
                                                 'unit_id': unit_id})
            a['created'] = self.timestamps[index]
            a['updated'] = self.timestamps[index]
            association_collection.save(a)

        #   Alpha
        for i, unit_id in enumerate(self.units['alpha']):
            make_association('repo-1', 'alpha', unit_id, i)

        #   Beta
        for i, unit_id in enumerate(self.units['beta']):
            make_association('repo-1', 'beta', unit_id, i)
            make_association('repo-2', 'beta', unit_id, i)

        #   Gamma
        for i, unit_id in enumerate(self.units['gamma']):
            make_association('repo-1', 'gamma', unit_id,
                             i + 1)
            make_association('repo-1', 'gamma', unit_id, i)

        #   Delta
        for i, unit_id in enumerate(self.units['delta']):
            make_association('repo-2', 'delta', unit_id, i)

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_find_by_criteria(self, mock_query):
        criteria = Criteria()
        self.manager.find_by_criteria(criteria)
        mock_query.assert_called_once_with(criteria)

    # -- get_units tests ------------------------------------------------------

    class GetUnitsMock(association_query_manager.RepoUnitAssociationQueryManager):

        def __init__(self):
            self.called_get_units = False
            self.repo_id = None
            self.criteria = None
            self.as_generator = None

        def get_units(self, repo_id, criteria=None, as_generator=None):
            self.called_get_units = True
            self.repo_id = repo_id
            self.criteria = criteria
            self.as_generator = as_generator

    def test_get_units_multiple_types(self):
        # Setup
        mock_manager = self.GetUnitsMock()

        # Test
        criteria = UnitAssociationCriteria(type_ids=['fus', 'ro'])
        mock_manager.get_units_across_types('repo-1', criteria=criteria)

        # Verify
        self.assertTrue(mock_manager.called_get_units)

        self.assertEqual('repo-1', mock_manager.repo_id)
        self.assertEqual(criteria, mock_manager.criteria)

    def test_get_units_single_type(self):
        # Setup
        mock_manager = self.GetUnitsMock()

        # Test
        criteria = UnitAssociationCriteria()
        mock_manager.get_units_by_type('repo-1', 'fus', criteria=criteria)

        # Verify
        self.assertTrue(mock_manager.called_get_units)

        self.assertEqual('repo-1', mock_manager.repo_id)
        self.assertEqual(['fus'], mock_manager.criteria.type_ids)

    def test_get_units_no_criteria(self):
        mock_manager = self.GetUnitsMock()

        # Test
        mock_manager.get_units('repo-1')

        # Verify
        self.assertTrue(mock_manager.called_get_units)

        self.assertEqual('repo-1', mock_manager.repo_id)
        self.assertEqual(None, mock_manager.criteria)

    def test_get_units_across_types(self):
        # Test
        units_1 = self.manager.get_units_across_types('repo-1')
        units_2 = self.manager.get_units_across_types('repo-2')

        # Verify
        self.assertEqual(len(units_1), self.repo_1_count)
        self.assertEqual(len(units_2), self.repo_2_count)

        for u in units_1 + units_2:
            self._assert_unit_integrity(u)

    def test_get_units_filter_type(self):
        # Test
        criteria = UnitAssociationCriteria(type_ids=['alpha', 'beta'])
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify
        expected_count = reduce(lambda x, y: x + len(self.units[y]), ['alpha', 'beta'], 0)
        self.assertEqual(expected_count, len(units))

        for u in units:
            self._assert_unit_integrity(u)
            self.assertTrue(u['unit_type_id'] in ['alpha', 'beta'])

    def test_get_units_limit(self):
        # Test
        low_criteria = UnitAssociationCriteria(limit=2)
        low_units = self.manager.get_units_across_types('repo-1', low_criteria)

        high_criteria = UnitAssociationCriteria(limit=10000)
        high_units = self.manager.get_units_across_types('repo-1', high_criteria)

        # Verify
        self.assertEqual(2, len(low_units))
        self.assertEqual(self.repo_1_count, len(high_units))

        #   Make sure the limit was applied to the front of the results
        self.assertEqual(low_units[0], high_units[0])
        self.assertEqual(low_units[1], high_units[1])

    def test_get_units_skip(self):
        # Test
        skip_criteria = UnitAssociationCriteria(skip=2)
        skip_units = self.manager.get_units_across_types('repo-1', skip_criteria)

        all_units = self.manager.get_units_across_types('repo-1')

        # Verify
        self.assertEqual(self.repo_1_count - 2, len(skip_units))

        # Make sure it was the first two that were actually skipped
        for su, au in zip(skip_units, all_units[2:]):
            self.assertEqual(su, au)

    def test_get_units_filter_created(self):
        # Test
        after_criteria = UnitAssociationCriteria(
            association_filters={'created': {'$gt': self.timestamps[0]}})
        after_units = self.manager.get_units_across_types('repo-1', after_criteria)

        before_criteria = UnitAssociationCriteria(
            association_filters={'created': {'$lt': self.timestamps[1]}})
        before_units = self.manager.get_units_across_types('repo-1', before_criteria)

        # Verify

        # The first association in each type/owner combination will be timestamps[0],
        # the second timestamps[1]. There are 4 such type/owner combinations,
        # however the user associations in gamma have timestamp offsets of i+1.

        self.assertEqual(self.repo_1_count - 3, len(after_units))
        self.assertEqual(3, len(before_units))

    def test_get_units_remove_duplicates(self):
        # Test
        criteria = UnitAssociationCriteria(remove_duplicates=True)
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify

        # The gamma units are associated twice, so they should only be returned once.
        self.assertEqual(self.repo_1_count, len(units))

        # there should be 2 gamma units returned
        gamma_units = [u for u in units if u['unit_type_id'] == 'gamma']
        self.assertEqual(2, len(gamma_units))

    def test_get_units_with_fields(self):
        # Test
        criteria = UnitAssociationCriteria(association_fields=['created'])
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify
        for u in units:
            self.assertTrue('created' in u)
            self.assertFalse('updated' in u)

    # -- get_units_by_type tests ----------------------------------------------

    def test_get_units_by_type_no_criteria(self):
        # Test
        alpha_units = self.manager.get_units_by_type('repo-1', 'alpha')
        beta_units = self.manager.get_units_by_type('repo-1', 'beta')
        epsilon_units = self.manager.get_units_by_type('repo-1', 'epsilon')

        # Verify
        self.assertEqual(len(self.units['alpha']), len(alpha_units))
        self.assertEqual(len(self.units['beta']), len(beta_units))
        self.assertEqual(0, len(epsilon_units))

        for u in alpha_units + beta_units:
            self._assert_unit_integrity(u)

    def test_get_units_by_type_association_filter(self):
        # Test
        criteria = UnitAssociationCriteria(
            association_filters={'updated': self.timestamps[1]}
        )
        units = self.manager.get_units_by_type('repo-1', 'gamma', criteria)

        # Verify

        self.assertEqual(1, len(units))

    def test_get_units_by_type_unit_metadata_filter(self):
        # Test
        criteria = UnitAssociationCriteria(unit_filters={'md_2': 0})
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected = math.ceil(float(len(self.units['alpha'])) / float(2))
        self.assertEqual(expected, len(units))

        for u in units:
            self.assertEqual(u['metadata']['md_2'], 0)

    def test_get_units_by_type_filter_wildcard(self):
        # Test
        criteria = UnitAssociationCriteria(unit_filters={'key_1': {'$regex': 'aa.*'}})
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(1, len(units))
        self.assertEqual('aardvark', units[0]['metadata']['key_1'])

    def test_get_units_by_type_association_sort_limit(self):
        # Test
        criteria = UnitAssociationCriteria(
            association_sort=[('updated', association_manager.SORT_DESCENDING)], limit=2)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(2, len(units))
        for i in range(0, len(units) - 1):
            u1 = units[i]
            u2 = units[i + 1]
            self.assertTrue(u1['updated'] >= u2['updated'])

    def test_get_units_by_type_unit_metadata_sort_limit(self):
        # Test
        criteria = UnitAssociationCriteria(
            unit_sort=[('md_2', association_manager.SORT_DESCENDING)], limit=2)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(2, len(units))
        for i in range(0, len(units) - 1):
            u1 = units[i]
            u2 = units[i + 1]
            self.assertTrue(u1['metadata']['md_2'] >= u2['metadata']['md_2'])

    def test_get_units_by_type_association_sort_skip(self):
        # Test
        criteria = UnitAssociationCriteria(
            association_sort=[('created', association_manager.SORT_DESCENDING)], skip=1)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected_count = len(self.units['alpha']) - 1  # skip the first
        self.assertEqual(expected_count, len(units))

    def test_get_units_by_type_unit_metadata_sort_skip(self):
        # Test
        criteria = UnitAssociationCriteria(
            unit_sort=[('md_2', association_manager.SORT_DESCENDING)], skip=1)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected_count = len(self.units['alpha']) - 1  # skip the first
        self.assertEqual(expected_count, len(units))

    def test_get_units_by_type_sort_association_data(self):
        # Test
        sort_criteria = UnitAssociationCriteria(
            association_sort=[('created', association_manager.SORT_DESCENDING)])
        sort_units = self.manager.get_units_by_type('repo-1', 'alpha', sort_criteria)

        # Verify
        self.assertEqual(len(self.units['alpha']), len(sort_units))

        for i in range(0, len(sort_units) - 1):
            u1 = sort_units[i]
            u2 = sort_units[i + 1]
            self.assertTrue(u1['created'] >= u2['created'])

    def test_get_units_by_type_sort_unit_data(self):
        # Test
        sort_criteria = UnitAssociationCriteria(
            unit_sort=[('md_2', association_manager.SORT_DESCENDING)])
        sort_units = self.manager.get_units_by_type('repo-1', 'alpha', sort_criteria)

        # Verify
        self.assertEqual(len(self.units['alpha']), len(sort_units))

        for i in range(0, len(sort_units) - 1):
            u1 = sort_units[i]
            u2 = sort_units[i + 1]
            self.assertTrue(u1['metadata']['md_2'] >= u2['metadata']['md_2'])

    def test_get_units_by_type_remove_duplicates(self):
        # Test
        criteria = UnitAssociationCriteria(remove_duplicates=True)
        units = self.manager.get_units_by_type('repo-1', 'gamma', criteria)

        # only one association per gamma unit
        self.assertEqual(len(self.units['gamma']), len(units))
        self.assertEqual(units[0]['unit_id'], 'garden')

    def test_get_units_by_type_with_assoc_fields(self):
        # Test
        criteria = UnitAssociationCriteria(association_fields=['created'])
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        for u in units:
            self.assertTrue('created' in u)
            self.assertFalse('updated' in u)

            # Make sure the unit fields are untouched by the filter
            self.assertTrue('key_1' in u['metadata'])
            self.assertTrue('md_1' in u['metadata'])

    def test_get_units_by_type_with_unit_fields(self):
        # Test
        criteria = UnitAssociationCriteria(unit_fields=['key_1', 'md_1'])
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        for u in units:
            # Make sure the association fields are untouched by the filter
            self.assertTrue('updated' in u)
            self.assertTrue('created' in u)

            self.assertTrue('key_1' in u['metadata'])
            self.assertTrue('md_1' in u['metadata'])
            self.assertFalse('md_2' in u['metadata'])
            self.assertFalse('md_3' in u['metadata'])

    def test_get_units_by_type_assoc_sort_unit_filters(self):
        """
        This test is a direct result of https://bugzilla.redhat.com/show_bug.cgi?id=952775
        """
        # Test
        criteria = UnitAssociationCriteria(
            unit_filters={'md_2': 0},
            association_sort=[('created', association_manager.SORT_ASCENDING)])
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected = math.ceil(float(len(self.units['alpha'])) / float(2))
        self.assertEqual(expected, len(units))

        #  The bug was that the metadata was None
        for u in units:
            self.assertEqual(u['metadata']['md_2'], 0)

    def test_get_units_by_type_not_query(self):
        """
        Mongo really doesn't like $not queries when regular expressions are
        involved. This test is to make sure that across mongo and pymongo
        versions a not expression against a regular expression continues to
        work.

        There is an important step in the parsing of the criteria from the
        REST call into the Criteria object. This call will use that method
        to more closely test the end to end experience.
        """

        # Setup

        # I got bit by the fact that incoming REST requests are in unicode;
        # the criteria parsing didn't account for this. This example specifically
        # replicates that by having the not and its value in unicode.

        query_string = {
            'filters': {
                'unit': {
                    'key_1': {
                        u'$not': u'.*aa.*'
                    }
                }
            }
        }
        criteria = UnitAssociationCriteria.from_client_input(query_string)

        # Test
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(len(self.units['alpha']) - 1, len(units))
        for u in units:
            self.assertTrue(u['metadata']['key_1'] != 'aardvark')

    def test_criteria_str(self):
        # Setup
        c1 = UnitAssociationCriteria()
        c2 = UnitAssociationCriteria(
            type_ids=['a'], association_filters={'a': 'a'}, unit_filters={'b': 'b'},
            association_sort=['c'], unit_sort=['d'], limit=1, skip=2, association_fields=['e'],
            unit_fields=['f'], remove_duplicates=True)

        # Test no exceptions are raised
        str(c1)
        str(c2)

    def test_criteria_init(self):
        # Test
        c = UnitAssociationCriteria(type_ids='single')
        self.assertEqual(['single'], c.type_ids)

    def _assert_unit_integrity(self, unit):
        """
        Makes sure all of the expected fields are present in the unit and that
        it is assembled correctly. This call has a limited concept of what the
        values should be but will do some tests were possible.

        This call will have to change if the returned structure of the units is
        changed.
        """

        self.assertTrue(unit['repo_id'] is not None)
        self.assertTrue(unit['unit_type_id'] is not None)
        self.assertTrue(unit['unit_id'] is not None)
        self.assertTrue(unit['created'] is not None)
        self.assertTrue(unit['updated'] is not None)

        self.assertTrue(unit['metadata'] is not None)
        self.assertTrue(unit['metadata']['key_1'] is not None)
        self.assertTrue(unit['metadata']['md_1'] is not None)
        self.assertTrue(unit['metadata']['md_2'] is not None)
        self.assertTrue(unit['metadata']['md_3'] is not None)
