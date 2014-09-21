from __future__ import print_function
from argparse import ArgumentParser
import sys

from asana import asana
from dateutil import parser as dtparser
from github import Github

import getch


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
        '--dont-apply-tag', action='store_true', dest='dont_apply_tag',
        help='every task copied to Github gets a tag copied-to-github at Asana. Use this switch to disable it.')
    parser.add_argument(
        '--dont-apply-label', action='store_true', dest='dont_apply_label',
        help='every issue copied to Github gets a label copied-from-asana at Github. Use this switch to disable it.')
    parser.add_argument(
        '--dont-apply-project-label', action='store_true', dest='dont_apply_project_label',
        help='Asana project name is applied as label to the copied task at Github. Use this switch to disable it.')
    parser.add_argument(
        '--dont-update-story', action='store_true', dest='dont_update_story',
        help='link of copied Github issues is added to Asana task story. Use this switch to disable it.')
    parser.add_argument(
        '--dont-copy-stories', action='store_true', dest='dont_copy_stories',
        help='Asana task stories are added as comment to the Github issue. Use this switch to disable it.')
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


def ask_user_permission(task):
    """Asks user permission to copy the task

    :Parameters:
        - `task`: Asana task object
    :Returns:
        True or False depending on the user response
    """

    print('Task title: {}'.format(task['name'].encode('utf-8')))
    print('URL: https://app.asana.com/0/{}/{}'.format(task['workspace']['id'], task['id']))
    user_input = None
    while user_input != 'y' and user_input != 'n':
        sys.stdout.write('Copy it to Github? [y/n] ')
        user_input = getch.getch()
    sys.stdout.write(user_input + '\n')
    return user_input == 'y'


def get_or_create_label(git_repo, label_name, label_color='FFFFFF'):
    """Returns instance of Label() or None

    :Parameter:
        - `git-repo` : repository at Github to whose issues tracker issues will be copied
        - `label_name`: Name of the label. Type string
    """
    try:
        label = git_repo.get_label(label_name.encode('utf-8'))
    except Exception:
        label = git_repo.create_label(label_name, label_color)
    return label


def apply_tag_at_asana(asana_api, tag_title, workspace_id, task_id):
    """Applies a tag to task

    :Parameters:
        - `asana_api`: an instance of Asana
        - `tag_title`: name of the tag. Type string.
        - `workspace_id`: id of the workspace in which tag is created
        - `task_id`: id of the task on which tag is applied
    """

    tag_id = None
    all_tags = asana_api.get_tags(workspace_id)
    for atag in all_tags:
        if atag['name'] == tag_title:
            tag_id = atag['id']
            break
    if not tag_id:
        new_tag = asana_api.create_tag(tag_title, workspace_id)
        tag_id = new_tag['id']

    asana_api.add_tag_task(task_id, tag_id)


def copy_stories_to_github(asana_api, task_id, issue):
    """Copy task story from Asana to Github

    :Parameters:
        - `asana_api`: an instance of Asana
        - `task_id`: task id
        - `issue`: instance of class Issue to which comments are added
    """

    comment = ''
    attachment = ''
    all_stories = asana_api.list_stories(task_id)
    for astory in all_stories:
        if astory['type'] == 'comment':
            the_time = dtparser.parse(astory['created_at'])
            the_time = the_time.strftime('%b-%d-%Y %H:%M %Z')
            comment = comment + """*{}*: **{}** wrote '{}'\n""".format(
                the_time, astory['created_by']['name'].encode('utf-8'),
                astory['text'].encode('utf-8').replace('\n', ''))
        if astory['type'] == 'system' and astory['text'][:9] == 'attached ':
            attachment = attachment + '1. [Link to attachment]({})\n'.format(astory['text'][9:])

    if comment:
        comment = '### Comments\n' + comment
    if attachment:
        attachment = '### Attachments\n' + attachment
    if comment or attachment:
        final_comment = attachment + '\n' + comment
        issue.create_comment(final_comment)


def copy_task_to_github(asana_api, task, git_repo, options):
    """Copy tasks from Asana to Github

    :Parameters:
        - `asana_api`: an instance of Asana
        - `a_task`: Asana task object
        - `task_id`: task id
        - `git_repo`: repository at Github to whose issues tracker issues will be copied
        - `options`: options parsed by OptionParser
    """

    labels = []
    if not options.dont_apply_label:
        a_label = get_or_create_label(git_repo, 'copied-from-asana')
        labels.append(a_label)
    if not options.dont_apply_project_label:
        for project in task['projects']:
            a_label = get_or_create_label(git_repo, project['name'])
            labels.append(a_label)
    print('Creating issue: {}'.format(task['name'].encode('utf-8')))
    meta = '#### Meta\n[Asana task](https://app.asana.com/0/{}/{}) was created at {}.'.format(
        task['workspace']['id'], task['id'], dtparser.parse(task['created_at']).strftime('%b-%d-%Y %H:%M %Z'))
    if task['due_on']:
        meta = meta + ' It is due on {}.'.format(dtparser.parse(task['due_on']).strftime('%b-%d-%Y'))
    body = task['notes'].encode('utf-8') + '\n' + meta
    new_issue = git_repo.create_issue(task['name'], body, labels=labels)

    # Add stories to Github
    if not options.dont_copy_stories:
        print('Copying stories to Github')
        copy_stories_to_github(asana_api, task['id'], new_issue)

    # Update Asana
    if not options.dont_apply_tag:
        print('Applying tag to Asana item')
        apply_tag_at_asana(asana_api, 'copied to github', task['workspace']['id'], task['id'])
    if not options.dont_update_story:
        story = '{}{}'.format('This task can be seen at ', new_issue.html_url.encode('utf-8'))
        print('Updating story of Asana item')
        asana_api.add_story(task['id'], story)


def migrate_asana_to_github(asana_api, project_id, git_repo, options):
    """Manages copying of tasks from Asana to Github issues

    :Parameters:
        - `asana_api`: an instance of Asana
        - `project_id`: project id whose tasks are to be copied
        - `git_repo`: repository at Github to whose issues tracker issues will be copied
        - `options`: options parsed by OptionParser
    """

    print('Fetching tasks from Asana')
    all_tasks = asana_api.get_project_tasks(project_id)

    if not all_tasks:
        print('{}/{} does not have any task in it'.format(options.workspace, options.project))
        return

    for a_task in all_tasks:
        task = asana_api.get_task(a_task['id'])
        # Filter completed and incomplete tasks. Copy if task is incomplete or even completed tasks are to be copied
        if not task['name'].endswith(':') and (options.copy_completed or not task['completed']):
            if options.interactive:
                should_copy = ask_user_permission(task)
            else:
                should_copy = True
            if should_copy:
                copy_task_to_github(asana_api, task, git_repo, options)
            else:
                print('Task skipped.')


def main():
    options = parse()
    asana_api = asana.AsanaAPI(options.asana_api_key, debug=options.verbose)
    github_api = Github(options.username, options.password)

    git_repo = github_api.get_repo(options.repo)

    migrate_asana_to_github(asana_api, options.projectid, git_repo, options)

    exit(0)


if __name__ == '__main__':
    main()
