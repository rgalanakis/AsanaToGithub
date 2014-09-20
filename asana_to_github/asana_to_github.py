from __future__ import print_function
from argparse import ArgumentParser

from asana import asana
from dateutil import parser as dtparser
from github import Github


def parse():
    """Returns OptionParser instance to parse the command line parameters"""

    parser = ArgumentParser()
    parser.add_argument('-u', '--username', help='GitHub username.')
    parser.add_argument('-p', '--password', help='GitHub password')
    parser.add_argument('-a', '--asana-api-key', dest='asana_api_key', help='Asana API Key.')
    parser.add_argument(
        '-w', '--workspace',
        help='WORKSPACE name which has the project you want to copy to Github. '
             'If none is specified a list of available workspaces is printed.')
    parser.add_argument(
        '-P', '--project',
        help='PROJECT name which has the items you want to copy to Github. '
             'If none is specified a list of available projects is printed.')
    parser.add_argument(
        '-r', '--repo',
        help='Github REPOsitory name to whose issue tracker you want to copy Asana tasks. '
             'If none is specified a list of available repositories is printed.')
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
    return parser


def print_workspaces(asana_api_object):
    """Prints a list of available workspaces on stdout
    
    :Parameter:
        - `asana_api_object`: an instance of Asana
    """

    my_spaces = asana_api_object.list_workspaces()
    print('Following Asana workspaces are available:')
    for item in my_spaces:
        print(item['name'])


def get_workspace_id(asana_api_object, workspace):
    """Returns id of the workspace

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `workspace`: name or id of the workspace
    """

    my_spaces = asana_api_object.list_workspaces()
    w_id = None
    for item in my_spaces:
        if item['name'].encode('utf-8') == workspace or item['id'] == workspace:
            w_id = item['id']
            break
    return w_id


def print_projects(asana_api_object, workspace_id):
    """Prints a list of available projects in the workspace on stdout
    
    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `workspace_id`: id of the workspace whose projects are to be listed
    """

    my_projects = asana_api_object.list_projects(workspace_id)
    print('Following projects are available in it:')
    for item in my_projects:
        print(item['name'])


def get_project_id(asana_api_object, workspace_id, project):
    """Returns id of the project 
    
    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `workspace_id`: id of the workspace that has the project
        - `project`: name of id of the project
    """

    my_projects = asana_api_object.list_projects(workspace_id)
    p_id = None
    for item in my_projects:
        if item['name'].encode('utf-8') == project or item['id'] == project:
            p_id = item['id']
            break
    return p_id


def get_tasks(asana_api_object, project_id):
    """Returns all the tasks present in the project
    
    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `project_id`: id of the project whose tasks are to be fetched
    """

    return asana_api_object.get_project_tasks(project_id)


def get_project_id_from_asana(asana_api_object, options):
    """Returns project id and handle cases when workspace or project is not specified at command line

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `options`: options parsed by OptionParser
    """

    project_id = None
    if not options.workspace:
        print_workspaces(asana_api_object)
    else:
        workspace_id = get_workspace_id(asana_api_object, options.workspace)
        if not workspace_id:
            print('Workspace not found. Make sure you have entered correct workspace name.')
        else:
            print('Workspace {} found'.format(options.workspace))
            if not options.project:
                print_projects(asana_api_object, workspace_id)
            else:
                project_id = get_project_id(asana_api_object, workspace_id, options.project)
                if not project_id:
                    print('Project not found. Make sure you have entered correct project name.')
                else:
                    print('Project {} found'.format(options.project))
    return project_id


def print_repos(github_api_object):
    """Prints a list of available repos on stdout
    
    :Parameter:
        - `github_api_object`: an instance of Github
    """

    my_repos = github_api_object.get_user().get_repos()
    print('Following Github repositories are available:')
    for item in my_repos:
        print(item.full_name)


