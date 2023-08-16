"""Unit tests for git-like commands of ingit."""

import collections
import logging
import os
import pathlib
import platform
import tempfile
import unittest
import unittest.mock

import git
import readchar

from ingit.main import main

HERE = pathlib.Path(__file__).resolve().parent

TEST_RUNTIME_CONFIG_PATH = pathlib.Path(HERE, 'examples', 'runtime_config', 'example_initial.json')
TEST_REPOS_CONFIG_PATH = pathlib.Path(HERE, 'examples', 'repos_config', 'example_initial.json')

PROJECT_NAMES = ('argunparse', 'transpyle', 'typed-astunparse')
PROJECT_NAME = PROJECT_NAMES[0]

_LOG = logging.getLogger(__name__)


def call_main(*args, answer='y'):
    with unittest.mock.patch.object(readchar, 'readchar', return_value=answer), \
            unittest.mock.patch.dict(os.environ, {
                'EXAMPLE_PROJECTS_PATH': os.environ.get('EXAMPLE_PROJECTS_PATH', '..')}):
        main(['--config', str(TEST_RUNTIME_CONFIG_PATH), '--repos', str(TEST_REPOS_CONFIG_PATH)]
             + list(args))


class Tests(unittest.TestCase):

    def setUp(self):
        assert 'INGIT_TEST_REPOS_PATH' not in os.environ
        self._tmpdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        os.environ['INGIT_TEST_REPOS_PATH'] = self._tmpdir.name
        _LOG.warning('set INGIT_TEST_REPOS_PATH="%s"', self._tmpdir.name)
        self.repos_path = pathlib.Path(self._tmpdir.name)

    def tearDown(self):
        if platform.system() != 'Windows':
            self._tmpdir.cleanup()
        del os.environ['INGIT_TEST_REPOS_PATH']

    def test_clone(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            self.assertFalse(repo_path.is_dir())
            call_main('-p', f'name == "{project_name}"', 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_clone_no(self):
        repo_path = pathlib.Path(self.repos_path, PROJECT_NAME)
        call_main('-p', f'name == "{PROJECT_NAME}"', 'clone', answer='n')
        self.assertFalse(repo_path.is_dir())

    def test_clone_to_repo_dir(self):
        repo_path = pathlib.Path(self.repos_path, PROJECT_NAME)
        call_main('-p', f'name == "{PROJECT_NAME}"', 'clone')
        self.assertTrue(repo_path.is_dir())
        self.assertTrue(repo_path.joinpath('.git').is_dir())
        call_main('-r', f'^{PROJECT_NAME}$', 'clone')

    def test_clone_to_nonempty_dir(self):
        repo_path = pathlib.Path(self.repos_path, PROJECT_NAME)
        repo_path.mkdir()
        repo_path.joinpath('file.txt').touch()
        with self.assertLogs(
                logger=logging.getLogger('ingit.interface.print'), level=logging.CRITICAL):
            call_main('-p', f'name == "{PROJECT_NAME}"', 'clone')
        self.assertTrue(repo_path.is_dir())

    # def test_clone_with_multiple_remotes(self):

    def test_init(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            self.assertFalse(repo_path.is_dir())
            call_main('-p', f'name == "{project_name}"', 'init')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_init_in_repo_dir(self):
        repo_path = pathlib.Path(self.repos_path, PROJECT_NAME)
        call_main('-p', f'name == "{PROJECT_NAME}"', 'clone')
        self.assertTrue(repo_path.is_dir())
        self.assertTrue(repo_path.joinpath('.git').is_dir())
        call_main('-p', f'name == "{PROJECT_NAME}"', 'init')

    def test_init_no(self):
        project_name = PROJECT_NAMES[0]
        call_main('-p', f'name == "{project_name}"', 'init')
        project_name = PROJECT_NAMES[1]
        repo_path = pathlib.Path(self.repos_path, project_name)
        call_main('-p', f'name == "{project_name}"', 'init', answer='n')
        self.assertFalse(repo_path.is_dir())

    def test_fetch(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', f'name == "{project_name}"', 'init')
            call_main('-p', f'name == "{project_name}"', 'fetch')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_fetch_all(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', f'name == "{project_name}"', 'init')
            call_main('-p', f'name == "{project_name}"', 'fetch', '--all')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_checkout_detached(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            self.assertFalse(repo_path.is_dir())
            call_main('-p', f'name == "{project_name}"', 'clone')
            self.assertTrue(repo_path.is_dir())
            repo = git.Repo(str(repo_path))
            head_ref = repo.head.commit.hexsha
            initial_commit = collections.deque(repo.iter_commits(), maxlen=1).pop()
            initial_ref = initial_commit.hexsha
            repo.git.checkout(initial_ref)
            call_main('-p', f'name == "{project_name}"', 'checkout', answer='n')
            self.assertEqual(repo.head.commit.hexsha, initial_ref)
            call_main('-p', f'name == "{project_name}"', 'checkout', answer='1')
            self.assertEqual(repo.head.commit.hexsha, head_ref)

    def test_checkout(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', f'name == "{project_name}"', 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())
            call_main('-p', f'name == "{project_name}"', 'checkout', answer='n')

    @unittest.expectedFailure
    def test_checkout_conflicting(self):
        """Checkout remote branch for which there already exists local branch having a different
        tracking branch, which will result in detached head.
        """
        # project_name = 'argunparse'
        self.fail()

    # def test_merge(self):
    #     for project_name in PROJECT_NAMES:
    #         repo_path = pathlib.Path(self.repos_path, project_name)
    #         call_main('-p', f'name == "{project_name}"', 'init')
    #         self.assertTrue(repo_path.is_dir())
    #         call_main('-p', f'name == "{project_name}"', 'merge')

    def test_push(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', f'name == "{project_name}"', 'init')
            self.assertTrue(repo_path.is_dir())
            call_main('-p', f'name == "{project_name}"', 'push')
            self.assertTrue(repo_path.is_dir())

    def test_gc(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', f'name == "{project_name}"', 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())
            call_main('-p', f'name == "{project_name}"', 'gc')

    def test_status(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', f'name == "{project_name}"', 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())
            call_main('-p', f'name == "{project_name}"', 'status', answer='n')

    def test_skip_nonexisting(self):
        for command in ('fetch', 'checkout', 'merge', 'push', 'gc', 'status'):
            repo_path = pathlib.Path(self.repos_path, PROJECT_NAME)
            self.assertFalse(repo_path.is_dir())
            call_main('-p', f'name == "{PROJECT_NAME}"', command)
            self.assertFalse(repo_path.is_dir())
