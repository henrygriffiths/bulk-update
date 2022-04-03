import os
import shutil
import subprocess
import json
import requests
import sys
import time

if len(sys.argv) > 1:
    configfilename = sys.argv[1]
else:
    configfilename = 'config.json'

with open(configfilename) as json_file:
    config = json.load(json_file)

sleeptime = 5*60
first = True

def run(args, returnoutput = False):
    while True:
        try:
            sp = subprocess.run(args, text = True, check = True, capture_output = returnoutput)
            if returnoutput:
                print(sp.stdout)
            return sp.stdout
        except:
            while True:
                print('Running {} Failed.'.format(' '.join(args)))
                result = input('(R)etry or (C)ontinue? : ')
                if result.lower() == 'r':
                    break
                elif result.lower() == 'c':
                    try:
                        return sp.stderr
                    except:
                        print('FAILED TO RETURN ERROR')
                        return


os.chdir('{}/{}'.format(os.getcwd(), 'repos'))
for repository_dict in config['repositories']:
    if not first:
        print('Sleeping')
        time.sleep(sleeptime)
    else:
        first = False
    repository = repository_dict['repository']
    source_branch = repository_dict['source_branch']
    dest_branch = '{}-{}'.format(config['dest_branch'], source_branch)
    org = repository.split('/')[0]
    repo = repository.split('/')[1]
    if not os.path.exists('{}/{}'.format(os.getcwd(), org)):
        os.makedirs('{}/{}'.format(os.getcwd(), org))
    os.chdir('{}/{}'.format(os.getcwd(), org))
    if os.path.exists('{}/{}'.format(os.getcwd(), repo)):
        os.chdir('{}/{}'.format(os.getcwd(), repo))
        # run(['git', 'clean', '-fd'])
        run(['git', 'reset', '--hard', 'HEAD'])
        # run(['git', 'checkout', 'origin/{}'.format(source_branch)])
        # run(['git', 'branch', '-D', source_branch])
        # run(['git', 'checkout', '-b', source_branch])
    else:
        run(['rm', '-rf', repo])
        if config['shallowclone'] == True:
            run(['git', 'clone', '--depth', '1', 'https://github.com/{}/{}.git'.format(org, repo)])
        else:
            run(['git', 'clone', 'https://github.com/{}/{}.git'.format(org, repo)])
        os.chdir('{}/{}'.format(os.getcwd(), repo))
    if config['shallowclone'] == True and config['existingbranch'] == True:
        run(['git', 'config', '--add', 'remote.origin.fetch', '+refs/heads/{}:refs/remotes/origin/{}'.format(dest_branch, dest_branch)])
    if 'repoprune' in config and config['repoprune'] == True:
        run(['git', 'fetch', '--prune'])
    else:
        run(['git', 'fetch'])
    run(['git', 'checkout', source_branch])
    run(['git', 'pull'])
    if config['existingbranch'] == False:
        run(['git', 'checkout', '-b', dest_branch])
    else:
        run(['git', 'checkout', dest_branch])
        run(['git', 'pull'])
        if config['updatebranch'] == True:
            run(['git', 'merge', source_branch, '-S', '-m', 'Merge branch \'{}\' into {}'.format(source_branch, dest_branch)])
    for f in config['files']:
        f['filedir'] = f['filedir'].rstrip('/')
        if f['versioned'] and 'version' in  repository_dict:
            local_filepath = '../../../files/{}/{}'.format(repository_dict['version'], f['filename'])
        else:
            local_filepath = '../../../files/{}'.format(f['filename'])
        remote_filepath = '{}/{}'.format(f['filedir'], f['filename'])
        if f['action'] == 'copy':
            if not os.path.exists('{}/{}'.format(os.getcwd(), f['filedir'])):
                os.makedirs('{}/{}'.format(os.getcwd(), f['filedir']))
            shutil.copyfile(local_filepath, remote_filepath)
        elif f['action'] == 'remove':
            run(['rm', '-rf', remote_filepath])
        elif f['action'] == 'edit':
            try:
                shutil.copyfile(remote_filepath, local_filepath)
            except:
                print('FAILED TO COPY FILE - DOES NOT EXIST')
            input('Hit Enter when done editing {} '.format(f['filename']))
            shutil.copyfile(local_filepath, remote_filepath)
        elif f['action'] == 'reset':
            run(['git', 'checkout', 'origin/{}'.format(source_branch), remote_filepath])
        run(['git', 'add', remote_filepath])
    if config['existingbranch'] == False:
        run(['git', 'commit', '-S', '-m', '{}'.format(config['msg']), '--no-verify'])
    else:
        run(['git', 'commit', '-S', '-m', '{}'.format(config['msg']), '--no-verify', '--allow-empty'])
    if config['existingbranch'] == False:
        run(['git', 'push', '--set-upstream', 'origin', dest_branch])
    else:
        run(['git', 'push'])
    if config['createpr'] == True:
        if config['existingbranch'] == False:
            if config['merge'] == 'draft':
                prnum = run(['gh', 'pr', 'create', '--title', config['msg'], '--body', '{}\n\nCreated by HenryGriffiths/bulk-update'.format(config['comment']), '-H', dest_branch, '-B', source_branch, '-a', '@me', '--draft', '-R', repository], returnoutput = True)
            else:
                prnum = run(['gh', 'pr', 'create', '--title', config['msg'], '--body', '{}\n\nCreated by HenryGriffiths/bulk-update'.format(config['comment']), '-H', dest_branch, '-B', source_branch, '-a', '@me', '-R', repository], returnoutput = True)
            try:
                prnum = prnum.split('https://github.com/')[1].split('/pull/')[1].strip()
                if config['merge'] == 'squash':
                    run(['gh', 'pr', 'merge', prnum, '-s', '-d'])
                elif config['merge'] == 'autosquash':
                    run(['gh', 'pr', 'merge', prnum, '-s', '-d', '--auto'])
                    if 'review_user' in config and 'review_token' in config:
                        requests.post('https://api.github.com/repos/{}/{}/pulls/{}/reviews'.format(org, repo, prnum), data = json.dumps({'event': 'APPROVE'}), headers = {'Accept': 'application/vnd.github.v3+json'}, auth = (config['review_user'], config['review_token']))
                elif config['merge'] == 'skip':
                    pass
            except:
                pass
    if config['shallowclone'] == True and config['repoprune'] == True and config['existingbranch'] == True:
        run(['git', 'config', '--unset', 'remote.origin.fetch', 'refs/heads/{}:refs/remotes/origin/{}'.format(dest_branch, dest_branch)])
        run(['git', 'branch', '-d', '-r', 'origin/{}'.format(dest_branch)])
    os.chdir('{}/../../'.format(os.getcwd()))
os.chdir('{}/../'.format(os.getcwd()))

