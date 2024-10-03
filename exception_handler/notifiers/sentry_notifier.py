from exception_handler.notifiers.base_notifier import BaseNotifier

class SentryNotifier(BaseNotifier):
    def process_exception(self, payload):
        # Check if the payload is in the api format
        if 'id' in payload and 'entries' in payload:
            return self.process_api_format(payload)
        # Otherwise, assume it's in the webhook format
        else:
            return self.process_webhook_format(payload)

    def process_webhook_format(self, event):
        # Existing code for processing old format
        exception = event.get('exception', {}).get('values', [{}])[0]
        return {
            "event_id": event.get('event_id'),
            "project": event.get('project'),
            "environment": event.get('environment'),
            "platform": event.get('platform'),
            "release": event.get('release'),
            "transaction": event.get('transaction'),
            "exception": {
                "type": exception.get('type'),
                "value": exception.get('value'),
                "module": exception.get('module'),
            },
            "stacktrace": [frame for frame in exception.get('stacktrace', {}).get('frames', []) if frame.get('in_app')],
            "context": {
                "request": event.get('request', {}),
                "user": event.get('user', {}),
            },
            "tags": dict(event.get('tags', [])),
            "extra": event.get('extra', {}),
            "timestamp": event.get('timestamp'),
            "url": event.get('url'),
            "issue_id": event.get('issue_id'),
            "web_url": event.get('web_url')
        }

    def process_api_format(self, payload):
        # New code for processing new format
        exception_entry = next((entry for entry in payload.get('entries', []) if entry.get('type') == 'exception'), {})
        exception = exception_entry.get('data', {}).get('values', [{}])[0]
        return {
            "event_id": payload.get('id'),
            "project": payload.get('projectID'),
            "environment": payload.get('contexts', {}).get('os', {}).get('name'),
            "platform": payload.get('platform'),
            "release": payload.get('release'),
            "transaction": payload.get('transaction'),
            "exception": {
                "type": exception.get('type'),
                "value": exception.get('value'),
                "module": exception.get('module'),
            },
            "stacktrace": [frame for frame in exception.get('stacktrace', {}).get('frames', []) if self.is_app_file(frame.get('filename'))],
            "context": {
                "request": next((entry.get('data') for entry in payload.get('entries', []) if entry.get('type') == 'request'), {}),
                "user": payload.get('user', {}),
            },
            "tags": payload.get('tags', []),
            "extra": payload.get('contexts', {}),
            "timestamp": payload.get('dateReceived'),
            "url": payload.get('contexts', {}).get('context', {}).get('url'),
            "issue_id": payload.get('groupID'),
            "web_url": None  # This field is not present in the new format
        }

    def is_app_file(self, filename):
        if not filename:
            return False
        # Check if the filename contains only path components
        return all(part.islower() or part == '_' for part in filename.replace('/', '').replace('.', ''))