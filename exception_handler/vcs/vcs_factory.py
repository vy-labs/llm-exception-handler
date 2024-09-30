from exception_handler.vcs.github_service import GitHubService

def get_vcs_service(config):
    vcs_type = config.get('vcs_type', 'github').lower()
    if vcs_type == 'github':
        return GitHubService(config)
    else:
        raise ValueError(f"Unsupported VCS type: {vcs_type}")