"""
Some vocabulary:

- ``task`` is an Asana API task object.
- ``git_repo`` is a Github API repo object.
- ``options`` are the parsed options.
"""

from __future__ import print_function
from argparse import ArgumentParser
import sys

from asana import asana
from github import Github

import getch
import issue_copier
import taskcache


def parse():
    parser = ArgumentParser()
    parser.add_argument('-u', '--username', help='GitHub username.')
    parser.add_argument('-p', '--password', help='GitHub password')
    parser.add_argument('-a', '--asana-api-key', dest='asana_api_key', help='Asana API Key.')
    parser.add_argument(
        '-P', '--projectid', type=int,
        help='PROJECT ID which has the items you want to copy to Github.')
    parser.add_argument(
        '-r', '--repo',
        help='Github REPOsitory name to whose issue tracker you want to copy Asana tasks.')
    parser.add_argument(
        '-i', '--interactive', action='store_true',
        help='request confirmation before attempting to copy each task to Github')
    parser.add_argument(
        '--copy-completed-tasks', action='store_true', dest='copy_completed',
        help='completed Asana tasks are not copied. Use this switch to force copy of completed tasks.')
    parser.add_argument(
        '--dont-update-story', action='store_true', dest='dont_update_story',
        help='link of copied Github issues is added to Asana task story. Use this switch to disable it.')
    parser.add_argument(
        '--use-cache', action='store_true', dest='use_cache',
        help='If provided, use a cache file so the same Asana tasks are not processed over and over.'
    )
    parser.add_argument(
        '--cache-path', dest='cache_path', default='.asanagh.cache',
        help='If --use-cache, this is the path the cache will be saved to. [default: %(default)s]'
    )
    parser.add_argument('-v', '--verbose', action='store_true')

    def read_config():
        try:
            with open('.asanaghrc') as f:
                return [line.strip() for line in f.readlines() if (line.strip() and not line.startswith('#'))]
        except IOError:
            return []

    argv = sys.argv[1:] + read_config()
    options = parser.parse_args(argv)

    if not options.asana_api_key:
        parser.error('Asana API Key is required')
    if not options.username:
        parser.error('Github username is required')
    if not options.password:
        parser.error('Github password is required')

    return options


def ask_user_permission(task, reponame):
    """Asks user permission to copy the task.

    :return: True or False depending on the user response.
    """

    print('Task title: {}'.format(task['name'].encode('utf-8')))
    print('URL: https://app.asana.com/0/{}/{}'.format(task['workspace']['id'], task['id']))
    user_input = None
    while user_input != 'y' and user_input != 'n':
        sys.stdout.write('Copy it to %s? [y/n] ' % reponame)
        user_input = getch.getch()
    sys.stdout.write(user_input + '\n')
    return user_input == 'y'


def could_copy(simple_task, cache):
    """Return True if the task should potentially be copied
    (based on name and cache state).
    """
    if simple_task['name'].endswith(':'):
        return False
    return not cache.includes(simple_task)


def migrate_asana_to_github(asana_api, project_id, git_repo, options):
    """Manages copying of tasks from Asana to Github issues."""
    cache = taskcache.TaskCache(options.use_cache, options.cache_path)
    print('Fetching tasks from Asana')
    all_tasks = asana_api.get_project_tasks(project_id)
    all_tasks = [t for t in all_tasks if could_copy(t, cache)]

    for a_task in all_tasks:
        task = asana_api.get_task(a_task['id'])
        should_set_in_cache = True
        # Filter completed and incomplete tasks. Copy if task is incomplete or even completed tasks are to be copied
        if options.copy_completed or not task['completed']:
            should_copy = True
            if options.interactive:
                should_copy = ask_user_permission(task, options.repo)
            if should_copy:
                issue_copier.create_github_issue(asana_api, task, git_repo, options)
            else:
                should_set_in_cache = False
                print('Task skipped.')
        if should_set_in_cache:
            cache.set(task)


def main():
    options = parse()
    asana_api = asana.AsanaAPI(options.asana_api_key, debug=options.verbose)
    github_api = Github(options.username, options.password)
    git_repo = github_api.get_repo(options.repo)
    migrate_asana_to_github(asana_api, options.projectid, git_repo, options)


if __name__ == '__main__':
    main()
