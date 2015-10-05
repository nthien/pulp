import errno
import math
import os
import shutil
import unittest

import mock

from pulp.bindings.exceptions import NotFoundException
from pulp.bindings.responses import Response
import pulp.client.upload.manager as upload_util


MOCK_UPLOAD_ID = 'ABC123'
MOCK_LOCATION = '/v2/uploads/%s/' % MOCK_UPLOAD_ID

TEST_RPM_FILENAME = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 '../data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm')


class UploadManagerTests(unittest.TestCase):

    def setUp(self):
        super(UploadManagerTests, self).setUp()

        # Temporary location to store tracker files
        self.upload_working_dir = '/tmp/pulp-upload-manager-test'
        if os.path.exists(self.upload_working_dir):
            shutil.rmtree(self.upload_working_dir)

        # Recreate for each test to minimize necessary cleanup
        self.mock_bindings = mock.Mock()
        self.mock_upload_bindings = mock.Mock()
        self.mock_bindings.uploads = self.mock_upload_bindings

        self._mock_initialize_upload()
        self._mock_upload_segment()
        self._mock_delete_upload()
        self._mock_import_upload()

        # Create the manager to test
        self.upload_manager = upload_util.UploadManager(self.upload_working_dir, self.mock_bindings)

    def tearDown(self):
        if os.path.exists(self.upload_working_dir):
            shutil.rmtree(self.upload_working_dir)

    def test_init_with_defaults(self):
        context = mock.MagicMock()
        context.config = {'filesystem': {'upload_working_dir': '/a/b/c'}}
        os.makedirs(self.upload_working_dir)

        manager = upload_util.UploadManager.init_with_defaults(context)

        self.assertTrue(isinstance(manager, upload_util.UploadManager))
        self.assertEqual(manager.upload_working_dir, '/a/b/c/default')

    def test_initialize_no_trackers(self):
        os.makedirs(self.upload_working_dir)

        # Test
        self.upload_manager.initialize()

        # Verify
        self.assertEqual(0, len(self.upload_manager.list_uploads()))

    @mock.patch('os.listdir')
    def test_no_workingdir(self, mock_listdir):
        ex = OSError('a mock error (ENOENT)')
        ex.errno = errno.ENOENT
        mock_listdir.side_effect = ex

        os.makedirs(self.upload_working_dir)

        # Test
        self.upload_manager.initialize()

        # Verify
        self.assertEqual(0, len(self.upload_manager.list_uploads()))

    @mock.patch('os.listdir')
    def test_workingdir_err(self, mock_listdir):
        ex = OSError('a mock error (EIO)')
        ex.errno = errno.EIO
        mock_listdir.side_effect = ex

        os.makedirs(self.upload_working_dir)

        # Test
        self.upload_manager.initialize()

        # Verify
        self.assertRaises(OSError, self.upload_manager.list_uploads)

    def test_initialize_with_trackers(self):
        # Setup
        all_ids = ['tf%s' % i for i in range(0, 2)]
        os.makedirs(self.upload_working_dir)

        for id in all_ids:
            filename = self.upload_manager._tracker_filename(id)
            tf = upload_util.UploadTracker(filename)
            tf.upload_id = id
            tf.save()

        # Verify

        # Verify list of all trackers
        trackers = self.upload_manager.list_uploads()
        self.assertEqual(len(all_ids), len(trackers))
        tracker_ids = [t.upload_id for t in trackers]
        for id in all_ids:
            self.assertTrue(id in tracker_ids)

        # Verify get returns a copy
        tracker1 = self.upload_manager.get_upload(tracker_ids[0])
        tracker2 = self.upload_manager.get_upload(tracker_ids[0])
        self.assertEqual(tracker1.upload_id, tracker_ids[0])
        self.assertEqual(tracker2.upload_id, tracker_ids[0])
        self.assertTrue(tracker1 is not tracker2)

    def test_initialize_upload(self):
        # Setup
        self.upload_manager.initialize()

        # Test
        upload_id = self.upload_manager.initialize_upload('fn-1', 'repo-1', 'type-1', {'k1': 'v1'},
                                                          {})

        # Verify

        # make sure it created the working directory
        self.assertTrue(os.path.exists(self.upload_working_dir))

        # Call to the server was correct
        self.assertEqual(upload_id, MOCK_UPLOAD_ID)

        # Tracker added to in memory cache
        in_memory = self.upload_manager._get_tracker_file_by_id(upload_id)
        self.assertTrue(in_memory is not None)
        self.assertEqual(in_memory.upload_id, upload_id)

        # Tracker file created on disk and has all of the specified values
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        self.assertTrue(os.path.exists(tf_filename))

        tracker = upload_util.UploadTracker.load(tf_filename)
        self.assertEqual(tracker.filename, tf_filename)
        self.assertEqual(tracker.upload_id, MOCK_UPLOAD_ID)
        self.assertEqual(tracker.location, MOCK_LOCATION)
        self.assertEqual(tracker.offset, 0)
        self.assertEqual(tracker.source_filename, 'fn-1')
        self.assertEqual(tracker.repo_id, 'repo-1')
        self.assertEqual(tracker.unit_type_id, 'type-1')
        self.assertEqual(tracker.unit_key, {'k1': 'v1'})
        self.assertEqual(tracker.unit_metadata, {})
        self.assertEqual(tracker.override_config, None)

    def test_initialize_upload_with_override_config(self):
        # Setup
        self.upload_manager.initialize()
        test_override_config = {'test-key': 'test-value'}

        # Test
        upload_id = self.upload_manager.initialize_upload('fn-1', 'repo-1', 'type-1', {'k1': 'v1'},
                                                          {}, test_override_config)

        # Verify

        # make sure it created the working directory
        self.assertTrue(os.path.exists(self.upload_working_dir))

        # Call to the server was correct
        self.assertEqual(upload_id, MOCK_UPLOAD_ID)

        # Tracker added to in memory cache
        in_memory = self.upload_manager._get_tracker_file_by_id(upload_id)
        self.assertTrue(in_memory is not None)
        self.assertEqual(in_memory.upload_id, upload_id)

        # Tracker file created on disk and has all of the specified values
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        self.assertTrue(os.path.exists(tf_filename))

        tracker = upload_util.UploadTracker.load(tf_filename)
        self.assertEqual(tracker.filename, tf_filename)
        self.assertEqual(tracker.upload_id, MOCK_UPLOAD_ID)
        self.assertEqual(tracker.location, MOCK_LOCATION)
        self.assertEqual(tracker.offset, 0)
        self.assertEqual(tracker.source_filename, 'fn-1')
        self.assertEqual(tracker.repo_id, 'repo-1')
        self.assertEqual(tracker.unit_type_id, 'type-1')
        self.assertEqual(tracker.unit_key, {'k1': 'v1'})
        self.assertEqual(tracker.unit_metadata, {})
        self.assertEqual(tracker.override_config, test_override_config)

    def test_upload_single_pass(self):
        # Setup
        # way higher than needed
        self.upload_manager.chunk_size = upload_util.DEFAULT_CHUNKSIZE * 10
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload(TEST_RPM_FILENAME, 'repo-1', 'type-1',
                                                          {'k': 'v'}, 'm-1')

        mock_callback = mock.Mock()

        # Test
        self.upload_manager.upload(upload_id, mock_callback.update_status)

        # Verify
        rpm_size = os.path.getsize(TEST_RPM_FILENAME)

        # Verify the callback calls
        self.assertEqual(1, mock_callback.update_status.call_count)
        self.assertEqual(rpm_size, mock_callback.update_status.call_args[0][0])
        self.assertEqual(rpm_size, mock_callback.update_status.call_args[0][1])

        # Verify the contents of the body sent to the server
        self.assertEqual(1, self.mock_upload_bindings.upload_segment.call_count)
        upload_args = self.mock_upload_bindings.upload_segment.call_args[0]
        self.assertEqual(upload_id, upload_args[0])
        self.assertEqual(0, upload_args[1])
        self.assertEqual(rpm_size, len(upload_args[2]))

        # Verify the state of the tracker file on disk
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        tracker = upload_util.UploadTracker.load(tf_filename)
        self.assertEqual(rpm_size, tracker.offset)

        # Verify the state of the tracker in memory
        tracker = self.upload_manager._get_tracker_file_by_id(upload_id)
        self.assertEqual(rpm_size, tracker.offset)
        self.assertEqual(True, tracker.is_finished_uploading)
        self.assertEqual(False, tracker.is_running)

    def test_upload_multiple_passes(self):
        # Setup
        self.upload_manager.chunk_size = 100
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload(TEST_RPM_FILENAME, 'repo-1', 'type-1',
                                                          {'k': 'v'}, 'm-1')

        mock_callback = mock.Mock()

        # Test
        self.upload_manager.upload(upload_id, mock_callback.update_status)

        # Verify
        rpm_size = os.path.getsize(TEST_RPM_FILENAME)
        num_upload_calls = int(math.ceil(float(rpm_size) / float(self.upload_manager.chunk_size)))

        # Verify the callback calls
        self.assertEqual(num_upload_calls, mock_callback.update_status.call_count)

        expected_offset = self.upload_manager.chunk_size
        for single_call_args in mock_callback.update_status.call_args_list:
            non_kwargs = single_call_args[0]
            self.assertEqual(expected_offset, non_kwargs[0])
            self.assertEqual(rpm_size, non_kwargs[1])
            expected_offset = min(expected_offset + self.upload_manager.chunk_size, rpm_size)

        # Verify the contents of the body sent to the server
        self.assertEqual(num_upload_calls, self.mock_upload_bindings.upload_segment.call_count)
        offset = 0
        for single_call_args in self.mock_upload_bindings.upload_segment.call_args_list:
            # Body
            f = open(TEST_RPM_FILENAME, 'r')
            f.seek(offset)
            expected_body = f.read(self.upload_manager.chunk_size)
            f.close()

            body = single_call_args[0][2]
            self.assertEqual(expected_body, body)

            # Correct offset sent to server
            self.assertEqual(offset, single_call_args[0][1])

            # Correct upload ID sent to server
            self.assertEqual(upload_id, single_call_args[0][0])

            offset += self.upload_manager.chunk_size

        # Verify the state of the tracker file on disk
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        tracker = upload_util.UploadTracker.load(tf_filename)
        self.assertEqual(rpm_size, tracker.offset)

        # Verify the state of the tracker in memory
        tracker = self.upload_manager._get_tracker_file_by_id(upload_id)
        self.assertEqual(rpm_size, tracker.offset)

    def test_upload_concurrent_upload(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload(TEST_RPM_FILENAME, 'repo-1',
                                                          'type-1', {'k': 'v'}, 'm-1')

        tracker = self.upload_manager._get_tracker_file_by_id(upload_id)
        tracker.is_running = True

        # Test
        self.assertRaises(upload_util.ConcurrentUploadException, self.upload_manager.upload,
                          upload_id)

    def test_delete_upload(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload('f', 'r', 't', {'k': 'v'}, 'm')

        tf_filename = self.upload_manager._tracker_filename(upload_id)
        self.assertTrue(os.path.exists(tf_filename))

        # Test
        self.upload_manager.delete_upload(upload_id)

        # Verify
        self.assertTrue(not os.path.exists(tf_filename))  # filesystem
        self.assertTrue(self.upload_manager._get_tracker_file_by_id(upload_id) is None)  # in memory

    def test_delete_upload_with_server_exception(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload('f', 'r', 't', {'k': 'v'}, 'm')

        self.mock_upload_bindings.delete_upload.side_effect = NotFoundException({})

        # Test
        self.assertRaises(NotFoundException, self.upload_manager.delete_upload, upload_id)

        # Verify

        # Tracker should still be present both on disk and in memory
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        self.assertTrue(os.path.exists(tf_filename))

        self.assertTrue(self.upload_manager._get_tracker_file_by_id(upload_id) is not None)

    def test_delete_upload_with_server_exception_and_force(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload('f', 'r', 't', {'k': 'v'}, 'm')

        self.mock_upload_bindings.delete_upload.side_effect = NotFoundException({})

        # Test
        self.upload_manager.delete_upload(upload_id, force=True)

        # Verify
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        self.assertTrue(not os.path.exists(tf_filename))

        self.assertTrue(self.upload_manager._get_tracker_file_by_id(upload_id) is None)

    def test_delete_in_progress_upload(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload('f', 'r', 't', {'k': 'v'}, 'm')

        tracker = self.upload_manager._get_tracker_file_by_id(upload_id)
        tracker.is_running = True

        # Test
        self.assertRaises(upload_util.ConcurrentUploadException, self.upload_manager.delete_upload,
                          upload_id)

        # Verify
        tf_filename = self.upload_manager._tracker_filename(upload_id)
        self.assertTrue(os.path.exists(tf_filename))

        tracker = self.upload_manager._get_tracker_file_by_id(upload_id)
        self.assertTrue(tracker is not None)

    def test_import_upload(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload('f', 'r', 't', {'k': 'v'}, 'm')

        tracker = self.upload_manager._get_tracker_file_by_id(upload_id)
        tracker.is_finished_uploading = True  # simulate the upload completion

        # Test
        response = self.upload_manager.import_upload(upload_id)

        # Verify
        self.assertTrue(isinstance(response, Response))

        # Verify call to server
        self.assertEqual(1, self.mock_upload_bindings.import_upload.call_count)
        args = self.mock_upload_bindings.import_upload.call_args[0]
        self.assertEqual(args[0], upload_id)
        self.assertEqual(args[1], 'r')
        self.assertEqual(args[2], 't')
        self.assertEqual(args[3], {'k': 'v'})
        self.assertEqual(args[4], 'm')

    def test_import_upload_incomplete_upload(self):
        # Setup
        self.upload_manager.initialize()
        upload_id = self.upload_manager.initialize_upload('f', 'r', 't', {'k': 'v'}, 'm')

        # Test
        self.assertRaises(upload_util.IncompleteUploadException, self.upload_manager.import_upload,
                          upload_id)

        # Verify
        self.assertEqual(0, self.mock_upload_bindings.import_upload.call_count)

    def test_missing_upload_requests(self):
        # Setup
        self.upload_manager.initialize()

        # Test
        self.assertRaises(upload_util.MissingUploadRequestException, self.upload_manager.upload,
                          'i')
        self.assertRaises(upload_util.MissingUploadRequestException,
                          self.upload_manager.import_upload, 'i')
        self.assertRaises(upload_util.MissingUploadRequestException,
                          self.upload_manager.delete_upload, 'i')

    def _mock_initialize_upload(self):
        """
        Configures the mock bindings to return a valid upload ID.
        """
        body = {
            'upload_id': MOCK_UPLOAD_ID,
            '_href': MOCK_LOCATION,
        }
        self.mock_upload_bindings.initialize_upload.return_value = Response(201, body)

    def _mock_upload_segment(self):
        """
        Configures the mock bindings to return a valid response to uploading a segment.
        """
        self.mock_upload_bindings.upload_segment.return_value = Response(200, {})

    def _mock_delete_upload(self):
        """
        Configures the mock bindings to return a valid response to deleting an upload.
        """
        self.mock_upload_bindings.delete_upload.return_value = Response(200, {})

    def _mock_import_upload(self):
        """
        Configures the mock bindings to return a valid response on importing an upload.
        """
        self.mock_upload_bindings.import_upload.return_value = Response(200, {})
