from ... import base
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types.model import TypeDefinition
import pulp.plugins.types.database as types_db
import pulp.server.managers.plugin as plugin_manager


class MockImporter:
    @classmethod
    def metadata(cls):
        return {'types': ['mock_type']}


class MockDistributor:
    @classmethod
    def metadata(cls):
        return {'types': ['mock_type']}


class MockProfiler:
    @classmethod
    def metadata(cls):
        return {'types': ['mock_type']}


class MockCataloger:
    @classmethod
    def metadata(cls):
        return {'types': ['mock_type']}


class PluginManagerTests(base.PulpServerTests):

    def setUp(self):
        super(PluginManagerTests, self).setUp()

        plugin_api._create_manager()

        # Configure content manager
        plugin_api._MANAGER.importers.add_plugin('MockImporter', MockImporter, {})
        plugin_api._MANAGER.distributors.add_plugin('MockDistributor', MockDistributor, {})
        plugin_api._MANAGER.profilers.add_plugin('MockProfiler', MockProfiler, {})
        plugin_api._MANAGER.catalogers.add_plugin('MockCataloger', MockCataloger, {})

        # Create the manager instance to test
        self.manager = plugin_manager.PluginManager()

    def tearDown(self):
        super(PluginManagerTests, self).tearDown()

        # Reset content manager
        plugin_api._MANAGER.importers.remove_plugin('MockImporter')
        plugin_api._MANAGER.distributors.remove_plugin('MockDistributor')
        plugin_api._MANAGER.profilers.remove_plugin('MockDistributor')

    def test_types(self):
        """
        Tests retrieving all types in the database.
        """

        # Setup
        types_db.clean()
        type_def_1 = TypeDefinition('type-1', 'Type 1', 'Type 1', [], [], [])
        type_def_2 = TypeDefinition('type-2', 'Type 2', 'Type 2', [], [], [])

        types_db._create_or_update_type(type_def_1)
        types_db._create_or_update_type(type_def_2)

        # Test
        found_defs = self.manager.types()

        # Verify
        self.assertEqual(2, len(found_defs))

        for type_def in [type_def_1, type_def_2]:
            found_def = [t for t in found_defs if t['id'] == type_def.id][0]

            self.assertEqual(found_def['id'], type_def.id)
            self.assertEqual(found_def['display_name'], type_def.display_name)
            self.assertEqual(found_def['description'], type_def.description)
            self.assertEqual(found_def['unit_key'], type_def.unit_key)
            self.assertEqual(found_def['search_indexes'], type_def.search_indexes)
            self.assertEqual(found_def['referenced_types'], type_def.referenced_types)

    def test_types_no_types(self):
        """
        Tests an empty list is returned when no types are loaded.
        """
        # Setup
        types_db.clean()

        # Test
        found_defs = self.manager.types()

        # Verify
        self.assertTrue(isinstance(found_defs, list))
        self.assertEqual(0, len(found_defs))

    def test_importers(self):
        """
        Tests retieving all importers.
        """

        # Test
        found = self.manager.importers()

        # Verify
        self.assertEqual(1, len(found))
        self.assertEqual('MockImporter', found[0]['id'])

    def test_importers_no_importers(self):
        """
        Tests an empty list is returned when no importers are present.
        """

        # Setup
        plugin_api._MANAGER.importers.remove_plugin('MockImporter')

        # Test
        found = self.manager.importers()

        # Verify
        self.assertTrue(isinstance(found, list))
        self.assertEqual(0, len(found))

    def test_distributors(self):
        """
        Tests retrieving all distributors.
        """

        # Test
        found = self.manager.distributors()

        # Verify
        self.assertEqual(1, len(found))
        self.assertEqual('MockDistributor', found[0]['id'])

    def test_distributors_no_distributors(self):
        """
        Tests an empty list is returned when no distributors are present.
        """

        # Setup
        plugin_api._MANAGER.distributors.remove_plugin('MockDistributor')

        # Test
        found = self.manager.distributors()

        # Verify
        self.assertTrue(isinstance(found, list))
        self.assertEqual(0, len(found))

    def test_profilers(self):
        """
        Tests retrieving all profilers.
        """

        # Test
        found = self.manager.profilers()

        # Verify
        self.assertEqual(1, len(found))
        self.assertEqual('MockProfiler', found[0]['id'])

    def test_profilers_no_profilers(self):
        """
        Tests an empty list is returned when no profilers are present.
        """

        # Setup
        plugin_api._MANAGER.profilers.remove_plugin('MockProfiler')

        # Test
        found = self.manager.profilers()

        # Verify
        self.assertTrue(isinstance(found, list))
        self.assertEqual(0, len(found))

    def test_catalogers(self):
        """
        Tests retrieving all catalogers.
        """

        # Test
        found = self.manager.catalogers()

        # Verify
        self.assertEqual(1, len(found))
        self.assertEqual('MockCataloger', found[0]['id'])

    def test_catalogers_no_catalogers(self):
        """
        Tests an empty list is returned when no catalogers are present.
        """

        # Setup
        plugin_api._MANAGER.catalogers.remove_plugin('MockCataloger')

        # Test
        found = self.manager.catalogers()

        # Verify
        self.assertTrue(isinstance(found, list))
        self.assertEqual(0, len(found))
