import base64
import os
import tempfile
import json
from github import Github
from git import Repo
from dotenv import load_dotenv
from exception_handler.vcs.base_vcs_service import BaseVCSService

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
            pr_body = self._create_pr_body(data)

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

    def _create_pr_body(self, data):
        return f"""
        This is an auto-generated pull request to fix this sentry exception.
        Sentry Issue: {data['web_url']}
        
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