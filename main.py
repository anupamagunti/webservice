from flask import Flask, request, abort
import requests
import os
import pdb
import logging

import jinja2
from jinja2.environment import Template

app = Flask(__name__)

base_bitbucket_url = os.environ['BITBUCKETURL']
bitbucket_api_token = os.environ['BITBUCKETAPITOKEN']
#base_bitbucket_url = "https://git.transunion.com"
#base_bitbucket_url = "https://git.com"
#bitbucket_api_token = "NDA2MDMyMzU1NjM4OhT3EtV1PQ9/R1v2ZCkbczZynwhS"
#bitbucket_api_token = "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"

if base_bitbucket_url is None or base_bitbucket_url == '':
    Exception('You must provide the base bitbucket url as an environmental variable.')
if bitbucket_api_token is None or bitbucket_api_token == '':
    Exception('You must provide a bitbucket api token as an environmental variable.')

base_bitbucket_api_url = f'{base_bitbucket_url}/rest/api/1.0'
#base_bitbucket_api_url = f'{base_bitbucket_url}'
bitbucket_headers = {"Authorization": f"Bearer {bitbucket_api_token}", "X-Atlassian-Token": "no-check"}


@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.get_json()

    bot_slug = requests.get(url=f'{base_bitbucket_url}/plugins/servlet/applinks/whoami', headers=bitbucket_headers).text
    project = data.get('pullRequest', {}).get('toRef').get('repository').get('project').get('key')
    repo = data.get('pullRequest', {}).get('toRef').get('repository').get('name')
    pr_id = data.get('pullRequest', {}).get('id')
    pr_version = data.get('pullRequest', {}).get('version')
    author_name = data.get("pullRequest", {}).get("author").get("user").get("name")
    author_display_name = data.get("pullRequest", {}).get("author").get("user").get("displayName")
    actor_display_name = data.get('actor', {}).get('displayName')
    src_ref_id = data.get('pullRequest', {}).get('fromRef').get('id')
    src_repo_id = data.get('pullRequest', {}).get('fromRef').get('repository').get('id')
    target_ref_id = data.get('pullRequest', {}).get('toRef').get('id')
    target_repo_id = data.get('pullRequest', {}).get('toRef').get('repository').get('id')
    target_branch = data.get('pullRequest', {}).get('toRef').get('displayId')
    base_pr_url = f'{base_bitbucket_api_url}/projects/{project}/repos/{repo}/pull-requests/{pr_id}'

    def is_pr_mergable(base_pr_url, headers):

        merge_status_url = f'{base_pr_url}/merge'
        merge_status = requests.get(merge_status_url, headers=headers).json()

        if merge_status.get('canMerge') is True and not merge_status.get('conflicted') and \
                merge_status.get('outcome') == 'CLEAN':
            app.logger.debug('PR is mergable, returning True')
            return True
        else:
            return False

    def approve_pr(base_pr_url, headers, slug):

        approval_url = f'{base_pr_url}/participants/{slug}'
        json_body = {'status': 'APPROVED'}
        r = requests.put(url=approval_url, headers=headers, json=json_body)

        return r

    def merge_pr(base_pr_url, pr_version, headers):

        merge_url = f'{base_pr_url}/merge?version={pr_version}'
        r = requests.post(url=merge_url, headers=headers)
        return r

    if data.get('eventKey', {}) == 'pr:comment:added':
        
        comment_text = data.get('comment', {}).get('text')
        print(f"comment_text = @{comment_text}")
        if comment_text.strip().casefold() == '/approve'.casefold():
            r = approve_pr(base_pr_url=base_pr_url, headers=bitbucket_headers, slug=bot_slug)
            is_mergable = is_pr_mergable(base_pr_url=base_pr_url, headers=bitbucket_headers)
            if is_mergable:
                merge_pr(base_pr_url=base_pr_url, pr_version=pr_version, headers=bitbucket_headers)


    return ('', 200, None)


if __name__ == '__main__':
    app.run(port=9080, debug=True)
