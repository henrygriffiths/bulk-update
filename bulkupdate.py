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

if 'secrets_file' in config:
    with open(config['secrets_file']) as secrets_json_file:
        secrets_config = json.load(secrets_json_file)
        config['review_user'] = secrets_config['review_user'] if 'review_user' not in config else config['review_user']
        config['review_token'] = secrets_config['review_token'] if 'review_token' not in config else config['review_token']


def main():
    prs = []
    first = True
    os.chdir(f"{os.getcwd()}/{'repos'}")
    for repository_dict in config['repositories']:
        if not first and 'sleeptime' in config:
            print('Sleeping')
            time.sleep(config['sleeptime'] * 60)
        else:
            first = False
        repository = repository_dict['repository']
        source_branch = repository_dict['source_branch']
        dest_branch = f"{config['dest_branch']}-{source_branch}"
        org = repository.split('/')[0]
        repo = repository.split('/')[1]
        shallowclone = repository_dict['shallowclone'] if 'shallowclone' in repository_dict else False
        if not os.path.exists(f"{os.getcwd()}/{org}"):
            os.makedirs(f"{os.getcwd()}/{org}")
        os.chdir(f"{os.getcwd()}/{org}")
        if os.path.exists(f"{os.getcwd()}/{repo}"):
            os.chdir(f"{os.getcwd()}/{repo}")
            run(['git', 'reset', '--hard', 'HEAD'])
        else:
            run(['rm', '-rf', repo])
            if shallowclone == True:
                run(['git', 'clone', '--depth', '1', f"https://github.com/{org}/{repo}.git"])
            else:
                run(['git', 'clone', f"https://github.com/{org}/{repo}.git"])
            os.chdir(f"{os.getcwd()}/{repo}")
        if shallowclone == True and config['existingbranch'] == True:
            run(['git', 'config', '--add', 'remote.origin.fetch', f"+refs/heads/{dest_branch}:refs/remotes/origin/{dest_branch}"])
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
                run(['git', 'merge', source_branch, '-S', '-m', f"Merge branch {source_branch} into {dest_branch}"])
        for f in config['files']:
            f['filedir'] = f['filedir'].rstrip('/')
            if f['versioned'] and 'version' in  repository_dict:
                local_filepath = f"../../../files/{repository_dict['version']}/{f['filename']}"
            else:
                local_filepath = f"../../../files/{f['filename']}"
            remote_filepath = f"{f['filedir']}/{f['filename']}"
            if f['action'] == 'copy':
                if not os.path.exists(f"{os.getcwd()}/{f['filedir']}"):
                    os.makedirs(f"{os.getcwd()}/{f['filedir']}")
                shutil.copyfile(local_filepath, remote_filepath)
            elif f['action'] == 'remove':
                run(['rm', '-rf', remote_filepath])
            elif f['action'] == 'edit':
                try:
                    shutil.copyfile(remote_filepath, local_filepath)
                except:
                    print('FAILED TO COPY FILE - DOES NOT EXIST')
                input(f"Hit Enter when done editing {f['filename']} ")
                shutil.copyfile(local_filepath, remote_filepath)
            elif f['action'] == 'reset':
                run(['git', 'checkout', f"origin/{source_branch}", remote_filepath])
            run(['git', 'add', remote_filepath])
        if config['existingbranch'] == False:
            run(['git', 'commit', '-S', '-m', config['msg'], '--no-verify'])
        else:
            run(['git', 'commit', '-S', '-m', config['msg'], '--no-verify', '--allow-empty'])
        if config['existingbranch'] == False:
            run(['git', 'push', '--set-upstream', 'origin', dest_branch])
        else:
            run(['git', 'push'])
        if config['createpr'] == True:
            prtitle = config['pr_info']['title'] if 'title' in config['pr_info'] and config['pr_info']['title'] != '' else config['msg']
            proptions = ['--title', prtitle, '--body', f"{config['pr_info']['description']}\n\nCreated by henrygriffiths/bulk-update", '-H', dest_branch, '-B', source_branch, '-R', repository]
            if config['pr_info']['merge'] == 'draft':
                proptions += ['--draft']
            prnum = run(['gh', 'pr', 'create'] + proptions, returnoutput = True)
            try:
                prnum = prnum.split('https://github.com/')[1].split('/pull/')[1].strip()
                if config['pr_info']['mergedelay'] in ['none', 'wait']:
                    merge(org, repo, prnum, config)
                else:
                    prs.append({'org': org, 'repo': repo, 'prnum': prnum})
            except:
                pass
            if config['pr_info']['mergedelay'] == 'wait':
                merged = False
                while merged == False:
                    try:
                        time.sleep(60*1)
                        pr_state = json.loads(run(['gh', 'pr', 'view', prnum, '--json', 'state'], returnoutput = True))['state']
                        if pr_state == 'MERGED':
                            merged = True
                        print('Merged', merged)
                    except:
                        print('Failure')
                        pass
        if shallowclone == True and ('repoprune' in config and config['repoprune'] == True) and config['existingbranch'] == True:
            run(['git', 'config', '--unset', 'remote.origin.fetch', f"refs/heads/{dest_branch}:refs/remotes/origin/{dest_branch}"])
            run(['git', 'branch', '-d', '-r', f"origin/{dest_branch}"])
        os.chdir(f"{os.getcwd()}/../../")

    if config['createpr'] == True and config['pr_info']['mergedelay'] in ['after', 'afterinput']:
        if config['pr_info']['mergedelay'] == 'afterinput':
            input('Press enter when ready to merge')
        for pr in prs:
            os.chdir(f"{os.getcwd()}/{pr['org']}/{pr['repo']}")
            merge(pr['org'], pr['repo'], pr['prnum'], config)
            os.chdir(f"{os.getcwd()}/../../")
    os.chdir(f"{os.getcwd()}/../")