def get_repo(github_api_object, repo_full_name):
    """Return an instance of repo
    
    :Parameters:
        - `github_api_object`: an instance of Github
        - `repo_full_name`: full name of the repo on Github, for example, talha131/try
    """

    my_repos = github_api_object.get_user().get_repos()
    my_repo = None
    for item in my_repos:
        if item.full_name == repo_full_name:
            my_repo = item
            break
    return my_repo


def get_repo_from_github(github_api_object, options):
    """Return an instance of repo and handle cases when repo is not specified or is invalid
    
    :Parameters:
        - `github_api_object`: an instance of Github
        - `options`: options parsed by OptionParser
    """

    my_repo = None
    if not options.repo:
        print_repos(github_api_object)
    else:
        my_repo = get_repo(github_api_object, options.repo)
        if not my_repo:
            print('Repository not found. Make sure you have entered complete repository name correctly.')
        else:
            print('Repository {} found.'.format(options.repo))
            if not my_repo.has_issues:
                print ('Issues tracker is disabled for this repo. '
                       'Make sure you have enabled it in the repository settings at Github.')
                my_repo = None
            else:
                print('Issue tracker is enabled')
    return my_repo


def ask_user_permission(a_task, task_id):
    """Asks user permission to copy the task

    :Parameters:
        - `a_task`: Asana task object
        - `task_id`: task id
    :Returns:
        True or False depending on the user response
    """

    print('Task title: {}'.format(a_task['name'].encode('utf-8')))
    print('URL: https://app.asana.com/0/{}/{}'.format(a_task['workspace']['id'], task_id))
    user_input = None
    while user_input is not 'y' and user_input is not 'n':
        user_input = raw_input('Copy it to Github [y/n]')
    return True if user_input == 'y' else False


def get_label(git_repo, label_name):
    """Returns instance of Label() or None

    :Parameter:
        - `git-repo` : repository at Github to whose issues tracker issues will be copied
        - `label_name`: Name of the label. Type string
    """

    try:
        label = git_repo.get_label(label_name.encode('utf-8'))
    except Exception:
        label = None

    return label


def apply_tag_at_asana(asana_api_object, tag_title, workspace_id, task_id):
    """Applies a tag to task

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `tag_title`: name of the tag. Type string.
        - `workspace_id`: id of the workspace in which tag is created
        - `task_id`: id of the task on which tag is applied
    """

    tag_id = None
    all_tags = asana_api_object.get_tags(workspace_id)
    for atag in all_tags:
        if atag['name'] == tag_title:
            tag_id = atag['id']
            break
    if not tag_id:
        new_tag = asana_api_object.create_tag(tag_title, workspace_id)
        tag_id = new_tag['id']

    asana_api_object.add_tag_task(task_id, tag_id)


def add_story_to_assana(asana_api_object, task_id, text):
    """Adds a new story to the task

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `task_id`: task id
        - `text`: story
    """

    asana_api_object.add_story(task_id, text)


def copy_stories_to_github(asana_api_object, task_id, issue):
    """Copy task story from Asana to Github

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `task_id`: task id
        - `issue`: instance of class Issue to which comments are added
    """

    comment = ''
    attachment = ''
    all_stories = asana_api_object.list_stories(task_id)
    for astory in all_stories:
        if astory['type'] == 'comment':
            the_time = dtparser.parse(astory['created_at'])
            the_time = the_time.strftime('%b-%d-%Y %H:%M %Z')
            comment = comment + """*{}*: **{}** wrote '{}'\n""".format(
                the_time, astory['created_by']['name'].encode('utf-8'),
                astory['text'].encode('utf-8').replace('\n', ''))
        if astory['type'] == 'system' and astory['text'][:9] == 'attached ':
            attachment = attachment + '1. [Link to attachment]({})\n'.format(astory['text'][9:])

    if len(comment) > 0:
        comment = '### Comments\n' + comment
    if len(attachment) > 0:
        attachment = '### Attachments\n' + attachment
    if len(comment) > 0 or len(attachment) > 0:
        final_comment = attachment + '\n' + comment
        issue.create_comment(final_comment)


