import os
import shutil
import subprocess
import json

with open('config3.json') as json_file:
    config = json.load(json_file)


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
    repository = repository_dict['repository']
    source_branch = repository_dict['source_branch']
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
        run(['git', 'clone', 'https://github.com/{}/{}.git'.format(org, repo)])
        os.chdir('{}/{}'.format(os.getcwd(), repo))
    run(['git', 'fetch'])
    run(['git', 'checkout', source_branch])
    run(['git', 'pull'])
    if config['existingbranch'] == False:
        run(['git', 'checkout', '-b', '{}-{}'.format(config['dest_branch'], source_branch)])
    else:
        run(['git', 'checkout', '{}-{}'.format(config['dest_branch'], source_branch)])
        run(['git', 'pull'])
    for f in config['files']:
        f['filedir'] = f['filedir'].rstrip('/')
        if f['action'] == 'copy':
            if not os.path.exists('{}/{}'.format(os.getcwd(), f['filedir'])):
                os.makedirs('{}/{}'.format(os.getcwd(), f['filedir']))
            shutil.copyfile('../../../files/{}'.format(f['filename']), '{}/{}'.format(f['filedir'], f['filename']))
        elif f['action'] == 'remove':
            run(['rm', '-rf', '{}/{}'.format(f['filedir'], f['filename'])])
        elif f['action'] == 'edit':
            shutil.copyfile('{}/{}'.format(f['filedir'], f['filename']), '../../../files/{}'.format(f['filename']))
            input('Hit Enter when done editing {} '.format(f['filename']))
            shutil.copyfile('../../../files/{}'.format(f['filename']), '{}/{}'.format(f['filedir'], f['filename']))
        run(['git', 'add', '{}/{}'.format(f['filedir'], f['filename'])])
    if config['existingbranch'] == False:
        run(['git', 'commit', '-S', '-m', '{}'.format(config['msg']), '--no-verify'])
    else:
        run(['git', 'commit', '-S', '-m', '{}'.format(config['msg']), '--no-verify', '--allow-empty'])
    if config['existingbranch'] == False:
        run(['git', 'push', '--set-upstream', 'origin', '{}-{}'.format(config['dest_branch'], source_branch)])
    else:
        run(['git', 'push'])
    if config['existingbranch'] == False:
        if config['merge'] == 'draft':
            prnum = run(['gh', 'pr', 'create', '--title', config['msg'], '--body', 'Created by HenryGriffiths/bulk-update', '-H', '{}-{}'.format(config['dest_branch'], source_branch), '-B', source_branch, '-a', '@me', '--draft', '-R', repository], returnoutput = True)
        else:
            prnum = run(['gh', 'pr', 'create', '--title', config['msg'], '--body', 'Created by HenryGriffiths/bulk-update', '-H', '{}-{}'.format(config['dest_branch'], source_branch), '-B', source_branch, '-a', '@me', '-R', repository], returnoutput = True)
        prnum = prnum.split('https://github.com/')[1].split('/pull/')[1].strip()
        if config['merge'] == 'squash':
            run(['gh', 'pr', 'merge', prnum, '-s', '-d'])
        elif config['merge'] == 'autosquash':
            run(['gh', 'pr', 'merge', prnum, '-s', '-d', '--auto'])
        elif config['merge'] == 'skip':
            pass
    os.chdir('{}/../../'.format(os.getcwd()))
os.chdir('{}/../'.format(os.getcwd()))