def merge(org, repo, prnum, config):
    try:
        if config['pr_info']['merge'] != 'skip':
            if 'review_user' in config and 'review_token' in config:
                requests.post(f"https://api.github.com/repos/{org}/{repo}/pulls/{prnum}/reviews", data = json.dumps({'event': 'APPROVE'}), headers = {'Accept': 'application/vnd.github.v3+json'}, auth = (config['review_user'], config['review_token']))
        prurl = f"https://github.com/{org}/{repo}/pull/{prnum}"
        deleteflag = [] if 'cleanup' in config['pr_info'] and config['pr_info']['cleanup'] == False else ['-d']
        if config['pr_info']['merge'] == 'merge':
            run(['gh', 'pr', 'merge', prurl, '-m'] + deleteflag)
        elif config['pr_info']['merge'] == 'automerge':
            run(['gh', 'pr', 'merge', prurl, '-m', '--auto'] + deleteflag)
        elif config['pr_info']['merge'] == 'rebase':
            run(['gh', 'pr', 'merge', prurl, '-r'] + deleteflag)
        elif config['pr_info']['merge'] == 'autorebase':
            run(['gh', 'pr', 'merge', prurl, '-r', '--auto'] + deleteflag)
        elif config['pr_info']['merge'] == 'squash':
            run(['gh', 'pr', 'merge', prurl, '-s'] + deleteflag)
        elif config['pr_info']['merge'] == 'autosquash':
            run(['gh', 'pr', 'merge', prurl, '-s', '--auto'] + deleteflag)
        elif config['pr_info']['merge'] == 'skip':
            pass
    except:
        print(f"Failure Merging {prurl}")


def run(args, returnoutput = False):
    while True:
        try:
            for x in range(10):
                if x <= 9:
                    try:
                        sp = subprocess.run(args, text = True, check = True, capture_output = returnoutput)
                        if returnoutput:
                            print(sp.stdout)
                        return sp.stdout
                    except:
                        time.sleep(pow(x * 2, 2))
                else:
                    sp = subprocess.run(args, text = True, check = True, capture_output = returnoutput)
                    if returnoutput:
                        print(sp.stdout)
                    return sp.stdout
        except:
            while True:
                print(f"Running {' '.join(args)} Failed.")
                result = input('(R)etry or (C)ontinue? : ')
                if result.lower() == 'r':
                    break
                elif result.lower() == 'c':
                    try:
                        return sp.stderr
                    except:
                        print('FAILED TO RETURN ERROR')
                        return


if __name__ == '__main__':
    main()
