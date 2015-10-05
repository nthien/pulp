from gettext import gettext as _
from pprint import pformat
import errno
import os

from pulp.plugins.types import database as content_types_db
from pulp.plugins.util.misc import paginate
from pulp.server import config as pulp_config
from pulp.server.exceptions import InvalidValue, MissingResource


class ContentQueryManager(object):
    """
    Query operations for content types and individual content units.
    """

    def list_content_types(self):
        """
        List the currently defined content type ids.
        @return: list of content type ids
        @rtype:  list [str, ...]
        """
        return content_types_db.all_type_ids()

    @classmethod
    def find_by_criteria(cls, type_id, criteria):
        """
        Return a list of content units that match the provided criteria.

        @param type_id: id of ContentType to search
        @type  type_id: basestring

        @param criteria:    A Criteria object representing a search you want
                            to perform
        @type  criteria:    pulp.server.db.model.criteria.Criteria

        @return:    list of content unit instances
        @rtype:     list
        """
        return cls.get_content_unit_collection(type_id).query(criteria)

    def list_content_units(self,
                           content_type,
                           db_spec=None,
                           model_fields=None,
                           start=0,
                           limit=None):
        """
        DEPRECATED!!!  Please use find_by_criteria() instead.

        List the content units in a content type collection.
        @param content_type: unique id of content collection
        @type content_type: str
        @param db_spec: spec document used to filter the results,
                        None means no filter
        @type db_spec: None or dict
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @param start: offset from the beginning of the results to return as the
                      first element
        @type start: non-negative int
        @param limit: the maximum number of results to return,
                      None means no limit
        @type limit: None or non-negative int
        @return: list of content units in the content type collection that
                 matches the parameters
        @rtype: (possibly empty) tuple of dicts
        """
        collection = content_types_db.type_units_collection(content_type)
        if db_spec is None:
            db_spec = {}
        cursor = collection.find(db_spec, fields=model_fields)
        if start > 0:
            cursor.skip(start)
        if limit is not None:
            cursor.limit(limit)
        return tuple(cursor)

    @staticmethod
    def get_content_unit_collection(type_id):
        """
        Get and return the PulpCollection that corresponds to a given
        ContentType id.

        @param type_id: ContentType id
        @type  type_id: basestring

        @return:    PulpCollection instance
        @rtype:     PulpCollection
        """
        return content_types_db.type_units_collection(type_id)

    def get_content_unit_by_keys_dict(self, content_type, unit_keys_dict, model_fields=None):
        """
        Look up an individual content unit in the corresponding content type
        collection using the given keys dictionary.
        :param content_type: unique id of content collection
        :type content_type: str
        :param unit_keys_dict: dictionary of key, value pairs that can uniquely
                               identify a content unit
        :type unit_keys_dict: dict
        :param model_fields: fields of each content unit to report,
                             None means all fields
        :type model_fields: None or list of str's
        :return: content unit from the content type collection that matches the
                 keys dict
        :rtype: dict
        :raises ValueError: if the unit_keys_dict is invalid
        :raises L{MissingResource}: if no content unit in the content type
                                    collection matches the keys dict
        """
        units_gen = self.get_multiple_units_by_keys_dicts(content_type, (unit_keys_dict,),
                                                          model_fields)
        try:
            unit = units_gen.next()
        except StopIteration:
            raise MissingResource(_('No content unit for keys: %(k)s') %
                                  {'k': pformat(unit_keys_dict)})
        return unit

    def get_content_unit_by_id(self, content_type, unit_id, model_fields=None):
        """
        Look up an individual content unit in the corresponding content type
        collection using the given id.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_id: unique id of content unit
        @type unit_id: str
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @return: content unit from the content type collection that matches the
                 given id
        @rtype: dict
        @raise: L{MissingResource} if no content unit in the content type
                collection matches the id
        """
        units = self.get_multiple_units_by_ids(content_type,
                                               (unit_id,),
                                               model_fields)
        if not units:
            raise MissingResource(_('No content unit found for: %(i)s') %
                                  {'i': unit_id})
        return units[0]

    def get_multiple_units_by_keys_dicts(self, content_type, unit_keys_dicts, model_fields=None):
        """
        Look up multiple content units in the collection for the given content
        type collection that match the list of keys dictionaries.
        :param content_type: unique id of content collection
        :type content_type: str
        :param unit_keys_dicts: list of dictionaries whose key, value pairs can
                                uniquely identify a content unit
        :type unit_keys_dicts: list of dict's
        :param model_fields: fields of each content unit to report,
                             None means all fields
        :type model_fields: None or list of str's
        :return: tuple of content units found in the content type collection
                 that match the given unit keys dictionaries
        :rtype: (possibly empty) tuple of dict's
        :raises ValueError: if any of the keys dictionaries are invalid
        """
        collection = content_types_db.type_units_collection(content_type)
        for segment in paginate(unit_keys_dicts, page_size=50):
            spec = _build_multi_keys_spec(content_type, segment)
            cursor = collection.find(spec, fields=model_fields)
            for unit_dict in cursor:
                yield unit_dict

    def get_multiple_units_by_ids(self, content_type, unit_ids, model_fields=None):
        """
        Look up multiple content units in the collection for the given content
        type collection that match the list of ids.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_ids: list of unique content unit ids
        @type unit_ids: list of str's
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @return: tuple of content units found in the content type collection
                 that match the given ids
        @rtype: (possibly empty) tuple of dict's
        """
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find({'_id': {'$in': unit_ids}}, fields=model_fields)
        return tuple(cursor)

    def get_content_unit_keys(self, content_type, unit_ids):
        """
        Return the keys and values that will uniquely identify the content units
        that match the given unique ids.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_ids: list of unique content unit ids
        @type unit_ids: list of str's
        @return: two tuples of the same length, one of ids the second of key dicts
                 the same index in each tuple corresponds to a single content unit
        @rtype: tuple of (possibly empty) tuples
        """
        key_fields = content_types_db.type_units_unit_key(content_type)
        if key_fields is None:
            raise InvalidValue(['content_type'])
        all_fields = ['_id']
        _flatten_keys(all_fields, key_fields)
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find({'_id': {'$in': unit_ids}}, fields=all_fields)
        dicts = tuple(dict(d) for d in cursor)
        ids = tuple(d.pop('_id') for d in dicts)
        return (ids, dicts)

    @staticmethod
    def get_content_unit_ids(content_type, unit_keys):
        """
        Return a generator of ids that uniquely identify the content units that match the
        given unique keys dictionaries.

        :param content_type: unique id of content collection
        :type  content_type: str
        :param unit_keys: list of keys dictionaries that uniquely identify
                          content units in the given content type collection
        :type  unit_keys: list of dicts

        :return:    generator of unit IDs as strings
        :rtype:     generator
        """
        collection = content_types_db.type_units_collection(content_type)
        for segment in paginate(unit_keys):
            spec = _build_multi_keys_spec(content_type, segment)
            fields = ['_id']
            for item in collection.find(spec, fields=fields):
                yield str(item['_id'])

    def get_root_content_dir(self, content_type):
        """
        Get the full path to Pulp's root content directory for a given content
        type.
        @param content_type: unique id of content collection
        @type content_type: str
        @return: file system path for content type's root directory
        @rtype: str
        """
        # I'm partitioning the content on the file system based on content type
        storage_dir = pulp_config.config.get('server', 'storage_dir')
        root = os.path.join(storage_dir, 'content', content_type)
        try:
            os.makedirs(root)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise
        return root

    def request_content_unit_file_path(self, content_type, relative_path):
        """
        @param content_type: unique id of content collection
        @type content_type: str
        @param relative_path: on disk path of a content unit relative to the
                              root directory for the given content type
        @type relative_path: str
        @return: full file system path for given relative path
        @rtype: str
        """

        # Strip off the leading / if it exists; the importer may be sloppy and
        # hand it in and its presence breaks makedirs
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]

        unit_path = os.path.join(self.get_root_content_dir(content_type), relative_path)
        unit_dir = os.path.dirname(unit_path)
        try:
            os.makedirs(unit_dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                    raise

        return unit_path


def _flatten_keys(flat_keys, nested_keys):
    """
    Take list of string keys and (possibly) nested sub-lists and flatten it out
    into an un-nested list of string keys.
    @param flat_keys: the flat list to store all of the keys in
    @type flat_keys: list
    @param nested_keys: possibly nested list of string keys
    @type nested_keys: list
    """
    if not nested_keys:
        return
    for key in nested_keys:
        if isinstance(key, basestring):
            flat_keys.append(key)
        else:
            _flatten_keys(flat_keys, key)


def _build_multi_keys_spec(content_type, unit_keys_dicts):
    """
    Build a mongo db spec document for a query on the given content_type
    collection out of multiple content unit key dictionaries.
    :param content_type: unique id of the content type collection
    :type content_type: str
    :param unit_keys_dicts: list of key dictionaries whose key, value pairs can be
                            used as unique identifiers for a single content unit
    :type unit_keys_dicts: list of dict
    :return: mongo db spec document for locating documents in a collection
    :rtype: dict
    :raises ValueError: if any of the key dictionaries do not match the unique
            fields of the collection
    """
    # keys dicts validation constants
    key_fields = []
    _flatten_keys(key_fields, content_types_db.type_units_unit_key(content_type))
    key_fields_set = set(key_fields)
    extra_keys_msg = _('keys dictionary found with superfluous keys %(a)s, valid keys are %(b)s')
    missing_keys_msg = _('keys dictionary missing keys %(a)s, required keys are %(b)s')
    keys_errors = []
    # Validate all of the keys in the unit_keys_dict
    for keys_dict in unit_keys_dicts:
        # keys dict validation
        keys_dict_set = set(keys_dict)
        extra_keys = keys_dict_set.difference(key_fields_set)
        if extra_keys:
            keys_errors.append(extra_keys_msg % {'a': ','.join(extra_keys),
                                                 'b': ','.join(key_fields)})
        missing_keys = key_fields_set.difference(keys_dict_set)
        if missing_keys:
            keys_errors.append(missing_keys_msg % {'a': ','.join(missing_keys),
                                                   'b': ','.join(key_fields)})
    if keys_errors:
        value_error_msg = '\n'.join(keys_errors)
        raise ValueError(value_error_msg)
    # Build the spec
    spec = {'$or': unit_keys_dicts}
    return spec
