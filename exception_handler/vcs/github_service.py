import base64
import os
import tempfile
import json
from github import Github
from git import Repo
from dotenv import load_dotenv
from exception_handler.vcs.base_vcs_service import BaseVCSService
import re

load_dotenv()

class GitHubService(BaseVCSService):
    def __init__(self, config):
        super().__init__(config)
        self.github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        self.github = Github(self.github_token)
        
        self.local_repo_path = self.config['local_repo_path']
        
        if not self.local_repo_path:
            raise ValueError("LOCAL_REPO_PATH environment variable not set")
        
        self.repo = Repo(self.local_repo_path)

    def get_repo(self, repo_name):
        return self.github.get_repo(repo_name)

    def get_file_content(self, repo, file_path):
        try:
            full_path = os.path.join(self.local_repo_path, file_path)
            with open(full_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading content for {file_path}: {str(e)}")
            return None

    def create_pull_request(self, data, repo_name):
        try:
            github_repo = self.get_repo(repo_name)
            branch_name = f"fix/exception-bot/{data['issue_id']}"
            commit_message = f"Fix {data['exception_type']} exception"
            pr_title = f"[Exception Bot] Fix for {data['exception_type']} exception"
            pr_body = self._create_pr_body(data, github_repo.full_name)

            self._apply_diff_and_create_pr(github_repo, data['proposed_fix'], branch_name, 
                                           commit_message, pr_title, pr_body)
            
            return {"status": "success", "pr_url": f"https://github.com/{repo_name}/pulls"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def pull_request_exists(self, repo_name, issue_id):
        try:
            repo = self.get_repo(repo_name)
            branch_name = f"fix/exception-bot/{issue_id}"
            branches = repo.get_branches()
            return any(branch.name == branch_name for branch in branches)
        except Exception as e:
            print(f"Error checking branches: {str(e)}")
            return False

    def _apply_diff_and_create_pr(self, github_repo, diff_content, branch_name, commit_message, pr_title, pr_body):
        default_branch = github_repo.default_branch
        self.repo.git.checkout(default_branch)
        self.repo.git.pull('origin', default_branch)

        try:
            self.repo.git.checkout('-b', branch_name)
        except Exception as e:
            print(f"Error creating branch: {e}")
            return

        diff_content = self._clean_diff_content(diff_content)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as temp_file:
            temp_file.write(diff_content)
            temp_file_path = temp_file.name

        try:
            self.repo.git.apply(temp_file_path)
        except Exception as e:
            print(f"Error applying diff: {e}")
            os.unlink(temp_file_path)
            return
        finally:
            os.unlink(temp_file_path)

        self.repo.git.add(A=True)
        self.repo.index.commit(commit_message)

        origin = self.repo.remote('origin')
        origin.push(branch_name)

        try:
            pr = github_repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base=default_branch)
            print(f"Pull Request created: {pr.html_url}")
        except Exception as e:
            print(f"Error creating Pull Request: {e}")

    def _create_pr_body(self, data, repo_full_name):
        issue_link = f"https://github.com/{repo_full_name}/issues/{data['issue_id']}"
        sentry_url = data.get('sentry_url', 'N/A')  # Get the Sentry URL from the data
        return f"""
        This is an auto-generated pull request to fix this sentry exception.
        Sentry Issue: {sentry_url}
        GitHub Issue: {issue_link}
        
        Exception Type: {data['exception_type']}
        Exception Value: {data['exception_value']}
        
        Affected Files:
        {', '.join(data['affected_files'])}
        
        Analysis and Proposed Fix:
        {data['analysis']}
        
        Please review and merge if appropriate.
        """

    def _clean_diff_content(self, diff_content):
         # Remove any escape characters that might cause issues
        cleaned_diff = diff_content.replace('\\n', '\n')
        
        # Ensure proper line endings (use Unix-style line endings)
        cleaned_diff = cleaned_diff.replace('\r\n', '\n')
        
        # Remove any whitespace at the end of each line
        cleaned_diff = '\n'.join(line.rstrip() for line in cleaned_diff.split('\n'))
        
        # Ensure the diff ends with a newline character
        if not cleaned_diff.endswith('\n'):
            cleaned_diff += '\n'
        
        # Remove any potential hidden characters at the end
        cleaned_diff = cleaned_diff.rstrip() + '\n'

        return cleaned_diff

    def get_pull_request(self, repo_name, pr_number):
        repo = self.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        return {
            "title": pr.title,
            "body": pr.body,
            "head_branch": pr.head.ref,
            "base_branch": pr.base.ref,
            "files_changed": [file.filename for file in pr.get_files()]
        }

    def update_pull_request(self, repo_name, pr_number, updated_analysis):
        repo = self.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        branch_name = pr.head.ref

        # Apply the new changes
        self._apply_diff_and_update_branch(repo, updated_analysis['analysis']['diff'], branch_name)

        # Update PR description
        pr.edit(body=self._create_updated_pr_body(pr.body, updated_analysis['analysis']['analysis']))

        return {"status": "success", "pr_url": pr.html_url}

    def _apply_diff_and_update_branch(self, repo, diff_content, branch_name):
        # Fetch the latest changes from the remote
        self.repo.git.fetch('origin')

        try:
            # Try to check out the branch
            self.repo.git.checkout(branch_name)
        except Exception as e:
            print(f"Error checking out branch {branch_name}: {e}")
            # If the branch doesn't exist locally, create it
            self.repo.git.checkout('-b', branch_name, f'origin/{branch_name}')

        # Pull the latest changes
        self.repo.git.pull('origin', branch_name)

        diff_content = self._clean_diff_content(diff_content)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as temp_file:
            temp_file.write(diff_content)
            temp_file_path = temp_file.name

        try:
            self.repo.git.apply(temp_file_path)
        except Exception as e:
            print(f"Error applying diff: {e}")
            os.unlink(temp_file_path)
            return
        finally:
            os.unlink(temp_file_path)

        self.repo.git.add(A=True)
        self.repo.index.commit("Update fix based on PR comment")

        origin = self.repo.remote('origin')
        origin.push(branch_name)

    def _create_updated_pr_body(self, original_body, new_analysis):
        # Preserve the GitHub Issue link if it exists in the original body
        issue_link_match = re.search(r'GitHub Issue: (https://github\.com/.*?/issues/\d+)', original_body)
        issue_link = issue_link_match.group(1) if issue_link_match else ""

        updated_body = f"{original_body}\n\n---\n\nUpdated Analysis:\n{new_analysis}"
        
        if issue_link:
            updated_body += f"\n\nGitHub Issue: {issue_link}"

        return updated_body

    def add_pr_comment(self, repo_name, pr_number, comment_body, analysis):
        try:
            repo = self.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            # Apply the diff to the branch
            self._apply_diff_and_update_branch(repo, analysis['diff'], pr.head.ref)
            # Create the comment
            comment = pr.create_issue_comment(comment_body)
            
            return {
                "status": "success",
                "comment_url": comment.html_url,
                "pr_url": pr.html_url
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _create_comment_body(self, analysis):
        return f"""
        Based on the PR comment, here's an updated analysis:

        {analysis['analysis']}

        The changes have been applied to the branch. Please review and make any necessary adjustments.
        """
