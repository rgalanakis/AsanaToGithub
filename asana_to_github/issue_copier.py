from __future__ import print_function
from dateutil import parser as dtparser


def _parse_asana_stories(asana_api, task):
    """Read the Asana task's stories and return ````."""
    comments = []
    attachments = []
    created_by = ''
    all_stories = asana_api.list_stories(task['id'])
    for astory in all_stories:
        if astory['type'] == 'comment':
            the_time = dtparser.parse(astory['created_at'])
            the_time = the_time.strftime('%b-%d-%Y %H:%M %Z')
            comments.append("*{time}*: **{who}** wrote '{what}'".format(
                time=the_time,
                who=astory['created_by']['name'].encode('utf-8'),
                what=astory['text'].encode('utf-8').replace('\n', '')))
        if astory['type'] == 'system':
            if astory['text'][:9] == 'attached ':
                attachments.append('1. [Link to attachment]({})'.format(astory['text'][9:]))
            # Take the first 'Added to <project>' comment to see who created it.
            if astory['text'].startswith('added ') and not created_by:
                created_by = astory['created_by']['name']

    return {'comments': comments, 'attachments': attachments, 'created_by': created_by}


def _parse_asana_task(asana_api, task):
    """Parses an Asana task and returns
    ``{name: <>, url: <>, created_at: <>, description: <>, comments: [], attachments: [], created_by: <>}}``"""
    result = {
        'name': task['name'],
        'url': 'https://app.asana.com/0/{}/{}'.format(task['workspace']['id'], task['id']),
        'created_at': dtparser.parse(task['created_at']).strftime('%b-%d-%Y %H:%M %Z'),
        'description': task['notes'].encode('utf-8') or '*No description.*'
    }
    storydata = _parse_asana_stories(asana_api, task)
    result.update(storydata)
    return result


def create_github_issue(asana_api, task, git_repo, options):
    print('Creating issue for {}: {}'.format(task['id'], task['name'].encode('utf-8')))
    
    task_data = _parse_asana_task(asana_api, task)
    bodylines = [task_data['description']]
    if task_data['comments']:
        bodylines.append('\n### Comments\n')
        bodylines.extend(task_data['comments'])
    if task_data['attachments']:
        bodylines.append('\n### Attachments\n')
        bodylines.extend(task_data['attachments'])
    bodylines.append('\n### Meta\n')
    bodylines.append('[Asana task]({url}) was created by {who} at {when}'.format(
        url=task_data['url'], who=task_data['created_by'], when=task_data['created_at']))
    body = '\n'.join(bodylines)
    new_issue = git_repo.create_issue(task['name'], body)
    
    if not options.dont_update_story:
        story = 'This task can be seen at {}'.format('This task can be seen at ', new_issue.html_url.encode('utf-8'))
        print('Updating story of Asana item')
        asana_api.add_story(task['id'], story)
