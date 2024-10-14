from exception_handler.ai.ai_analysis_service import get_ai_service
from exception_handler.vcs.vcs_factory import get_vcs_service
import os
import re
import json

class ExceptionHandler:
    def __init__(self, config):
        self.config = config
        self.ai_service = get_ai_service(config)
        self.vcs_service = get_vcs_service(config)

    def handle_exception(self, processed_data, github_issue_id):
        repo_name = self.config['repo']
        
        if not github_issue_id:
            return {"error": "No GitHub issue ID provided"}
        
        if self.vcs_service.pull_request_exists(repo_name, github_issue_id):
            return {"status": "skipped", "reason": "Pull request already exists"}
        
        repo = self.vcs_service.get_repo(repo_name)

        trace_files = self._get_trace_files(repo, processed_data['stacktrace'])
        if not trace_files:
            return {"error": "Could not fetch any file content from the repository"}

        analysis_result = self.ai_service.analyze_exception(processed_data, trace_files)

        # Get the Sentry URL from environment variables
        sentry_url = os.environ.get('SENTRY_URL', 'N/A')

        vcs_response = self.vcs_service.create_pull_request({
            'proposed_fix': analysis_result['analysis'].get('diff', ''),
            'exception_type': processed_data['exception']['type'],
            'exception_value': processed_data['exception']['value'],
            'event_id': processed_data.get('event_id', 'unknown'),
            'issue_id': github_issue_id,
            'sentry_url': sentry_url,  # Use the Sentry URL from environment variables
            'analysis': analysis_result['analysis'].get('analysis', ''),
            'affected_files': analysis_result['affected_files']
        }, repo_name)

        return {
            "status": "success",
            "analysis": analysis_result,
            "vcs_response": vcs_response
        }

    def _get_trace_files(self, repo, stacktrace):
        trace_files = {}
        for frame in stacktrace:
            file_path = frame['filename']
            if file_path not in trace_files:
                file_content = self.vcs_service.get_file_content(repo, file_path)
                if file_content:
                    trace_files[file_path] = file_content
        return trace_files

    def handle_pr_comment(self, comment_data):
        repo_name = self.config['repo']
        pr_number = comment_data['pr_number']
        comment = comment_data['comment']

        pr_details = self.vcs_service.get_pull_request(repo_name, pr_number)
        
        # Extract affected files and their stacktraces from the PR description
        affected_files, stacktraces = self._extract_affected_files_and_stacktraces(pr_details['body'])

        # Fetch the content of affected files
        file_contents = {}
        for file_path in affected_files:
            content = self.vcs_service.get_file_content(self.vcs_service.get_repo(repo_name), file_path)
            if content:
                file_contents[file_path] = content

        # Get the original analysis from the PR description
        original_analysis = self._extract_original_analysis(pr_details['body'])

        analysis_result = self.ai_service.process_comment(comment, pr_details, file_contents, stacktraces, original_analysis)

        vcs_response = self.vcs_service.update_pull_request(repo_name, pr_number, analysis_result)

        return {
            "status": "success",
            "analysis": analysis_result,
            "vcs_response": vcs_response
        }

    def _extract_affected_files_and_stacktraces(self, pr_body):
        affected_files = []
        stacktraces = {}
        
        # Extract affected files
        files_section = re.search(r'Affected Files:\n(.*?)\n\n', pr_body, re.DOTALL)
        if files_section:
            affected_files = [file.strip() for file in files_section.group(1).split(',')]

        # Extract stacktraces
        stacktrace_section = re.search(r'Stacktrace:\n```(.*?)```', pr_body, re.DOTALL)
        if stacktrace_section:
            stacktrace_json = json.loads(stacktrace_section.group(1))
            for frame in stacktrace_json:
                file_path = frame.get('filename')
                if file_path and file_path not in stacktraces:
                    stacktraces[file_path] = frame

        return affected_files, stacktraces

    def _extract_original_analysis(self, pr_body):
        analysis_start = pr_body.find("Analysis and Proposed Fix:")
        if analysis_start != -1:
            return pr_body[analysis_start:]
        return ""
