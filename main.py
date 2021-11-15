from flask import Flask, request, abort
import requests
import os
import pdb

app = Flask(__name__)

#base_bitbucket_url = os.environ['BITBUCKETURL']
#bitbucket_api_token = os.environ['BITBUCKETAPITOKEN']
#base_bitbucket_url = "https://git.transunion.com"
base_bitbucket_url = "https://git.com"
#bitbucket_api_token = "NDA2MDMyMzU1NjM4OhT3EtV1PQ9/R1v2ZCkbczZynwhS"
bitbucket_api_token = "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"

if base_bitbucket_url is None or base_bitbucket_url == '':
    Exception('You must provide the base bitbucket url as an environmental variable.')
if bitbucket_api_token is None or bitbucket_api_token == '':
    Exception('You must provide a bitbucket api token as an environmental variable.')

base_bitbucket_api_url = f'{base_bitbucket_url}/rest/api/1.0'
#base_bitbucket_api_url = f'{base_bitbucket_url}'
bitbucket_headers = {"Authorization": f"Bearer {bitbucket_api_token}", "X-Atlassian-Token": "no-check"}


@app.route('/webhook', methods=['POST'])
def parse_webhook():

    data = request.get_json()

    if data.get('pullRequest', {}).get('toRef').get('repository').get('name') != 'playbook-common':
        return "Event not relevant."

    project = data.get('pullRequest', {}).get('toRef').get('repository').get('project').get('key')
    repo = data.get('pullRequest', {}).get('toRef').get('repository').get('name')
    pr_id = data.get('pullRequest', {}).get('id')
    author_name = data.get("pullRequest", {}).get("author").get("user").get("name")
    src_ref_id = data.get('pullRequest', {}).get('fromRef').get('id')
    src_repo_id = data.get('pullRequest', {}).get('fromRef').get('repository').get('id')
    target_ref_id = data.get('pullRequest', {}).get('toRef').get('id')
    target_repo_id = data.get('pullRequest', {}).get('toRef').get('repository').get('id')

    base_pr_url = f'{base_bitbucket_api_url}/projects/{project}/repos/{repo}/pull-requests/{pr_id}'

    if data.get('eventKey', {}) == 'pr:reviewer:approved':

        merge_status_url = f'{base_pr_url}/merge'
        merge_status = requests.get(merge_status_url, headers=bitbucket_headers).json()

        if merge_status.get('canMerge') is True and not merge_status.get('conflicted') and \
                merge_status.get('outcome') == 'CLEAN':

            comment_text = {"text": f"@{author_name} Your PR is ready to be merged."}
            r = requests.post(url=f'{base_pr_url}/comments', headers=bitbucket_headers, json=comment_text)

    if data.get('eventKey', {}) == 'pr:reviewer:updated':

        removedReviewers = data.get('removedReviewers')
        if removedReviewers:

            reviewers_api_url = f'{base_bitbucket_url}/rest/default-reviewers/1.0/projects/{project}/repos/' \
                                f'{repo}/reviewers'
            reviewers_params = {'sourceRepoId': src_repo_id, 'targetRepoId': target_repo_id, 'sourceRefId': src_ref_id,
                                'targetRefId': target_ref_id}
            default_reviewers = requests.get(url=reviewers_api_url, params=reviewers_params, headers=bitbucket_headers)
            removed_list = []
            for reviewer in removedReviewers:
                for default_reviewer in default_reviewers.json():
                    if reviewer.get('name') == default_reviewer.get('name'):
                        removed_list.append(reviewer.get('displayName'))

            if len(removed_list) > 0:

                users_string = [f'* {x}' for x in removed_list]
                users_join = '\n'.join(users_string)
                comment = \
                    "@%s\nYou have removed the default user(s):\n%s\n\nYou are free to add additional approvers " \
                    "but approval is required from at least one default reviewer. In order to expedite approval " \
                    "of your request we ask that you do not remove any default reviewers." % (author_name, users_join)
                comment_text = {"text": f"{comment}"}

                r = requests.post(url=f'{base_pr_url}/comments', headers=bitbucket_headers, json=comment_text)

    return ('', 200, None)


if __name__ == '__main__':
    app.run(port=7999)
