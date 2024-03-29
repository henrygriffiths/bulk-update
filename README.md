# Bulk Update

Bulk Update is a script that can automatically copy/update a series of files across multiple git repositories, with the ability to open and merge pull requests. The script is written in Python 3, uses JSON for configuration files, and optionally the GitHub command line tool for opening and managing pull requests. For example, common contributing guides, licenses, lint configurations, etc that are the same across an organization can be automatically copied and merged across all the repositories in an organization, eliminating the need to manually copy and update these files.


## Table of contents

* [Installation](#installation)
* [Configuration](#configuration)
* [Repository Structure](#repository-structure)


## Installation

### Prerequisites:
* [Python](https://www.python.org/) >= v3.8
* [Git](https://git-scm.com/) >= v2.39.0
* [GitHub CLI](https://cli.github.com/) >= 2.23.0

### Install from scratch:
1. Clone the repository
2. Create a Python virtual environment and activate (not required, but good practice)
3. Install the requirements
4. Configure the `config.json` file as required
5. Run the `bulkupdate.py` python script. Optionally specify the config file to use, eg `python bulkupdate.py config.json`


## Configuration

The [example.config.json](example.config.json) file contains an example configuration as follows:
  ```json
  {
      "files": [
          {
              "filedir": "dir",
              "filename": "test.txt",
              "action": "copy",
              "versioned": true
          }
      ],
      "repositories": [
          {
              "repository": "org/example",
              "source_branch": "main",
              "version": "v1",
              "shallowclone": false
          }
      ],
      "dest_branch": "feat/test",
      "force_branch_suffix": false,
      "msg": "feat: example",
      "createpr": true,
      "pr_info": {
          "title": "PR Title",
          "description": "This PR fixes example issue",
          "merge": "merge",
          "mergedelay": "none",
          "cleanup": true
      },
      "existingbranch": false,
      "updatebranch": false,
      "sleeptime": 0,
      "repoprune": true,
      "shallowclone": true,
      "secrets_file": "secrets.json"
  }
  ```
  
  * `files` (required): array that stores information about the files the script is updating
    + `filedir` (required): path to the file in the remote repositories (repositories which the script is updating). Leave blank for the root of the repository
    + `filename` (required): the full name of the file
    + `action` (required): 
      * `copy`: copy the file as-is to the remote repo
      * `edit`: copy the file from the remote repo, allow for editing, then copy back
      * `remove`: remove the file from the remote repo
      * `reset`: reset any changes to the file done on the working branch
    + `versioned` (required):
      * `false`: Use the file in the `files/` directory
      * `true`: Use the file in the `files/<version>` directory, where `<version>` is specified in the repositories configuration
  * `repositories` (required): array of repositories the script is updating
    + `repository` (required): The organization/user and repository name of the GitHub repository
    + `source_branch` (required): The branch of the repository off of which the script works
    + `version` (optional): If the file is set as versioned, the path under the files directory in which the file is located
    + `shallowclone` (optional): Whether or not to perform a shallow clone
  * `dest_branch` (required): The branch on which the script will commit files. Will be suffixed by the source branch name to differentiate when there are duplicate repositories with different source branches.
  * `force_branch_suffix` (optional): If enabled, will always suffix the destination branch with the source branch name.
  * `msg` (required): The commit message and PR title
  * `createpr` (required): Whether to create a PR
  * `pr_info` (required if createpr is true): Dict holding PR-specific info
    + `title` (optional): The PR title. Defaults to the commit message if empty
    + `description` (required): The PR description
    + `merge` (required):
      * `draft`: Create a PR in a draft state
      * `merge`: Merge the PR with a merge commit
      * `automerge`: Enable auto-merge, merge with a merge commit when requirements are met
      * `rebase`: Rebase merge the PR
      * `autorebase`: Enable auto-merge, rebase merge when requirements are met
      * `squash`: Squash merge the PR
      * `autosquash`: Enable auto-merge, squash merge when requirements are met
      * `skip`: Do not automatically merge the PR
    + `mergedelay` (required):
      * `none`: Perform merge action after creating PR
      * `wait`: Wait until the created PR has been merged before creating the next one
      * `after`: Wait until all PRs have been created, then perform merge action
      * `afterinput`: Wait until all PRs have been created, request user input, then perform merge action
    + `cleanup` (optional): Whether or not to delete the PR's branch after merging
  * `existingbranch` (required):
    + `true`: Use an existing branch already on the remote repositories
    + `false`: Create a new branch on the remote repositories
  * `updatebranch` (required): Whether or not to update the `source_branch` with new changes on the `dest_branch`
  * `sleeptime` (optional): The amount of time (in minutes) to wait between actions on each repository
  * `repoprune` (optional): Whether or not to delete branches that no longer exist on the remotes of the remote repositories
  * `secrets_file` (optional): The name of the secrets file. The data in the secrets file can also be provided in this configuration. If not provided, the PR (if created) will not be automatically approved

The [example.secrets.json](example.secrets.json) file contains an example configuration as follows:
  ```json
  {
      "review_user": "",
      "review_token": ""
  }
  ```

* `review_user` (optional): If `merge` is `autosquash`, the username of a second GitHub user to approve the PR
* `review_token` (optional): A GitHub Personal Access Token for the user


## Repository Structure

* `files`: Files that the script copies to the remote repositories under the path `repos/<version>` if the files are versioned.
* `repos`: Repos that the script has managed under the path `repos/<org>/<repo>`
* `config.json`: Contains the script configuration, as described in [Configuration](#configuration)
* `secrets.json`: Contains the script secrets, as described in [Configuration](#configuration)