def copy_task_to_github(asana_api_object, task, task_id, git_repo, options):
    """Copy tasks from Asana to Github

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `a_task`: Asana task object
        - `task_id`: task id
        - `git_repo`: repository at Github to whose issues tracker issues will be copied
        - `options`: options parsed by OptionParser
    """

    labels = []
    if not options.dont_apply_label:
        a_label = get_label(git_repo, 'copied-from-asana')
        if not a_label:
            a_label = git_repo.create_label('copied-from-asana', 'FFFFFF')
        labels.append(a_label)
    if not options.dont_apply_project_label:
        for project in task['projects']:
            a_label = get_label(git_repo, project['name'])
            if not a_label:
                a_label = git_repo.create_label(project['name'], 'FFFFFF')
            labels.append(a_label)
    print('Creating issue: {}'.format(task['name'].encode('utf-8')))
    meta = '### Meta\n[Asana task](https://app.asana.com/0/{}/{}) was created at {}.'.format(
        task['workspace']['id'], task_id, dtparser.parse(task['created_at']).strftime('%b-%d-%Y %H:%M %Z'))
    if task['due_on']:
        meta = meta + ' It is due on {}.'.format(dtparser.parse(task['due_on']).strftime('%b-%d-%Y'))
    body = task['notes'].encode('utf-8') + '\n' + meta
    new_issue = git_repo.create_issue(task['name'], body, labels=labels)

    """Add stories to Github"""
    if not options.dont_copy_stories:
        print('Copying stories to Github')
        copy_stories_to_github(asana_api_object, task_id, new_issue)

    """Update Asana"""
    if not options.dont_apply_tag:
        print('Applying tag to Asana item')
        apply_tag_at_asana(asana_api_object, 'copied to github', task['workspace']['id'], task_id)
    if not options.dont_update_story:
        story = '{}{}'.format('This task can be seen at ', new_issue.html_url.encode('utf-8'))
        print('Updating story of Asana item')
        add_story_to_assana(asana_api_object, task_id, story)


def migrate_asana_to_github(asana_api_object, project_id, git_repo, options):
    """Manages copying of tasks from Asana to Github issues

    :Parameters:
        - `asana_api_object`: an instance of Asana
        - `project_id`: project id whose tasks are to be copied
        - `git_repo`: repository at Github to whose issues tracker issues will be copied
        - `options`: options parsed by OptionParser
    """

    print('Fetching tasks from Asana')
    all_tasks = get_tasks(asana_api_object, project_id)

    if len(all_tasks) == 0:
        print('{}/{} does not have any task in it'.format(options.workspace, options.project))
        return

    for a_task in all_tasks:
        task = asana_api_object.get_task(a_task['id'])
        # Filter completed and incomplete tasks. Copy if task is incomplete or even completed tasks are to be copied
        if not task['completed'] or options.copy_completed:
            if options.interactive:
                should_copy = ask_user_permission(task, a_task['id'])
            else:
                should_copy = True
            if should_copy:
                copy_task_to_github(asana_api_object, task, a_task['id'], git_repo, options)
            else:
                print('Task skipped.')


def main():
    parser = parse()
    options = parser.parse_args()

    if not options.asana_api_key:
        parser.error('Asana API Key is required')
    if not options.username:
        parser.error('Github username is required')
    if not options.password:
        parser.error('Github password is required')

    asana_api = asana.AsanaAPI(options.asana_api_key, debug=options.verbose)
    project_id = get_project_id_from_asana(asana_api, options)
    if not project_id:
        exit(1)

    github_api = Github(options.username, options.password)
    git_repo = get_repo_from_github(github_api, options)
    if not git_repo:
        exit(1)

    migrate_asana_to_github(asana_api, project_id, git_repo, options)

    exit(0)


if __name__ == '__main__':
    main()
