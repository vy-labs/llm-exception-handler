from exception_handler.ai.ai_analysis_service import get_ai_service
from exception_handler.vcs.vcs_factory import get_vcs_service

class ExceptionHandler:
    def __init__(self, config):
        self.config = config
        self.ai_service = get_ai_service(config)
        self.vcs_service = get_vcs_service(config)

    def handle_exception(self, processed_data):
        project = next((p for p in self.config['projects'] if str(p['unique_identifier']) == str(processed_data['project'])), None)
        
        if not project or processed_data['environment'] not in project['environments']:
            return {"status": "skipped", "reason": "Project or environment not allowed"}

        repo_name = project['repo']
        issue_id = processed_data['issue_id']
        
        if self.vcs_service.pull_request_exists(repo_name, issue_id):
            return {"status": "skipped", "reason": "Pull request already exists"}
        
        repo = self.vcs_service.get_repo(repo_name)
        trace_files = self._get_trace_files(repo, processed_data['stacktrace'])
        
        if not trace_files:
            return {"error": "Could not fetch any file content from the repository"}

        analysis_result = self.ai_service.analyze_exception(processed_data, trace_files)

        vcs_response = self.vcs_service.create_pull_request({
            'proposed_fix': analysis_result['analysis'].get('diff', ''),
            'exception_type': processed_data['exception']['type'],
            'exception_value': processed_data['exception']['value'],
            'event_id': processed_data.get('event_id', 'unknown'),
            'issue_id': processed_data.get('issue_id', 'unknown'),
            'web_url': processed_data.get('web_url', 'unknown'),
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